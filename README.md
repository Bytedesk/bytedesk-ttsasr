# bytedesk-ttsasr

基于 FunASR + 多 TTS Provider（VoxCPM / Qwen3-TTS）的 Docker 化语音服务，提供 HTTP 接口，方便被其他服务直接调用实现 ASR 和 TTS。

**Language:** [English](README.md) | [中文](README.zh.md)

## 功能

- 上传音频文件后返回识别结果
- 文本转语音，返回 wav 音频流
- 默认使用 `iic/SenseVoiceSmall + fsmn-vad`
- 默认使用 `openbmb/VoxCPM2` 提供 TTS，并支持 `qwen-tts`
- 支持通过环境变量切换模型、设备和可选能力
- 适合以 Docker / Docker Compose 方式部署

## 目录结构

```text
.
├── .github
│   └── workflows
│       └── ttsasr-docker.yml
├── app
│   ├── download_models.py
│   ├── main.py
│   ├── model_provider.py
│   └── utils.py
├── Dockerfile
├── docker-compose.yml
├── README.md
├── README.zh.md
├── TODO.md
├── LICENSE
└── requirements.txt
```

## 接口

服务默认监听 `8000` 端口，以下示例均假设服务地址为 `http://localhost:8000`。

接口列表：

- `GET /health`: 健康检查
- `GET /v1/models/download-status`: 查询模型下载状态
- `POST /v1/models/download`: 主动下载模型
- `POST /v1/asr/transcriptions`: ASR 转写
- `POST /v1/audio/transcriptions`: OpenAI 兼容 ASR 转写
- `POST /v1/audio/speech`: OpenAI 兼容 TTS

### 健康检查

```bash
curl http://localhost:8000/health
```

返回示例：

```json
{
  "status": "ok"
}
```

### 模型下载状态

支持的模型名：`funasr`、`voxcpm`、`qwen-tts`。

查询全部模型状态：

```bash
curl http://localhost:8000/v1/models/download-status
```

查询指定模型状态：

```bash
curl 'http://localhost:8000/v1/models/download-status?model=funasr'
```

触发模型下载：

```bash
curl -X POST http://localhost:8000/v1/models/download \
  -H 'Content-Type: application/json' \
  -d '{"model":"qwen-tts"}'
```

查询返回示例：

```json
{
  "data": [
    {
      "model": "funasr",
      "display_name": "FunASR",
      "downloaded": true,
      "items": [
        {
          "model_id": "iic/SenseVoiceSmall",
          "downloaded": true
        },
        {
          "model_id": "fsmn-vad",
          "downloaded": true
        }
      ]
    }
  ]
}
```

下载返回示例：

```json
{
  "message": "模型 Qwen3-TTS 下载完成",
  "data": {
    "model": "qwen-tts",
    "display_name": "Qwen3-TTS",
    "downloaded": true,
    "items": [
      {
        "model_id": "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice",
        "downloaded": true
      }
    ]
  }
}
```

说明：

- `GET /v1/models/download-status`: 不传 `model` 时返回全部模型状态；传入 `model` 时返回单个模型状态
- `POST /v1/models/download`: 请求体为 JSON，格式为 `{"model":"funasr"}`
- 当 `model` 不合法时，接口返回 `400`

### 语音识别

请求方式：`multipart/form-data`

```bash
curl -X POST http://localhost:8000/v1/asr/transcriptions \
  -F file=@sample.wav \
  -F language=auto
```

也支持通过音频 URL 识别（`file` 与 `url` 二选一）：

```bash
curl -X POST http://localhost:8000/v1/asr/transcriptions \
  -F 'url=https://example.com/sample.wav' \
  -F language=auto
```

### OpenAI 兼容接口

```bash
curl -X POST http://localhost:8000/v1/audio/transcriptions \
  -F file=@sample.wav \
  -F model=funasr \
  -F response_format=json
```

URL 方式示例：

```bash
curl -X POST http://localhost:8000/v1/audio/transcriptions \
  -F 'url=https://sip.weiyuai.cn/freeswitch-recordings/ivr-5002_013311156272_1846b772-f8d2-4324-b6f5-8d1742208f1f_2026-06-05-17-40-11.wav' \
  -F model=funasr \
  -F response_format=json
```

