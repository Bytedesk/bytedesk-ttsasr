import os
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile # type: ignore
from pydantic import BaseModel
from fastapi.responses import JSONResponse, PlainTextResponse, Response # type: ignore
from app.model_provider import get_asr_model, get_qwen_tts_model, get_tts_model
from app.utils import _clean_result, _download_audio_from_url, _env, _env_bool, _env_int, _get_speech_output_dir, _save_upload_file, _wav_bytes_from_array


app = FastAPI(
    title="Bytedesk Speech Service",
    version="0.2.0",
    description="Dockerized speech service for FunASR ASR and VoxCPM TTS.",
)


class SpeechRequest(BaseModel):
    input: str
    model: str = "voxcpm"
    voice: str = "default"
    language: str = "Auto"
    response_format: str = "wav"
    speed: float = 1.0
    cfg_value: float = 2.0
    inference_timesteps: int = 10
    reference_audio_url: Optional[str] = None
    prompt_audio_url: Optional[str] = None
    prompt_text: Optional[str] = None


@app.on_event("startup")
def startup_event() -> None:
    if _env_bool("FUNASR_PRELOAD", False):
        get_asr_model()
    if _env_bool("VOXCPM_PRELOAD", False):
        get_tts_model()
    if _env_bool("QWEN_TTS_PRELOAD", False):
        get_qwen_tts_model()


@app.get("/health")
def health() -> dict[str, str]:
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
            temp_path, source_filename = await _save_upload_file(file, "audio.wav")
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

        result = get_asr_model().generate(**generate_kwargs)
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


