# TODO

- [x] 将 [FunASR](https://github.com/modelscope/FunASR) 打包成 docker 镜像服务，方便在其他服务中直接调用 FunASR 接口，从而实现 ASR
- [x] TTS provider 默认使用 ModelScope
- [x] 增加支持 [qwen-tts](/Users/ningjinpeng/Desktop/Git/Github/open/Qwen3-TTS)
- [x] 支持在配置文件中配置语音文件生成目录路径
- [x] 在docker首次安装镜像时，通过配置文件控制是否默认下载模型，默认开启
- [x] 增加接口判断是否已经下载模型，并增加下载模型接口
- [x] 类“FastAPI”中的“on_event”方法已弃用