返回示例：

```json
{
  "text": "你好，欢迎使用 FunASR 服务",
  "filename": "sample.wav",
  "raw": [
    {
      "text": "你好，欢迎使用 FunASR 服务"
    }
  ]
}
```

可选表单参数：

- `language`: 默认 `auto`
- `file` / `url`: 二选一，分别表示上传文件或远程音频地址（仅支持 `http/https`）
- `hotword`: 热词，多个词可用空格分隔
- `batch_size`: 默认 `1`
- `response_format`: 支持 `json` 和 `text`

约束：

- `file` 和 `url` 必须二选一，同时为空或同时传入都会返回 `400`
- 远程音频下载大小受 `FUNASR_MAX_URL_FILE_SIZE` 控制，默认 `50MB`

### OpenAI 兼容 TTS

请求方式同时支持 `application/json` 和 `multipart/form-data`。

```bash
curl -X POST http://localhost:8000/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "voxcpm",
    "input": "你好，欢迎使用 Bytedesk 语音服务。",
    "voice": "年轻女声，温柔自然",
    "response_format": "wav"
  }' \
  --output speech.wav
```

说明：

- `input`: 必填，要合成的文本
- `model`: TTS provider，支持 `voxcpm`（默认）和 `qwen-tts`
- `voice`: 可选，除 `default` 外会作为 VoxCPM 的音色描述前缀拼接到文本前，例如 `(年轻女声，温柔自然)你好`
- `response_format`: 当前仅支持 `wav`
- `cfg_value`: 可选，默认 `2.0`
- `inference_timesteps`: 可选，默认 `10`

使用 Qwen3-TTS（CustomVoice）示例：

```bash
curl -X POST http://localhost:8000/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "qwen-tts",
    "input": "你好，欢迎使用 Qwen3-TTS。",
    "voice": "语气轻快自然",
    "language": "Chinese",
    "response_format": "wav"
  }' \
  --output qwen_tts.wav
```

使用 Qwen3-TTS（Base）克隆示例：

```bash
curl -X POST http://localhost:8000/v1/audio/speech \
  -F model='qwen-tts' \
  -F input='这是一个 Qwen3-TTS 克隆示例。' \
  -F language='Chinese' \
  -F reference_audio=@voice.wav \
  -F prompt_text='参考音频对应文本。' \
  --output qwen_clone.wav
```

声音克隆示例，支持上传参考音频或传 URL：

```bash
curl -X POST http://localhost:8000/v1/audio/speech \
  -F input='这是一个声音克隆示例。' \
  -F reference_audio=@voice.wav \
  --output clone.wav
```

高保真续写示例：

```bash
curl -X POST http://localhost:8000/v1/audio/speech \
  -F input='这是一个高保真声音克隆示例。' \
  -F prompt_audio=@voice.wav \
  -F prompt_text='参考音频对应的文本。' \
  -F reference_audio=@voice.wav \
  --output hifi_clone.wav
```

克隆相关参数：

- `reference_audio` / `reference_audio_url`: 可选，参考音频，二选一
- `prompt_audio` / `prompt_audio_url`: 可选，提示音频，二选一
- `prompt_text`: 可选，提示音频的文本内容；与 `prompt_audio` 配合可实现高保真续写

  返回说明：

  - 成功时直接返回 `audio/wav` 二进制内容
  - 响应头会附带 `X-Speech-Model` 和 `X-TTS-Provider`
  - `response_format` 当前仅支持 `wav`，否则返回 `400`

  使用建议：

  - `voxcpm` 适合通用 TTS；`qwen-tts` 适合自定义音色和克隆场景
  - 如果使用 Qwen Base 模型进行克隆，建议同时传入 `reference_audio` 和 `prompt_text`
  - `reference_audio` 与 `reference_audio_url` 不能同时传，`prompt_audio` 与 `prompt_audio_url` 不能同时传

## 快速启动

### 方式一：Docker Compose

```bash
docker compose up --build
```

### 方式二：Docker

