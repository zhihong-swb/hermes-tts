# Hermes TTS

Text-to-Speech voice synthesis & delivery for Hermes Agent.

Supports multiple TTS engines (free) and platform voice message delivery (Feishu).

## Features

- **Edge TTS** - free, 400+ voices, no GPU needed, production ready
- **Fish Audio** - free tier (10k chars/day), zero-shot voice cloning
- **CosyVoice** - open source (Alibaba), local voice cloning
- **GPT-SoVITS** - open source, high-quality Chinese voice cloning
- **Feishu voice message** - auto-convert to opus and send via bot
- **Extensible** - add new TTS engines or platforms easily

## Install

```bash
# From GitHub
pip install git+https://github.com/zhihong-swb/hermes-tts.git

# System dependency (audio format conversion)
# macOS
brew install ffmpeg
# Ubuntu/Debian
apt install -y ffmpeg
```

## Quick Start

### Basic TTS + Feishu Voice Message

```python
import asyncio
from hermes_tts import create_service

async def main():
    svc = create_service(
        engine_type="edge",       # free, no GPU
        platform="feishu",
        voice="zh-CN-XiaoxiaoNeural",  # female, warm
    )
    await svc.speak(
        text="Hello from Hermes!",
        target_id="ou_xxxxx",     # user's open_id
        receive_id_type="open_id",
    )

asyncio.run(main())
```

### Voice Cloning (Fish Audio)

```python
from hermes_tts import create_service

# Method 1: Use pre-created voice model
svc = create_service(
    engine_type="fish",
    platform="feishu",
    api_key="your_fish_audio_api_key",
    reference_id="your_model_id",
)
await svc.speak("Cloned voice!", target_id="ou_xxxxx")

# Method 2: Zero-shot clone from reference audio
svc = create_service(
    engine_type="fish",
    platform="feishu",
    api_key="your_key",
    reference_audio="path/to/sample.wav",  # 10-30s reference
    reference_text="transcript of reference audio",
)
await svc.speak("Real-time clone!", target_id="ou_xxxxx")
```

### List Available Voices

```python
from hermes_tts import EdgeTTSEngine

voices = await EdgeTTSEngine.list_voices(locale="zh-CN")
for v in voices:
    print(f"{v['name']}  {v['gender']}")
```

### CLI Usage

```bash
# List Chinese voices
hermes-tts --list-voices

# Synthesize to local file
hermes-tts "你好世界" --voice zh-CN-YunxiNeural --platform local

# Synthesize and send via Feishu
hermes-tts "你好" --platform feishu --target ou_xxxxx
```

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `FEISHU_APP_ID` | For Feishu | Feishu bot app ID |
| `FEISHU_APP_SECRET` | For Feishu | Feishu bot app secret |
| `FISH_AUDIO_API_KEY` | For voice clone | Fish Audio API key (https://fish.audio) |
| `COSYVOICE_API_URL` | For CosyVoice | Local CosyVoice server URL |

### Feishu Bot Permissions

Ensure your Feishu bot has these permissions:
- `im:message:send_as_bot` - Send messages
- `im:file` - Upload files

### Available Voices (Chinese)

| Voice | Gender | Style |
|-------|--------|-------|
| zh-CN-XiaoxiaoNeural | Female | Warm (default) |
| zh-CN-YunxiNeural | Male | Casual |
| zh-CN-XiaoyiNeural | Female | Lively |
| zh-CN-YunjianNeural | Male | Authoritative |
| zh-CN-YunyangNeural | Male | News anchor |
| zh-CN-XiaochenNeural | Female | Relaxed |

Full list: `hermes-tts --list-voices`

## Integration with Hermes Agent

```python
from hermes_tts import create_service, EdgeTTSEngine

class HermesVoicePlugin:
    def __init__(self):
        self.tts = create_service("edge", "feishu", voice="zh-CN-XiaoxiaoNeural")

    async def reply_voice(self, user_id: str, text: str):
        """Send voice reply to user."""
        return await self.tts.speak(text=text, target_id=user_id, receive_id_type="open_id")

    async def reply_voice_to_group(self, chat_id: str, text: str):
        """Send voice to group chat."""
        return await self.tts.speak(text=text, target_id=chat_id, receive_id_type="chat_id")

    def set_voice(self, voice: str):
        """Switch voice."""
        self.tts.engine = EdgeTTSEngine(voice=voice)
```

## Architecture

```
Text -> [TTS Engine] -> MP3/WAV -> [AudioConverter] -> OGG/Opus -> [PlatformSender] -> Voice Message
```

Extend by subclassing:
- `TTSEngine` - add new TTS backends
- `PlatformSender` - add new delivery platforms (Telegram, Discord, WeChat...)

## License

MIT
