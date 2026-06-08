import os
import tempfile
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile # type: ignore
from fastapi.responses import JSONResponse, PlainTextResponse, Response # type: ignore
from app.model_provider import get_model
from app.utils import _clean_result, _download_audio_from_url, _env_int


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