```bash
docker build -t bytedesk-ttsasr .
docker run --rm -p 8000:8000 bytedesk-ttsasr
```

### 方式三：本地 Python 直接运行（不使用 Docker）

- 创建并激活虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
```

- 安装依赖

```bash
pip install -r requirements.txt
```

- 启动服务

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- 验证服务

```bash
curl http://localhost:8000/health
```

如需切换模型或设备，可先设置环境变量再启动，例如：

```bash
export FUNASR_DEVICE=cpu
export FUNASR_MODEL=iic/SenseVoiceSmall
export FUNASR_PRELOAD=false
export VOXCPM_MODEL=openbmb/VoxCPM2
export VOXCPM_SOURCE=modelscope
export VOXCPM_MODELSCOPE_MODEL=OpenBMB/VoxCPM2
export VOXCPM_DEVICE=cpu
export QWEN_TTS_MODEL=Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice
export QWEN_TTS_SOURCE=modelscope
export QWEN_TTS_MODELSCOPE_MODEL=Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice
export QWEN_TTS_DEVICE_MAP=cpu
export QWEN_TTS_LANGUAGE=Auto
export QWEN_TTS_SPEAKER=Vivian
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## 环境变量

- `FUNASR_DEVICE`: `cpu` 或 `cuda`，默认 `cpu`
- `FUNASR_MODEL`: 默认 `iic/SenseVoiceSmall`
- `FUNASR_VAD_MODEL`: 默认 `fsmn-vad`
- `FUNASR_PUNC_MODEL`: 可选，标点模型
- `FUNASR_SPK_MODEL`: 可选，说话人分离模型
- `FUNASR_HUB`: 可选，模型来源
- `FUNASR_TRUST_REMOTE_CODE`: 可选，`true/false`
- `FUNASR_MAX_URL_FILE_SIZE`: 可选，URL 下载音频最大字节数，默认 `52428800`（50MB）
- `FUNASR_PRELOAD`: 是否在服务启动时预加载 ASR 模型，默认 `false`
- `VOXCPM_MODEL`: 默认 `openbmb/VoxCPM2`
- `VOXCPM_SOURCE`: 模型来源，支持 `auto`、`huggingface`、`modelscope`，默认 `modelscope`
- `VOXCPM_MODELSCOPE_MODEL`: ModelScope 模型名，默认 `OpenBMB/VoxCPM2`
- `VOXCPM_DEVICE`: 默认 `cpu`，可按需设置为 `cuda`
- `VOXCPM_LOAD_DENOISER`: 是否加载 denoiser，默认 `false`
- `VOXCPM_PRELOAD`: 容器启动时是否预加载 TTS 模型，默认 `false`
- `TTS_PROVIDER`: 默认 TTS provider，支持 `voxcpm` 和 `qwen-tts`，默认 `voxcpm`
- `QWEN_TTS_MODEL`: 默认 `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice`
- `QWEN_TTS_SOURCE`: 模型来源，支持 `auto`、`huggingface`、`modelscope`，默认 `modelscope`
- `QWEN_TTS_MODELSCOPE_MODEL`: ModelScope 模型名，默认 `Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice`
- `QWEN_TTS_DEVICE_MAP`: 默认 `cpu`
- `QWEN_TTS_LANGUAGE`: 默认 `Auto`
- `QWEN_TTS_SPEAKER`: CustomVoice 默认说话人，默认 `Vivian`
- `QWEN_TTS_PRELOAD`: 容器启动时是否预加载 Qwen TTS 模型，默认 `false`
- `TTS_OUTPUT_DIR`: 可选，语音文件生成目录路径；设置后每次 TTS 请求都会在该目录额外保存一份 wav 文件，文件名格式为 `{provider}_{timestamp}_{uuid}.wav`；留空（默认）则不保存

## 构建参数（Build Args）

通过 `docker build --build-arg` 或 `docker-compose.yml` 的 `build.args` 控制构建期行为：

