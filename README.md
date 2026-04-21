# Hermes TTS

Hermes Agent 文字转语音合成与语音消息发送。

支持多种免费 TTS 引擎和飞书语音消息投递。

## 功能特性

- **Edge TTS** - 免费，400+ 音色，无需 GPU，开箱即用
- **Fish Audio** - 免费额度（每天 1 万字），零样本语音克隆
- **CosyVoice** - 阿里开源，本地语音克隆
- **GPT-SoVITS** - 开源，高质量中文语音克隆
- **飞书语音消息** - 自动转码 opus 格式并通过机器人发送
- **可扩展** - 轻松添加新的 TTS 引擎或平台

## 项目结构

本项目包含两部分：

### 1. Python 包（`hermes_tts/`）

可通过 pip 安装的 Python 库，适合在代码中直接调用。

### 2. Agent Skill（`voice-tts/`）

自包含的 skill 目录，复制到 agent 的 skills 目录即可使用（支持 Hermes Agent / Claude Code / Qoder）。详见 [voice-tts/setup.md](voice-tts/setup.md)。

## 安装

```bash
# 方式一：pip 安装 Python 包
pip install git+https://github.com/zhihong-swb/hermes-tts.git

# 方式二：作为 skill 使用（复制到 agent skills 目录）
git clone https://github.com/zhihong-swb/hermes-tts.git
cp -r hermes-tts/voice-tts ~/.hermes/skills/

# 系统依赖（音频格式转换）
# macOS
brew install ffmpeg
# CentOS
yum install -y ffmpeg
# Ubuntu/Debian
apt install -y ffmpeg
```

## 快速开始

### 基础 TTS + 飞书语音消息

```python
import asyncio
from hermes_tts import create_service

async def main():
    svc = create_service(
        engine_type="edge",                    # 免费，无需 GPU
        platform="feishu",
        voice="zh-CN-XiaoxiaoNeural",          # 女声，温暖亲切
    )
    await svc.speak(
        text="你好，我是 Hermes！",
        target_id="ou_xxxxx",                  # 用户的 open_id
        receive_id_type="open_id",
    )

asyncio.run(main())
```

### 语音克隆（Fish Audio）

```python
from hermes_tts import create_service

# 方式一：使用已创建的声音模型
svc = create_service(
    engine_type="fish",
    platform="feishu",
    api_key="你的_fish_audio_api_key",
    reference_id="你的模型ID",
)
await svc.speak("克隆的声音说话了！", target_id="ou_xxxxx")

# 方式二：零样本克隆（提供参考音频）
svc = create_service(
    engine_type="fish",
    platform="feishu",
    api_key="你的_api_key",
    reference_audio="path/to/sample.wav",      # 10-30 秒参考音频
    reference_text="参考音频的文字内容",
)
await svc.speak("实时克隆！", target_id="ou_xxxxx")
```

### 列出可用音色

```python
from hermes_tts import EdgeTTSEngine

voices = await EdgeTTSEngine.list_voices(locale="zh-CN")
for v in voices:
    print(f"{v['name']}  {v['gender']}")
```

### 命令行使用

```bash
# 列出中文音色
hermes-tts --list-voices

# 合成到本地文件
hermes-tts "你好世界" --voice zh-CN-YunxiNeural --platform local

# 合成并通过飞书发送
hermes-tts "你好" --platform feishu --target ou_xxxxx
```

### Skill 脚本使用

```bash
# 发送语音消息
python scripts/speak.py --text "你好" --target "ou_xxx"

# 列出音色
python scripts/voices.py
```

## 配置

### 环境变量

| 变量 | 必填条件 | 说明 |
|------|----------|------|
| `FEISHU_APP_ID` | 使用飞书时 | 飞书机器人 App ID |
| `FEISHU_APP_SECRET` | 使用飞书时 | 飞书机器人 App Secret |
| `FISH_AUDIO_API_KEY` | 使用语音克隆时 | Fish Audio API 密钥（https://fish.audio） |
| `COSYVOICE_API_URL` | 使用 CosyVoice 时 | 本地 CosyVoice 服务地址 |

### 飞书机器人权限

确保机器人已开通以下权限：
- `im:message:send_as_bot` - 发送消息
- `im:file` - 上传文件

### 可用中文音色

| 音色 | 性别 | 风格 |
|------|------|------|
| zh-CN-XiaoxiaoNeural | 女 | 温暖亲切（默认） |
| zh-CN-YunxiNeural | 男 | 年轻休闲 |
| zh-CN-XiaoyiNeural | 女 | 活泼开朗 |
| zh-CN-YunjianNeural | 男 | 沉稳权威 |
| zh-CN-YunyangNeural | 男 | 新闻播报 |
| zh-CN-XiaochenNeural | 女 | 轻松自然 |

完整列表：`hermes-tts --list-voices`

## 集成 Hermes Agent

```python
from hermes_tts import create_service, EdgeTTSEngine

class HermesVoicePlugin:
    def __init__(self):
        self.tts = create_service("edge", "feishu", voice="zh-CN-XiaoxiaoNeural")

    async def reply_voice(self, user_id: str, text: str):
        """给用户发送语音回复"""
        return await self.tts.speak(text=text, target_id=user_id, receive_id_type="open_id")

    async def reply_voice_to_group(self, chat_id: str, text: str):
        """给群聊发送语音"""
        return await self.tts.speak(text=text, target_id=chat_id, receive_id_type="chat_id")

    def set_voice(self, voice: str):
        """切换音色"""
        self.tts.engine = EdgeTTSEngine(voice=voice)
```

## 架构

```
文字 -> [TTS 引擎] -> MP3/WAV -> [音频转换器] -> OGG/Opus -> [平台发送器] -> 语音消息
```

扩展方式：
- 继承 `TTSEngine` - 添加新的 TTS 引擎
- 继承 `PlatformSender` - 添加新的平台（Telegram、Discord、微信等）

## 许可证

MIT
