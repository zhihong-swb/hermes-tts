# Hermes TTS

Hermes Agent 文字转语音合成与语音消息发送。

支持多种免费 TTS 引擎和飞书语音消息投递。

---

## 使用方式

### 一、Skill 安装

将 `voice-tts/` 目录复制到你的 agent 的 skills 目录，即可使用。

**1. 安装系统依赖**

```bash
# macOS
brew install ffmpeg

# CentOS / Alibaba Cloud Linux
yum install -y ffmpeg

# Ubuntu / Debian
apt install -y ffmpeg
```

**2. 安装 Python 依赖**

```bash
pip install edge-tts httpx
```

> 如果 agent 使用独立的 venv（如 Hermes Agent），需要指定 Python 路径安装：
> ```bash
> /home/admin/.hermes/hermes-agent/venv/bin/python3 -m pip install edge-tts httpx
> ```

**3. 复制 skill 到 agent 的 skills 目录**

```bash
git clone https://github.com/zhihong-swb/hermes-tts.git
```

```bash
# Hermes Agent
cp -r hermes-tts/voice-tts ~/.hermes/skills/

# Claude Code
cp -r hermes-tts/voice-tts ~/.claude/skills/

# OpenClaw
cp -r hermes-tts/voice-tts ~/.openclaw/skills/

# Qoder
cp -r hermes-tts/voice-tts ~/.qoder/skills/
```

**4. 配置飞书凭证（环境变量）**

```bash
export FEISHU_APP_ID="你的飞书app_id"
export FEISHU_APP_SECRET="你的飞书app_secret"
```

> Hermes Agent 用户：如果 `~/.hermes/.env` 中已有 `FEISHU_APP_ID`，无需重复配置。

**5. 验证**

```bash
# 测试合成（保存到本地）
python ~/.hermes/skills/voice-tts/scripts/speak.py \
    --text "安装成功" --target test --platform local --output-dir /tmp/test

# 测试飞书发送
python ~/.hermes/skills/voice-tts/scripts/speak.py \
    --text "语音测试" --target "ou_你的open_id"
```

### 二、声音克隆

本项目支持通过 **Fish Audio** 实现零成本语音克隆（免费额度：每天 10,000 字）。

**1. 注册 Fish Audio**

访问 https://fish.audio 注册账号，获取 API Key。

```bash
export FISH_AUDIO_API_KEY="你的api_key"
```

**2. 方式一：在 Fish Audio 网站创建声音模型（推荐）**

1. 准备 10-30 秒的清晰语音样本（WAV 格式，无背景噪音，16kHz 以上采样率）
2. 在 https://fish.audio 上传音频，创建声音模型
3. 获取模型 ID，然后使用：

```bash
python scripts/speak.py \
    --text "这是克隆的声音" \
    --target "ou_xxx" \
    --engine fish \
    --fish-model-id "你的模型ID"
```

**3. 方式二：零样本克隆（无需预创建模型）**

直接提供一段参考音频，实时克隆声音：

```bash
python scripts/speak.py \
    --text "实时克隆的声音" \
    --target "ou_xxx" \
    --engine fish \
    --reference-audio "/path/to/sample.wav" \
    --reference-text "参考音频对应的文字内容"
```

> **克隆效果提升技巧：**
> - 参考音频 10-30 秒，纯语音，无背景音乐/噪声
> - 提供 `--reference-text`（参考音频的文字转写）可显著提高克隆质量
> - 推荐 WAV 格式、16kHz 以上采样率

**4. 本地语音克隆（可选，需 GPU）**

如需完全离线的语音克隆，可部署以下开源项目：
- **CosyVoice**：https://github.com/FunAudioLLM/CosyVoice （阿里开源）
- **GPT-SoVITS**：https://github.com/RVC-Boss/GPT-SoVITS （社区热门）

---

## 功能特性

- **Edge TTS** - 免费，400+ 音色，无需 GPU，开箱即用
- **Fish Audio** - 免费额度（每天 1 万字），零样本语音克隆
- **CosyVoice** - 阿里开源，本地语音克隆
- **GPT-SoVITS** - 开源，高质量中文语音克隆
- **飞书语音消息** - 自动转码 opus 格式并通过机器人发送
- **可扩展** - 轻松添加新的 TTS 引擎或平台

## 项目结构

```
hermes-tts/
├── README.md                # 本文档
├── voice-tts/               # Agent Skill（复制到 skills 目录即用）
│   ├── SKILL.md             # Skill 指令（agent 读取）
│   ├── setup.md             # 详细安装配置教程
│   └── scripts/
│       ├── speak.py         # 语音合成 + 发送脚本
│       ├── voices.py        # 列出可用音色
│       └── requirements.txt
├── hermes_tts/              # Python 包（可选，pip install 方式使用）
│   ├── __init__.py
│   ├── engines.py
│   ├── senders.py
│   ├── converter.py
│   ├── service.py
│   └── cli.py
├── pyproject.toml
└── setup.py
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
