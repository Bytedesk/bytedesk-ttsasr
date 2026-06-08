#!/usr/bin/env python3
"""
在 Docker 镜像构建阶段预下载模型权重。
通过以下构建参数（ARG）控制行为（默认值见 Dockerfile）：

  DOWNLOAD_MODELS_ON_BUILD   总开关，默认 true
  FUNASR_DOWNLOAD_ON_BUILD   是否下载 ASR 模型，默认 true
  VOXCPM_DOWNLOAD_ON_BUILD   是否下载 VoxCPM 模型，默认 false（约 4.3GB）
  QWEN_TTS_DOWNLOAD_ON_BUILD 是否下载 Qwen3-TTS 模型，默认 false（约 3.6GB）
"""
import os
import sys
from typing import Any, Callable


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name, "")
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _env(name: str, default: str) -> str:
    return os.getenv(name) or default


def _snapshot_download(model_id: str, local_files_only: bool = False) -> str:
    from modelscope import snapshot_download  # type: ignore

    return snapshot_download(model_id, local_files_only=local_files_only)


def _normalize_model_key(model_name: str) -> str:
    normalized = (model_name or "").strip().lower()
    if normalized in {"funasr", "asr", "sensevoice"}:
        return "funasr"
    if normalized in {"voxcpm", "tts"}:
        return "voxcpm"
    if normalized in {"qwen", "qwen-tts", "qwen3-tts"}:
        return "qwen-tts"
    raise ValueError(f"不支持的模型类型: {model_name}")


def _funasr_model_refs() -> list[str]:
    return [
        model_name
        for model_name in [
            _env("FUNASR_MODEL", "iic/SenseVoiceSmall"),
            _env("FUNASR_VAD_MODEL", "fsmn-vad"),
        ]
        if model_name
    ]


def _model_entries() -> dict[str, dict[str, Any]]:
    return {
        "funasr": {
            "display_name": "FunASR",
            "models": _funasr_model_refs(),
            "downloader": download_funasr,
        },
        "voxcpm": {
            "display_name": "VoxCPM",
            "models": [_env("VOXCPM_MODELSCOPE_MODEL", "OpenBMB/VoxCPM2")],
            "downloader": download_voxcpm,
        },
        "qwen-tts": {
            "display_name": "Qwen3-TTS",
            "models": [_env("QWEN_TTS_MODELSCOPE_MODEL", "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice")],
            "downloader": download_qwen_tts,
        },
    }


def _is_model_cached(model_id: str) -> bool:
    try:
        resolved_path = _snapshot_download(model_id, local_files_only=True)
        return bool(resolved_path and os.path.exists(resolved_path))
    except Exception:
        return False


def get_model_download_status(model_name: str) -> dict[str, Any]:
    model_key = _normalize_model_key(model_name)
    entry = _model_entries()[model_key]
    model_states = [
        {
            "model_id": model_id,
            "downloaded": _is_model_cached(model_id),
        }
        for model_id in entry["models"]
    ]
    return {
        "model": model_key,
        "display_name": entry["display_name"],
        "downloaded": all(item["downloaded"] for item in model_states),
        "items": model_states,
    }


def list_model_download_status() -> list[dict[str, Any]]:
    return [get_model_download_status(model_name) for model_name in _model_entries()]


def download_model_by_name(model_name: str) -> dict[str, Any]:
    model_key = _normalize_model_key(model_name)
    entry = _model_entries()[model_key]
    downloader = entry["downloader"]
    if not callable(downloader):
        raise RuntimeError(f"模型 {model_key} 缺少下载器")

    downloader()
    return get_model_download_status(model_key)


def download_funasr() -> None:
    print("[download] Downloading FunASR ASR models...", flush=True)
    try:
        for m in _funasr_model_refs():
            if m:
                print(f"[download]   {m}", flush=True)
                _snapshot_download(m)
        print("[download] FunASR models done.", flush=True)
    except Exception as exc:
        print(f"[download] WARNING: FunASR download failed: {exc}", file=sys.stderr, flush=True)


def download_voxcpm() -> None:
    print("[download] Downloading VoxCPM model (~4.3 GB)...", flush=True)
    try:
        model = _env("VOXCPM_MODELSCOPE_MODEL", "OpenBMB/VoxCPM2")
        print(f"[download]   {model}", flush=True)
        _snapshot_download(model)
        print("[download] VoxCPM model done.", flush=True)
    except Exception as exc:
        print(f"[download] WARNING: VoxCPM download failed: {exc}", file=sys.stderr, flush=True)


def download_qwen_tts() -> None:
    print("[download] Downloading Qwen3-TTS model (~3.6 GB)...", flush=True)
    try:
        model = _env("QWEN_TTS_MODELSCOPE_MODEL", "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice")
        print(f"[download]   {model}", flush=True)
        _snapshot_download(model)
        print("[download] Qwen3-TTS model done.", flush=True)
    except Exception as exc:
        print(f"[download] WARNING: Qwen3-TTS download failed: {exc}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    if not _env_bool("DOWNLOAD_MODELS_ON_BUILD", True):
        print("[download] DOWNLOAD_MODELS_ON_BUILD=false, skipping.", flush=True)
        sys.exit(0)

    if _env_bool("FUNASR_DOWNLOAD_ON_BUILD", True):
        download_funasr()

    if _env_bool("VOXCPM_DOWNLOAD_ON_BUILD", False):
        download_voxcpm()

    if _env_bool("QWEN_TTS_DOWNLOAD_ON_BUILD", False):
        download_qwen_tts()

    print("[download] All done.", flush=True)
