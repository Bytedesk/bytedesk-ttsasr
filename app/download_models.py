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


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name, "")
    if not value:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _env(name: str, default: str) -> str:
    return os.getenv(name) or default


def download_funasr() -> None:
    print("[download] Downloading FunASR ASR models...", flush=True)
    try:
        from modelscope import snapshot_download  # type: ignore

        models = [
            _env("FUNASR_MODEL", "iic/SenseVoiceSmall"),
            _env("FUNASR_VAD_MODEL", "fsmn-vad"),
        ]
        for m in models:
            if m:
                print(f"[download]   {m}", flush=True)
                snapshot_download(m)
        print("[download] FunASR models done.", flush=True)
    except Exception as exc:
        print(f"[download] WARNING: FunASR download failed: {exc}", file=sys.stderr, flush=True)


def download_voxcpm() -> None:
    print("[download] Downloading VoxCPM model (~4.3 GB)...", flush=True)
    try:
        from modelscope import snapshot_download  # type: ignore

        model = _env("VOXCPM_MODELSCOPE_MODEL", "OpenBMB/VoxCPM2")
        print(f"[download]   {model}", flush=True)
        snapshot_download(model)
        print("[download] VoxCPM model done.", flush=True)
    except Exception as exc:
        print(f"[download] WARNING: VoxCPM download failed: {exc}", file=sys.stderr, flush=True)


def download_qwen_tts() -> None:
    print("[download] Downloading Qwen3-TTS model (~3.6 GB)...", flush=True)
    try:
        from modelscope import snapshot_download  # type: ignore

        model = _env("QWEN_TTS_MODELSCOPE_MODEL", "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice")
        print(f"[download]   {model}", flush=True)
        snapshot_download(model)
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
