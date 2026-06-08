FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    FUNASR_DEVICE=cpu \
    FUNASR_MODEL=iic/SenseVoiceSmall \
    FUNASR_VAD_MODEL=fsmn-vad \
    FUNASR_PRELOAD=false \
    VOXCPM_MODEL=openbmb/VoxCPM2 \
    VOXCPM_SOURCE=modelscope \
    VOXCPM_MODELSCOPE_MODEL=OpenBMB/VoxCPM2 \
    VOXCPM_DEVICE=cpu \
    VOXCPM_LOAD_DENOISER=false \
    VOXCPM_PRELOAD=false \
    QWEN_TTS_MODEL=Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice \
    QWEN_TTS_SOURCE=modelscope \
    QWEN_TTS_MODELSCOPE_MODEL=Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice \
    QWEN_TTS_DEVICE_MAP=cpu \
    QWEN_TTS_LANGUAGE=Auto \
    QWEN_TTS_SPEAKER=Vivian \
    QWEN_TTS_PRELOAD=false \
    TTS_OUTPUT_DIR=

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libsndfile1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-build-isolation -r requirements.txt

COPY app ./app

# 构建时模型下载控制（通过 --build-arg 覆盖）
# DOWNLOAD_MODELS_ON_BUILD  总开关，默认 true
# FUNASR_DOWNLOAD_ON_BUILD  是否下载 ASR 模型，默认 true
# VOXCPM_DOWNLOAD_ON_BUILD  是否下载 VoxCPM（约 4.3GB），默认 false
# QWEN_TTS_DOWNLOAD_ON_BUILD 是否下载 Qwen3-TTS（约 3.6GB），默认 false
ARG DOWNLOAD_MODELS_ON_BUILD=true
ARG FUNASR_DOWNLOAD_ON_BUILD=true
ARG VOXCPM_DOWNLOAD_ON_BUILD=false
ARG QWEN_TTS_DOWNLOAD_ON_BUILD=false

RUN DOWNLOAD_MODELS_ON_BUILD=${DOWNLOAD_MODELS_ON_BUILD} \
    FUNASR_DOWNLOAD_ON_BUILD=${FUNASR_DOWNLOAD_ON_BUILD} \
    VOXCPM_DOWNLOAD_ON_BUILD=${VOXCPM_DOWNLOAD_ON_BUILD} \
    QWEN_TTS_DOWNLOAD_ON_BUILD=${QWEN_TTS_DOWNLOAD_ON_BUILD} \
    python app/download_models.py

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]