- `DOWNLOAD_MODELS_ON_BUILD`: 构建时是否下载模型，总开关，默认 `true`
- `FUNASR_DOWNLOAD_ON_BUILD`: 是否下载 FunASR ASR 模型，默认 `true`
- `VOXCPM_DOWNLOAD_ON_BUILD`: 是否下载 VoxCPM 模型（约 4.3GB），默认 `false`
- `QWEN_TTS_DOWNLOAD_ON_BUILD`: 是否下载 Qwen3-TTS 模型（约 3.6GB），默认 `false`

跳过所有模型下载（构建最快，应用启动后按需下载）：

```bash
docker build --build-arg DOWNLOAD_MODELS_ON_BUILD=false -t bytedesk-ttsasr .
```

构建时同时下载 VoxCPM：

```bash
docker build \
  --build-arg VOXCPM_DOWNLOAD_ON_BUILD=true \
  -t bytedesk-ttsasr .
```

如果要使用 GPU，可在宿主机已安装 NVIDIA Container Toolkit 的前提下，将 `FUNASR_DEVICE=cuda`，并按需调整容器运行参数。

## 说明

- 容器首次启动会下载模型，耗时取决于网络情况
- CPU 模式可直接运行，但识别速度较 GPU 慢
- 默认不在启动阶段预加载 ASR/TTS，模型会在首次对应请求时下载并加载
- 默认 `VOXCPM_SOURCE=modelscope`，优先从 ModelScope 下载 VoxCPM；如需切换可改为 `auto` 或 `huggingface`
- Qwen3-TTS 同样支持 ModelScope 下载，且可通过 `/v1/audio/speech` 的 `model=qwen-tts` 启用
- VoxCPM 体积较大，首次请求 TTS 时会额外下载模型
- 可通过 `/v1/models/download-status` 查看 `funasr`、`voxcpm`、`qwen-tts` 是否已缓存，并通过 `/v1/models/download` 主动下载
- 当前接口直接返回 FunASR 原始结果，并补充了 `filename`
- `/v1/audio/speech` 当前返回 `audio/wav`，适合直接对接 OpenAI 风格 TTS 调用
- 当前镜像默认优先支持 wav、flac 等常见无损音频；如果你需要更广泛的音频格式转码能力，可在镜像中额外安装 ffmpeg

## Server

- [Bytedesk](https://github.com/Bytedesk/bytedesk)

## Open Source Demo + SDK

|Project|Description|Forks|Stars|
|---|---|---|---|
|[iOS](https://github.com/bytedesk/bytedesk-swift)|iOS|![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-swift)|![GitHub Repo stars](https://img.shields.io/github/stars/Bytedesk/bytedesk-swift)|
|[Android](https://github.com/bytedesk/bytedesk-android)|Android|![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-android)|![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-android)|
|[Flutter](https://github.com/bytedesk/bytedesk-flutter)|Flutter|![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-flutter)|![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-flutter)|
|[UniApp](https://github.com/bytedesk/bytedesk-uniapp)|Uniapp|![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-uniapp)|![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-uniapp)|
|[Web](https://github.com/bytedesk/bytedesk-web)|Vue/React/Angular/Next.js/JQuery/...|![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-web)|![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-web)|
|[Wordpress](https://github.com/bytedesk/bytedesk-wordpress)|Wordpress|![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-wordpress)|![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-wordpress)|
|[Woocommerce](https://github.com/bytedesk/bytedesk-woocommerce)|woocommerce|![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-woocommerce)|![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-woocommerce)|
<!-- |[Magento](https://github.com/bytedesk/bytedesk-magento)|Magento|![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-magento)|![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-magento)|
|[Prestashop](https://github.com/bytedesk/bytedesk-prestashop)|Prestashop|![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-prestashop)|![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-prestashop)|
|[Shopify](https://github.com/bytedesk/bytedesk-shopify)|Shopify|![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-shopify)|![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-shopify)|
|[Opencart](https://github.com/bytedesk/bytedesk-opencart)|Opencart|![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-opencart)|![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-opencart)|
|[Laravel](https://github.com/bytedesk/bytedesk-laravel)|Laravel|![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-laravel)|![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-laravel)|
|[Django](https://github.com/bytedesk/bytedesk-django)|Django|![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-django)|![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-django)| -->
