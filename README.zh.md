# bytedesk-ttsasr

基于 FunASR 的 Docker 化语音识别服务，提供 HTTP 接口，方便被其他服务直接调用实现 ASR。

**语言 / Language:** [中文](README.zh.md) | [English](README.md)

## 功能

- 上传音频文件后返回识别结果
- 默认使用 `iic/SenseVoiceSmall + fsmn-vad`
- 支持通过环境变量切换模型、设备和可选能力
- 适合以 Docker / Docker Compose 方式部署

## 目录结构

```text
.
├── app
│   └── main.py
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 接口

### 健康检查

```bash
curl http://localhost:8000/health
```

### 语音识别

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

如果要使用 GPU，可在宿主机已安装 NVIDIA Container Toolkit 的前提下，将 `FUNASR_DEVICE=cuda`，并按需调整容器运行参数。

## 说明

- 容器首次启动会下载模型，耗时取决于网络情况
- CPU 模式可直接运行，但识别速度较 GPU 慢
- 当前接口直接返回 FunASR 原始结果，并补充了 `filename`
- 当前镜像默认优先支持 wav、flac 等常见无损音频；如果你需要更广泛的音频格式转码能力，可在镜像中额外安装 ffmpeg


## 服务器

- [Bytedesk](https://github.com/Bytedesk/bytedesk)

## 开源Demo + SDK

| Project | Description | Forks | Stars |
| --- | --- | --- | --- |
| [iOS](https://github.com/bytedesk/bytedesk-swift) | iOS | ![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-swift) | ![GitHub Repo stars](https://img.shields.io/github/stars/Bytedesk/bytedesk-swift) |
| [Android](https://github.com/bytedesk/bytedesk-android) | Android | ![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-android) | ![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-android) |
| [Flutter](https://github.com/bytedesk/bytedesk-flutter) | Flutter | ![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-flutter) | ![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-flutter) |
| [UniApp](https://github.com/bytedesk/bytedesk-uniapp) | Uniapp | ![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-uniapp) | ![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-uniapp) |
| [Web](https://github.com/bytedesk/bytedesk-web) | Vue/React/Angular/Next.js/JQuery/... | ![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-web) | ![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-web) |
| [Wordpress](https://github.com/bytedesk/bytedesk-wordpress) | Wordpress | ![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-wordpress) | ![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-wordpress) |
| [Woocommerce](https://github.com/bytedesk/bytedesk-woocommerce) | woocommerce | ![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-woocommerce) | ![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-woocommerce) |
<!-- |[Magento](https://github.com/bytedesk/bytedesk-magento)|Magento|![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-magento)|![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-magento)|
|[Prestashop](https://github.com/bytedesk/bytedesk-prestashop)|Prestashop|![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-prestashop)|![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-prestashop)|
|[Shopify](https://github.com/bytedesk/bytedesk-shopify)|Shopify|![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-shopify)|![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-shopify)|
|[Opencart](https://github.com/bytedesk/bytedesk-opencart)|Opencart|![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-opencart)|![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-opencart)|
|[Laravel](https://github.com/bytedesk/bytedesk-laravel)|Laravel|![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-laravel)|![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-laravel)|
|[Django](https://github.com/bytedesk/bytedesk-django)|Django|![GitHub forks](https://img.shields.io/github/forks/bytedesk/bytedesk-django)|![GitHub Repo stars](https://img.shields.io/github/stars/bytedesk/bytedesk-django)| -->
