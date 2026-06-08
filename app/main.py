import os
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse, Response
from funasr import AutoModel


def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def _env_bool(name: str, default: bool = False) -> bool:
    value = _env(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = _env(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _clean_result(result: Any) -> dict[str, Any]:
    if isinstance(result, list) and result:
        first = result[0]
        if isinstance(first, dict):
            payload = dict(first)
            payload.setdefault("raw", result)
            return payload
    if isinstance(result, dict):
        payload = dict(result)
        payload.setdefault("raw", result)
        return payload
    return {"raw": result}


def _download_audio_from_url(url: str, max_bytes: int) -> tuple[str, str]:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise HTTPException(status_code=400, detail="url 仅支持 http/https")

    filename = Path(unquote(parsed.path or "")).name or "audio_from_url.wav"
    suffix = Path(filename).suffix or ".wav"

    try:
        request = Request(url, headers={"User-Agent": "bytedesk-ttsasr/0.1"})
        with urlopen(request, timeout=30) as response:
            content_length = response.headers.get("Content-Length")
            if content_length is not None and content_length.isdigit():
                if int(content_length) > max_bytes:
                    raise HTTPException(
                        status_code=413,
                        detail=f"url 音频文件过大，最大允许 {max_bytes} 字节",
                    )

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                total = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        temp_path = temp_file.name
                        temp_file.close()
                        if os.path.exists(temp_path):
                            os.remove(temp_path)
                        raise HTTPException(
                            status_code=413,
                            detail=f"url 音频文件过大，最大允许 {max_bytes} 字节",
                        )
                    temp_file.write(chunk)

                if total == 0:
                    raise HTTPException(status_code=400, detail="url 音频内容为空")

                return temp_file.name, filename
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"下载 url 音频失败: {exc}") from exc


@lru_cache(maxsize=1)
def get_model() -> AutoModel:
    model_name = _env("FUNASR_MODEL", "iic/SenseVoiceSmall")
    model_kwargs: dict[str, Any] = {
        "model": model_name,
        "device": _env("FUNASR_DEVICE", "cpu"),
        "disable_update": True,
    }

    optional_settings = {
        "vad_model": _env("FUNASR_VAD_MODEL", "fsmn-vad"),
        "punc_model": _env("FUNASR_PUNC_MODEL"),
        "spk_model": _env("FUNASR_SPK_MODEL"),
        "hub": _env("FUNASR_HUB"),
    }
    for key, value in optional_settings.items():
        if value:
            model_kwargs[key] = value

    if _env_bool("FUNASR_TRUST_REMOTE_CODE", False):
        model_kwargs["trust_remote_code"] = True

    return AutoModel(**model_kwargs)


app = FastAPI(
    title="FunASR Service",
    version="0.1.0",
    description="Dockerized FunASR HTTP service for ASR transcription.",
)


@app.on_event("startup")
def startup_event() -> None:
    get_model()


@app.get("/health")
def health() -> dict[str, str]:
    get_model()
    return {"status": "ok"}


async def _transcribe_impl(
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = Form(default=None),
    language: str = Form("auto"),
    hotword: Optional[str] = Form(default=None),
    batch_size: int = Form(default=1),
    response_format: str = Form(default="json"),
) -> Response:
    if (file is None and not url) or (file is not None and url):
        raise HTTPException(status_code=400, detail="请在 file 和 url 中二选一")

    temp_path = ""
    source_filename = "audio.wav"

    try:
        if file is not None:
            source_filename = file.filename or "audio.wav"
            suffix = Path(source_filename).suffix or ".wav"
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                while True:
                    chunk = await file.read(1024 * 1024)
                    if not chunk:
                        break
                    temp_file.write(chunk)
                temp_path = temp_file.name
        else:
            max_bytes = _env_int("FUNASR_MAX_URL_FILE_SIZE", 50 * 1024 * 1024)
            temp_path, source_filename = _download_audio_from_url(url=url or "", max_bytes=max_bytes)

        generate_kwargs: dict[str, Any] = {
            "input": temp_path,
            "batch_size": batch_size,
        }
        if language and language != "auto":
            generate_kwargs["language"] = language
        if hotword:
            generate_kwargs["hotword"] = hotword

        result = get_model().generate(**generate_kwargs)
        payload = _clean_result(result)
        payload.setdefault("text", payload.get("text", ""))
        payload["filename"] = source_filename

        if response_format == "text":
            return PlainTextResponse(payload["text"])
        return JSONResponse(payload)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - runtime dependency failures
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        if file is not None:
            await file.close()


@app.post("/v1/asr/transcriptions")
async def transcribe(
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = Form(default=None),
    language: str = Form("auto"),
    hotword: Optional[str] = Form(default=None),
    batch_size: int = Form(default=1),
    response_format: str = Form(default="json"),
) -> Response:
    return await _transcribe_impl(
        file=file,
        url=url,
        language=language,
        hotword=hotword,
        batch_size=batch_size,
        response_format=response_format,
    )


@app.post("/v1/audio/transcriptions")
async def openai_transcribe(
    file: Optional[UploadFile] = File(default=None),
    url: Optional[str] = Form(default=None),
    model: Optional[str] = Form(default=None),
    language: str = Form("auto"),
    hotword: Optional[str] = Form(default=None),
    batch_size: int = Form(default=1),
    response_format: str = Form(default="json"),
) -> Response:
    del model
    return await _transcribe_impl(
        file=file,
        url=url,
        language=language,
        hotword=hotword,
        batch_size=batch_size,
        response_format=response_format,
    )