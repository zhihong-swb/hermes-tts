"""TTS engine implementations."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import edge_tts
import httpx

logger = logging.getLogger("hermes_tts")


class TTSEngine(ABC):
    """Abstract base class for TTS engines."""

    @abstractmethod
    async def synthesize(self, text: str, output_path: str, **kwargs) -> str:
        """Synthesize text to audio file. Returns output file path."""
        ...

    @staticmethod
    async def list_voices(**kwargs) -> list:
        return []


class EdgeTTSEngine(TTSEngine):
    """
    Microsoft Edge TTS - free, 400+ voices, no GPU needed.

    Args:
        voice: Voice name (e.g. "zh-CN-XiaoxiaoNeural")
        rate: Speed adjustment ("-50%" to "+100%")
        pitch: Pitch adjustment ("-50Hz" to "+50Hz")
    """

    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural", rate: str = "+0%", pitch: str = "+0Hz"):
        self.voice = voice
        self.rate = rate
        self.pitch = pitch

    async def synthesize(self, text: str, output_path: str, **kwargs) -> str:
        communicate = edge_tts.Communicate(
            text=text,
            voice=self.voice,
            rate=self.rate,
            pitch=self.pitch,
        )
        await communicate.save(output_path)
        logger.info(f"Edge TTS synthesized: {output_path}")
        return output_path

    @staticmethod
    async def list_voices(locale: str = "zh-CN") -> list:
        voices = await edge_tts.list_voices()
        if locale:
            voices = [v for v in voices if locale.lower() in v["Locale"].lower()]
        return [
            {
                "name": v["ShortName"],
                "gender": v["Gender"],
                "locale": v["Locale"],
                "friendly_name": v.get("FriendlyName", ""),
            }
            for v in voices
        ]


class FishAudioEngine(TTSEngine):
    """
    Fish Audio TTS with voice cloning.
    Free tier: 10,000 chars/day. https://fish.audio

    Args:
        api_key: Fish Audio API key
        reference_id: Pre-uploaded voice model ID
        reference_audio: Path to reference audio for zero-shot cloning (10-30s)
        reference_text: Transcript of reference audio (improves quality)
        format: Output format (mp3, wav, opus, flac)
    """

    API_BASE = "https://api.fish.audio"

    def __init__(
        self,
        api_key: str,
        reference_id: Optional[str] = None,
        reference_audio: Optional[str] = None,
        reference_text: Optional[str] = None,
        format: str = "mp3",
    ):
        self.api_key = api_key
        self.reference_id = reference_id
        self.reference_audio = reference_audio
        self.reference_text = reference_text
        self.format = format

    async def synthesize(self, text: str, output_path: str, **kwargs) -> str:
        ref_audio = kwargs.get("reference_audio", self.reference_audio)
        ref_text = kwargs.get("reference_text", self.reference_text)
        ref_id = kwargs.get("reference_id", self.reference_id)

        async with httpx.AsyncClient(timeout=60.0) as client:
            if ref_id:
                resp = await client.post(
                    f"{self.API_BASE}/v1/tts",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"text": text, "reference_id": ref_id, "format": self.format},
                )
            elif ref_audio:
                with open(ref_audio, "rb") as f:
                    files = {"file": ("reference.wav", f, "audio/wav")}
                    data = {"text": text, "format": self.format}
                    if ref_text:
                        data["reference_text"] = ref_text
                    resp = await client.post(
                        f"{self.API_BASE}/v1/tts",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        data=data,
                        files=files,
                    )
            else:
                raise ValueError("FishAudioEngine requires either reference_id or reference_audio")

            resp.raise_for_status()
            Path(output_path).write_bytes(resp.content)

        logger.info(f"Fish Audio synthesized: {output_path}")
        return output_path

    async def create_voice_model(self, name: str, audio_paths: list, description: str = "") -> str:
        """Upload audio samples to create a reusable voice model."""
        async with httpx.AsyncClient(timeout=120.0) as client:
            files = [("files", (Path(p).name, open(p, "rb"), "audio/wav")) for p in audio_paths]
            resp = await client.post(
                f"{self.API_BASE}/v1/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                data={"name": name, "description": description},
                files=files,
            )
            resp.raise_for_status()
            model_id = resp.json()["id"]
        logger.info(f"Created Fish Audio voice model: {model_id}")
        return model_id


class CosyVoiceEngine(TTSEngine):
    """
    CosyVoice TTS (Alibaba open source) - local deployment with voice cloning.
    GitHub: https://github.com/FunAudioLLM/CosyVoice

    Args:
        api_url: CosyVoice API server URL
        mode: "zero_shot", "cross_lingual", or "sft"
        speaker: Speaker name for SFT mode (e.g. "中文女")
        reference_audio: Reference audio for clone modes
        reference_text: Transcript (required for zero_shot)
    """

    def __init__(
        self,
        api_url: str = "http://localhost:9880",
        mode: str = "zero_shot",
        speaker: str = "",
        reference_audio: Optional[str] = None,
        reference_text: Optional[str] = None,
    ):
        self.api_url = api_url.rstrip("/")
        self.mode = mode
        self.speaker = speaker
        self.reference_audio = reference_audio
        self.reference_text = reference_text

    async def synthesize(self, text: str, output_path: str, **kwargs) -> str:
        ref_audio = kwargs.get("reference_audio", self.reference_audio)
        ref_text = kwargs.get("reference_text", self.reference_text)
        mode = kwargs.get("mode", self.mode)

        async with httpx.AsyncClient(timeout=120.0) as client:
            if mode == "sft":
                resp = await client.post(
                    f"{self.api_url}/inference_sft",
                    json={"tts_text": text, "spk_id": self.speaker},
                )
            elif mode == "zero_shot":
                if not ref_audio or not ref_text:
                    raise ValueError("zero_shot mode requires reference_audio and reference_text")
                with open(ref_audio, "rb") as f:
                    resp = await client.post(
                        f"{self.api_url}/inference_zero_shot",
                        data={"tts_text": text, "prompt_text": ref_text},
                        files={"prompt_wav": ("ref.wav", f, "audio/wav")},
                    )
            elif mode == "cross_lingual":
                if not ref_audio:
                    raise ValueError("cross_lingual mode requires reference_audio")
                with open(ref_audio, "rb") as f:
                    resp = await client.post(
                        f"{self.api_url}/inference_cross_lingual",
                        data={"tts_text": text},
                        files={"prompt_wav": ("ref.wav", f, "audio/wav")},
                    )
            else:
                raise ValueError(f"Unknown CosyVoice mode: {mode}")

            resp.raise_for_status()
            Path(output_path).write_bytes(resp.content)

        logger.info(f"CosyVoice synthesized ({mode}): {output_path}")
        return output_path


class GPTSoVITSEngine(TTSEngine):
    """
    GPT-SoVITS TTS - local deployment with voice cloning.
    GitHub: https://github.com/RVC-Boss/GPT-SoVITS

    Args:
        api_url: GPT-SoVITS API server URL
        reference_audio: Reference audio path
        reference_text: Reference audio transcript
        reference_lang: Reference audio language ("zh", "en", "ja")
    """

    def __init__(
        self,
        api_url: str = "http://localhost:9880",
        reference_audio: Optional[str] = None,
        reference_text: Optional[str] = None,
        reference_lang: str = "zh",
    ):
        self.api_url = api_url.rstrip("/")
        self.reference_audio = reference_audio
        self.reference_text = reference_text
        self.reference_lang = reference_lang

    async def synthesize(self, text: str, output_path: str, **kwargs) -> str:
        ref_audio = kwargs.get("reference_audio", self.reference_audio)
        ref_text = kwargs.get("reference_text", self.reference_text)
        ref_lang = kwargs.get("reference_lang", self.reference_lang)

        params = {"text": text, "text_language": "zh"}
        if ref_audio:
            params["refer_wav_path"] = ref_audio
        if ref_text:
            params["prompt_text"] = ref_text
            params["prompt_language"] = ref_lang

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.get(self.api_url, params=params)
            resp.raise_for_status()
            Path(output_path).write_bytes(resp.content)

        logger.info(f"GPT-SoVITS synthesized: {output_path}")
        return output_path
