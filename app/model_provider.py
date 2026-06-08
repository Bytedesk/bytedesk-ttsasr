from functools import lru_cache
from typing import Any

from funasr import AutoModel  # type: ignore

from app.utils import _env, _env_bool


@lru_cache(maxsize=1)
def get_model() -> AutoModel:
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
