from functools import lru_cache
from typing import Any

from funasr import AutoModel  # type: ignore

from app.utils import _env, _env_bool


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

    return VoxCPM.from_pretrained(
        _env("VOXCPM_MODEL", "openbmb/VoxCPM2"),
        device=_env("VOXCPM_DEVICE", "cpu"),
        load_denoiser=_env_bool("VOXCPM_LOAD_DENOISER", False),
    )
