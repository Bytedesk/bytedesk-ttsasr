from pathlib import Path
from functools import lru_cache
from typing import Any

from funasr import AutoModel  # type: ignore

from app.utils import _env, _env_bool


def _resolve_model_ref(model_ref: str, source: str, modelscope_model: str) -> str:
    if Path(model_ref).exists():
        return model_ref

    if source in {"auto", "modelscope"}:
        try:
            from modelscope import snapshot_download  # type: ignore

            return snapshot_download(modelscope_model)
        except Exception:
            if source == "modelscope":
                raise

    return model_ref


@lru_cache(maxsize=1)
def get_asr_model() -> AutoModel:
    model_name = _env("FUNASR_MODEL", "iic/SenseVoiceSmall")
    model_kwargs: dict[str, Any] = {
        "model": model_name,
        "device": _env("FUNASR_DEVICE", "cpu"),
        "disable_update": _env_bool("FUNASR_DISABLE_UPDATE", True),
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


@lru_cache(maxsize=1)
def get_tts_model() -> Any:
    try:
        from voxcpm import VoxCPM  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on optional runtime dependency
        raise RuntimeError(
            "未安装 voxcpm 依赖，请确认镜像已安装 VoxCPM 所需包"
        ) from exc

    model_ref = _env("VOXCPM_MODEL", "openbmb/VoxCPM2") or "openbmb/VoxCPM2"
    source = (_env("VOXCPM_SOURCE", "modelscope") or "modelscope").lower()
    resolved_model_ref = _resolve_model_ref(
        model_ref=model_ref,
        source=source,
        modelscope_model=_env("VOXCPM_MODELSCOPE_MODEL", "OpenBMB/VoxCPM2") or "OpenBMB/VoxCPM2",
    )

    return VoxCPM.from_pretrained(
        resolved_model_ref,
        device=_env("VOXCPM_DEVICE", "cpu"),
        load_denoiser=_env_bool("VOXCPM_LOAD_DENOISER", False),
    )


@lru_cache(maxsize=1)
def get_qwen_tts_model() -> Any:
    try:
        from qwen_tts import Qwen3TTSModel  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on optional runtime dependency
        raise RuntimeError(
            "未安装 qwen-tts 依赖，请确认镜像已安装 Qwen3-TTS 所需包"
        ) from exc

    model_ref = _env("QWEN_TTS_MODEL", "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice") or "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
    source = (_env("QWEN_TTS_SOURCE", "modelscope") or "modelscope").lower()
    resolved_model_ref = _resolve_model_ref(
        model_ref=model_ref,
        source=source,
        modelscope_model=_env("QWEN_TTS_MODELSCOPE_MODEL", "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice") or "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
    )

    init_kwargs: dict[str, Any] = {
        "device_map": _env("QWEN_TTS_DEVICE_MAP", "cpu"),
    }

    dtype_name = (_env("QWEN_TTS_DTYPE") or "").strip()
    if dtype_name and dtype_name != "auto":
        try:
            import torch  # type: ignore

            init_kwargs["dtype"] = getattr(torch, dtype_name)
        except Exception:
            pass

    attn_impl = _env("QWEN_TTS_ATTN_IMPLEMENTATION")
    if attn_impl:
        init_kwargs["attn_implementation"] = attn_impl

    return Qwen3TTSModel.from_pretrained(resolved_model_ref, **init_kwargs)
