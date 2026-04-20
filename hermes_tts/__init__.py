"""
Hermes TTS - Text-to-Speech Voice Synthesis & Delivery

Usage:
    from hermes_tts import create_service

    svc = create_service("edge", "feishu", voice="zh-CN-XiaoxiaoNeural")
    await svc.speak("Hello!", target_id="ou_xxx")
"""

from hermes_tts.engines import (
    TTSEngine,
    EdgeTTSEngine,
    FishAudioEngine,
    CosyVoiceEngine,
    GPTSoVITSEngine,
)
from hermes_tts.senders import PlatformSender, FeishuSender, LocalFileSender
from hermes_tts.converter import AudioConverter
from hermes_tts.service import VoiceService, create_service

__all__ = [
    "TTSEngine",
    "EdgeTTSEngine",
    "FishAudioEngine",
    "CosyVoiceEngine",
    "GPTSoVITSEngine",
    "AudioConverter",
    "PlatformSender",
    "FeishuSender",
    "LocalFileSender",
    "VoiceService",
    "create_service",
]
