# bytedesk-ttsasr

基于 FunASR 的 Docker 化语音识别服务，提供 HTTP 接口，方便被其他服务直接调用实现 ASR。

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

### OpenAI 兼容接口

```bash
curl -X POST http://localhost:8000/v1/audio/transcriptions \
  -F file=@sample.wav \
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

## 环境变量

- `FUNASR_DEVICE`: `cpu` 或 `cuda`，默认 `cpu`
- `FUNASR_MODEL`: 默认 `iic/SenseVoiceSmall`
- `FUNASR_VAD_MODEL`: 默认 `fsmn-vad`
- `FUNASR_PUNC_MODEL`: 可选，标点模型
- `FUNASR_SPK_MODEL`: 可选，说话人分离模型
- `FUNASR_HUB`: 可选，模型来源
- `FUNASR_TRUST_REMOTE_CODE`: 可选，`true/false`

如果要使用 GPU，可在宿主机已安装 NVIDIA Container Toolkit 的前提下，将 `FUNASR_DEVICE=cuda`，并按需调整容器运行参数。

## 说明

- 容器首次启动会下载模型，耗时取决于网络情况
- CPU 模式可直接运行，但识别速度较 GPU 慢
- 当前接口直接返回 FunASR 原始结果，并补充了 `filename`
- 当前镜像默认优先支持 wav、flac 等常见无损音频；如果你需要更广泛的音频格式转码能力，可在镜像中额外安装 ffmpeg
