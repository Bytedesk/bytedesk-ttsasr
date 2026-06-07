import os
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse
from funasr import AutoModel


def _env(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value


def _env_bool(name: str, default: bool = False) -> bool:
    value = _env(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


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


@lru_cache(maxsize=1)
def get_model() -> AutoModel:
    model_name = _env("FUNASR_MODEL", "iic/SenseVoiceSmall")
    model_kwargs: dict[str, Any] = {
        "model": model_name,
        "device": _env("FUNASR_DEVICE", "cpu"),
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
    file: UploadFile = File(...),
    language: str = Form("auto"),
    hotword: str | None = Form(default=None),
    batch_size: int = Form(default=1),
    response_format: str = Form(default="json"),
) -> JSONResponse | PlainTextResponse:
    suffix = Path(file.filename or "audio.wav").suffix or ".wav"

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                temp_file.write(chunk)
            temp_path = temp_file.name

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
        payload["filename"] = file.filename

        if response_format == "text":
            return PlainTextResponse(payload["text"])
        return JSONResponse(payload)
    except Exception as exc:  # pragma: no cover - runtime dependency failures
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if "temp_path" in locals() and os.path.exists(temp_path):
            os.remove(temp_path)
        await file.close()


@app.post("/v1/asr/transcriptions")
async def transcribe(
    file: UploadFile = File(...),
    language: str = Form("auto"),
    hotword: str | None = Form(default=None),
    batch_size: int = Form(default=1),
    response_format: str = Form(default="json"),
) -> JSONResponse | PlainTextResponse:
    return await _transcribe_impl(
        file=file,
        language=language,
        hotword=hotword,
        batch_size=batch_size,
        response_format=response_format,
    )


@app.post("/v1/audio/transcriptions")
async def openai_transcribe(
    file: UploadFile = File(...),
    model: str | None = Form(default=None),
    language: str = Form("auto"),
    hotword: str | None = Form(default=None),
    batch_size: int = Form(default=1),
    response_format: str = Form(default="json"),
) -> JSONResponse | PlainTextResponse:
    del model
    return await _transcribe_impl(
        file=file,
        language=language,
        hotword=hotword,
        batch_size=batch_size,
        response_format=response_format,
    )