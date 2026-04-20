"""Platform voice message senders."""

import json
import logging
import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import httpx

from hermes_tts.converter import AudioConverter

logger = logging.getLogger("hermes_tts")


class PlatformSender(ABC):
    """Abstract base class for platform voice message senders."""

    @abstractmethod
    async def send_voice(self, audio_path: str, target_id: str, **kwargs) -> dict:
        ...


class FeishuSender(PlatformSender):
    """
    Send voice messages via Feishu (Lark) bot.
    Audio will be auto-converted to opus/ogg format.

    Args:
        app_id: Feishu app ID (or env FEISHU_APP_ID)
        app_secret: Feishu app secret (or env FEISHU_APP_SECRET)
    """

    API_BASE = "https://open.feishu.cn/open-apis"

    def __init__(self, app_id: str = "", app_secret: str = ""):
        self.app_id = app_id or os.environ.get("FEISHU_APP_ID", "")
        self.app_secret = app_secret or os.environ.get("FEISHU_APP_SECRET", "")
        if not self.app_id or not self.app_secret:
            raise ValueError("FEISHU_APP_ID and FEISHU_APP_SECRET are required (param or env var)")
        self._access_token: Optional[str] = None

    async def _get_access_token(self) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.API_BASE}/auth/v3/tenant_access_token/internal",
                json={"app_id": self.app_id, "app_secret": self.app_secret},
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"Failed to get Feishu token: {data}")
            self._access_token = data["tenant_access_token"]
        return self._access_token

    async def _upload_audio(self, audio_path: str) -> str:
        """Upload audio file to Feishu, return file_key."""
        token = await self._get_access_token()

        # Convert to opus/ogg if needed
        if not audio_path.endswith(".ogg"):
            ogg_path = str(Path(audio_path).with_suffix(".ogg"))
            AudioConverter.to_opus(audio_path, ogg_path)
            audio_path = ogg_path

        duration = AudioConverter.get_duration(audio_path)

        async with httpx.AsyncClient() as client:
            with open(audio_path, "rb") as f:
                resp = await client.post(
                    f"{self.API_BASE}/im/v1/files",
                    headers={"Authorization": f"Bearer {token}"},
                    data={
                        "file_type": "opus",
                        "file_name": Path(audio_path).name,
                        "duration": str(int(duration)),
                    },
                    files={"file": (Path(audio_path).name, f, "audio/ogg")},
                )
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise RuntimeError(f"Failed to upload audio to Feishu: {data}")

        file_key = data["data"]["file_key"]
        logger.info(f"Uploaded audio to Feishu: {file_key}")
        return file_key

    async def send_voice(self, audio_path: str, target_id: str, **kwargs) -> dict:
        """
        Send voice message via Feishu.

        Args:
            audio_path: Path to audio file
            target_id: open_id, user_id, union_id, or chat_id
            **kwargs: receive_id_type ("open_id" default, "chat_id" for groups)
        """
        receive_id_type = kwargs.get("receive_id_type", "open_id")
        file_key = await self._upload_audio(audio_path)
        token = await self._get_access_token()

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.API_BASE}/im/v1/messages",
                params={"receive_id_type": receive_id_type},
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={
                    "receive_id": target_id,
                    "msg_type": "audio",
                    "content": json.dumps({"file_key": file_key}),
                },
            )
            resp.raise_for_status()
            data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(f"Failed to send voice message: {data}")

        logger.info(f"Voice message sent to {target_id}")
        return data


class LocalFileSender(PlatformSender):
    """Save audio to local file (for testing or custom integrations)."""

    def __init__(self, output_dir: str = "./voice_output"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def send_voice(self, audio_path: str, target_id: str, **kwargs) -> dict:
        dest = self.output_dir / f"{target_id}_{Path(audio_path).name}"
        shutil.copy2(audio_path, dest)
        logger.info(f"Audio saved to: {dest}")
        return {"status": "ok", "path": str(dest)}
