"""VoiceService - Main orchestrator combining TTS engine + platform sender."""

import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from hermes_tts.engines import (
    TTSEngine,
    EdgeTTSEngine,
    FishAudioEngine,
    CosyVoiceEngine,
    GPTSoVITSEngine,
)
from hermes_tts.senders import PlatformSender, FeishuSender, LocalFileSender
from hermes_tts.converter import AudioConverter

logger = logging.getLogger("hermes_tts")


class VoiceService:
    """
    Main service: text -> TTS synthesis -> format conversion -> platform delivery.

    Args:
        engine: TTS engine instance
        sender: Platform sender instance
        temp_dir: Temporary directory for audio files
    """

    def __init__(self, engine: TTSEngine, sender: PlatformSender, temp_dir: Optional[str] = None):
        self.engine = engine
        self.sender = sender
        self.temp_dir = temp_dir or tempfile.mkdtemp(prefix="hermes_tts_")

    async def speak(self, text: str, target_id: str, **kwargs) -> dict:
        """
        Synthesize text and send as voice message.

        Args:
            text: Text to synthesize
            target_id: Target user/chat ID on the platform
            **kwargs: Passed to engine.synthesize() and sender.send_voice()

        Returns:
            Platform-specific response dict
        """
        ext = ".mp3" if isinstance(self.engine, EdgeTTSEngine) else ".wav"
        audio_path = os.path.join(self.temp_dir, f"tts_output{ext}")

        audio_path = await self.engine.synthesize(text, audio_path, **kwargs)
        result = await self.sender.send_voice(audio_path, target_id, **kwargs)
        self._cleanup(audio_path)

        return result

    async def synthesize_only(self, text: str, output_path: str, fmt: str = "mp3", **kwargs) -> str:
        """Synthesize text to audio file without sending."""
        temp_path = os.path.join(self.temp_dir, f"tts_temp.{fmt}")
        await self.engine.synthesize(text, temp_path, **kwargs)

        if fmt == "ogg":
            AudioConverter.to_opus(temp_path, output_path)
        elif temp_path != output_path:
            shutil.copy2(temp_path, output_path)

        return output_path

    def _cleanup(self, *paths: str):
        for p in paths:
            try:
                path = Path(p)
                if path.exists():
                    path.unlink()
                ogg_path = path.with_suffix(".ogg")
                if ogg_path.exists():
                    ogg_path.unlink()
            except OSError:
                pass


def create_service(
    engine_type: str = "edge",
    platform: str = "feishu",
    voice: str = "zh-CN-XiaoxiaoNeural",
    **kwargs,
) -> VoiceService:
    """
    Factory function for quick setup.

    Args:
        engine_type: "edge", "fish", "cosyvoice", "gpt-sovits"
        platform: "feishu", "local"
        voice: Voice name (edge-tts only)
        **kwargs: Engine/sender specific args

    Examples:
        # Edge TTS + Feishu
        svc = create_service("edge", "feishu")
        await svc.speak("你好!", target_id="ou_xxx")

        # Fish Audio clone + Feishu
        svc = create_service("fish", "feishu", api_key="xxx", reference_id="model_id")

        # Local testing
        svc = create_service("edge", "local")
    """
    if engine_type == "edge":
        engine = EdgeTTSEngine(
            voice=voice,
            rate=kwargs.get("rate", "+0%"),
            pitch=kwargs.get("pitch", "+0Hz"),
        )
    elif engine_type == "fish":
        engine = FishAudioEngine(
            api_key=kwargs.get("api_key", os.environ.get("FISH_AUDIO_API_KEY", "")),
            reference_id=kwargs.get("reference_id"),
            reference_audio=kwargs.get("reference_audio"),
            reference_text=kwargs.get("reference_text"),
        )
    elif engine_type == "cosyvoice":
        engine = CosyVoiceEngine(
            api_url=kwargs.get("api_url", os.environ.get("COSYVOICE_API_URL", "http://localhost:9880")),
            mode=kwargs.get("mode", "zero_shot"),
            speaker=kwargs.get("speaker", ""),
            reference_audio=kwargs.get("reference_audio"),
            reference_text=kwargs.get("reference_text"),
        )
    elif engine_type == "gpt-sovits":
        engine = GPTSoVITSEngine(
            api_url=kwargs.get("api_url", "http://localhost:9880"),
            reference_audio=kwargs.get("reference_audio"),
            reference_text=kwargs.get("reference_text"),
        )
    else:
        raise ValueError(f"Unknown engine type: {engine_type}")

    if platform == "feishu":
        sender = FeishuSender(
            app_id=kwargs.get("app_id", ""),
            app_secret=kwargs.get("app_secret", ""),
        )
    elif platform == "local":
        sender = LocalFileSender(output_dir=kwargs.get("output_dir", "./voice_output"))
    else:
        raise ValueError(f"Unknown platform: {platform}")

    return VoiceService(engine=engine, sender=sender)
