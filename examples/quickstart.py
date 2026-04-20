"""
Hermes TTS - Quick Start Examples

Run: python examples/quickstart.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from hermes_tts import EdgeTTSEngine, VoiceService, LocalFileSender, FeishuSender, create_service


async def example_basic():
    """Basic: edge-tts + save to local file."""
    print("--- Basic Edge TTS ---")
    svc = create_service("edge", "local", voice="zh-CN-XiaoxiaoNeural")
    result = await svc.speak("你好，我是 Hermes，很高兴为你服务！", target_id="demo")
    print(f"  Result: {result}\n")


async def example_voices():
    """List available Chinese voices."""
    print("--- Available zh-CN Voices ---")
    voices = await EdgeTTSEngine.list_voices("zh-CN")
    for v in voices:
        print(f"  {v['name']:35s} {v['gender']}")
    print()


async def example_feishu():
    """Send voice via Feishu (requires env vars)."""
    print("--- Feishu Voice ---")
    app_id = os.environ.get("FEISHU_APP_ID")
    app_secret = os.environ.get("FEISHU_APP_SECRET")
    target = os.environ.get("FEISHU_TARGET_ID")

    if not all([app_id, app_secret, target]):
        print("  Skipped: set FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_TARGET_ID\n")
        return

    svc = create_service("edge", "feishu", voice="zh-CN-YunxiNeural")
    result = await svc.speak("这是 Hermes 发来的语音消息。", target_id=target, receive_id_type="open_id")
    print(f"  Sent: {result}\n")


async def example_clone():
    """Voice cloning with Fish Audio (requires API key)."""
    print("--- Fish Audio Voice Clone ---")
    api_key = os.environ.get("FISH_AUDIO_API_KEY")
    if not api_key:
        print("  Skipped: set FISH_AUDIO_API_KEY (register at https://fish.audio)\n")
        return

    svc = create_service("fish", "local", api_key=api_key, reference_id="your_model_id")
    # result = await svc.speak("克隆的声音说话了！", target_id="clone_test")
    print("  Fish Audio engine ready (set reference_id to run)\n")


async def example_hermes_integration():
    """Typical hermes agent integration pattern."""
    print("--- Hermes Integration Pattern ---")

    class HermesVoice:
        def __init__(self):
            self.service = create_service("edge", "local", voice="zh-CN-XiaoxiaoNeural")

        async def reply(self, user_id: str, text: str):
            return await self.service.speak(text=text, target_id=user_id)

        def set_voice(self, voice: str):
            self.service.engine = EdgeTTSEngine(voice=voice)

    bot = HermesVoice()
    result = await bot.reply("user_001", "Hermes 收到你的消息了")
    print(f"  Female voice: {result}")

    bot.set_voice("zh-CN-YunxiNeural")
    result = await bot.reply("user_001", "已切换到男声")
    print(f"  Male voice: {result}\n")


async def main():
    await example_basic()
    await example_voices()
    await example_feishu()
    await example_clone()
    await example_hermes_integration()
    print("All examples done!")


if __name__ == "__main__":
    asyncio.run(main())