@app.post("/v1/audio/speech")
async def openai_speech(
    request: Request,
    input: Optional[str] = Form(default=None),
    model: str = Form(default="voxcpm"),
    voice: str = Form(default="default"),
    language: str = Form(default="Auto"),
    response_format: str = Form(default="wav"),
    speed: float = Form(default=1.0),
    cfg_value: float = Form(default=2.0),
    inference_timesteps: int = Form(default=10),
    prompt_text: Optional[str] = Form(default=None),
    reference_audio_url: Optional[str] = Form(default=None),
    prompt_audio_url: Optional[str] = Form(default=None),
    reference_audio: Optional[UploadFile] = File(default=None),
    prompt_audio: Optional[UploadFile] = File(default=None),
) -> Response:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("application/json"):
        request_payload = SpeechRequest.model_validate(await request.json())
    else:
        request_payload = SpeechRequest(
            input=input or "",
            model=model,
            voice=voice,
            language=language,
            response_format=response_format,
            speed=speed,
            cfg_value=cfg_value,
            inference_timesteps=inference_timesteps,
            reference_audio_url=reference_audio_url,
            prompt_audio_url=prompt_audio_url,
            prompt_text=prompt_text,
        )

    if not request_payload.input.strip():
        raise HTTPException(status_code=400, detail="input 不能为空")
    if request_payload.response_format != "wav":
        raise HTTPException(status_code=400, detail="当前仅支持 wav 输出")
    if request_payload.speed <= 0:
        raise HTTPException(status_code=400, detail="speed 必须大于 0")
    if reference_audio is not None and request_payload.reference_audio_url:
        raise HTTPException(status_code=400, detail="reference_audio 和 reference_audio_url 只能二选一")
    if prompt_audio is not None and request_payload.prompt_audio_url:
        raise HTTPException(status_code=400, detail="prompt_audio 和 prompt_audio_url 只能二选一")

    provider = (request_payload.model or _env("TTS_PROVIDER", "voxcpm") or "voxcpm").strip().lower()
    if provider in {"qwen", "qwen3-tts", "qwen-tts"}:
        provider = "qwen-tts"
    else:
        provider = "voxcpm"

    text = request_payload.input.strip()

    temp_paths: list[str] = []
    reference_audio_path = ""
    prompt_audio_path = ""

    try:
        max_bytes = _env_int("FUNASR_MAX_URL_FILE_SIZE", 50 * 1024 * 1024)
        if reference_audio is not None:
            reference_audio_path, _ = await _save_upload_file(reference_audio, "reference.wav")
            temp_paths.append(reference_audio_path)
        elif request_payload.reference_audio_url:
            reference_audio_path, _ = _download_audio_from_url(
                url=request_payload.reference_audio_url,
                max_bytes=max_bytes,
            )
            temp_paths.append(reference_audio_path)

        if prompt_audio is not None:
            prompt_audio_path, _ = await _save_upload_file(prompt_audio, "prompt.wav")
            temp_paths.append(prompt_audio_path)
        elif request_payload.prompt_audio_url:
            prompt_audio_path, _ = _download_audio_from_url(
                url=request_payload.prompt_audio_url,
                max_bytes=max_bytes,
            )
            temp_paths.append(prompt_audio_path)

        if provider == "voxcpm":
            voxcpm_text = text
            if request_payload.voice and request_payload.voice != "default":
                voxcpm_text = f"({request_payload.voice}){voxcpm_text}"

            tts_generate_kwargs: dict[str, Any] = {
                "text": voxcpm_text,
                "cfg_value": request_payload.cfg_value,
                "inference_timesteps": request_payload.inference_timesteps,
            }
            if reference_audio_path:
                tts_generate_kwargs["reference_wav_path"] = reference_audio_path
            if prompt_audio_path:
                tts_generate_kwargs["prompt_wav_path"] = prompt_audio_path
            if request_payload.prompt_text:
                tts_generate_kwargs["prompt_text"] = request_payload.prompt_text

            tts_model = get_tts_model()
            wav = tts_model.generate(**tts_generate_kwargs)
            sample_rate = int(getattr(tts_model.tts_model, "sample_rate", 48000))
        else:
            qwen_model = get_qwen_tts_model()
            qwen_language = request_payload.language or _env("QWEN_TTS_LANGUAGE", "Auto") or "Auto"

            if reference_audio_path:
                if not hasattr(qwen_model, "generate_voice_clone"):
                    raise HTTPException(status_code=400, detail="当前 Qwen 模型不支持声音克隆，请切换 Base 模型")
                clone_kwargs: dict[str, Any] = {
                    "text": text,
                    "language": qwen_language,
                    "ref_audio": reference_audio_path,
                }
                if request_payload.prompt_text:
                    clone_kwargs["ref_text"] = request_payload.prompt_text
                else:
                    clone_kwargs["x_vector_only_mode"] = True
                wavs, sample_rate = qwen_model.generate_voice_clone(**clone_kwargs)
                wav = wavs[0]
            elif hasattr(qwen_model, "generate_custom_voice"):
                custom_kwargs: dict[str, Any] = {
                    "text": text,
                    "language": qwen_language,
                    "speaker": _env("QWEN_TTS_SPEAKER", "Vivian") or "Vivian",
                }
                if request_payload.voice and request_payload.voice != "default":
                    custom_kwargs["instruct"] = request_payload.voice
                wavs, sample_rate = qwen_model.generate_custom_voice(**custom_kwargs)
                wav = wavs[0]
            elif hasattr(qwen_model, "generate_voice_design"):
                instruct = request_payload.voice if request_payload.voice != "default" else (_env("QWEN_TTS_DEFAULT_INSTRUCT") or "")
                if not instruct:
                    raise HTTPException(status_code=400, detail="当前 Qwen 模型需要 voice/instruct 参数")
                wavs, sample_rate = qwen_model.generate_voice_design(
                    text=text,
                    language=qwen_language,
                    instruct=instruct,
                )
                wav = wavs[0]
            else:
                raise HTTPException(status_code=500, detail="当前 Qwen 模型不支持可用的语音生成方法")

        audio_bytes = _wav_bytes_from_array(wav, sample_rate)
    except HTTPException:
        raise
    except Exception as exc:  # pragma: no cover - runtime dependency failures
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        for temp_path in temp_paths:
            if temp_path and os.path.exists(temp_path):
                os.remove(temp_path)
        if reference_audio is not None:
            await reference_audio.close()
        if prompt_audio is not None:
            await prompt_audio.close()

    output_dir = _get_speech_output_dir()
    if output_dir:
        import uuid as _uuid
        import datetime as _dt
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        ts = _dt.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{provider}_{ts}_{_uuid.uuid4().hex[:8]}.wav"
        (out_path / filename).write_bytes(audio_bytes)

    headers = {
        "Content-Disposition": 'inline; filename="speech.wav"',
        "X-Speech-Model": request_payload.model,
        "X-TTS-Provider": provider,
    }
    return Response(content=audio_bytes, media_type="audio/wav", headers=headers)