import io
import os
import tempfile
import wave
from pathlib import Path
from typing import Any, Optional, Tuple
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

from fastapi import HTTPException, UploadFile  # type: ignore
import numpy as np


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


def _download_audio_from_url(url: str, max_bytes: int) -> Tuple[str, str]:
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


async def _save_upload_file(upload: UploadFile, fallback_name: str) -> Tuple[str, str]:
    filename = upload.filename or fallback_name
    suffix = Path(filename).suffix or Path(fallback_name).suffix or ".wav"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            temp_file.write(chunk)
        return temp_file.name, filename


def _wav_bytes_from_array(audio: Any, sample_rate: int) -> bytes:
    audio_array = np.asarray(audio, dtype=np.float32)
    if audio_array.size == 0:
        raise HTTPException(status_code=500, detail="TTS 生成的音频为空")

    if audio_array.ndim == 1:
        channels = 1
    elif audio_array.ndim == 2:
        channels = audio_array.shape[1]
    else:
        raise HTTPException(status_code=500, detail="TTS 音频维度不受支持")

    pcm16 = np.clip(audio_array, -1.0, 1.0)
    pcm16 = (pcm16 * 32767.0).astype(np.int16)

    with io.BytesIO() as buffer:
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm16.tobytes())
        return buffer.getvalue()
