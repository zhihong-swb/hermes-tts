"""Audio format converter using ffmpeg."""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional


class AudioConverter:
    """Convert audio between formats using ffmpeg."""

    @staticmethod
    def check_ffmpeg() -> bool:
        return shutil.which("ffmpeg") is not None

    @staticmethod
    def convert(input_path: str, output_path: str, codec: str = "libopus", bitrate: str = "48k") -> str:
        if not AudioConverter.check_ffmpeg():
            raise RuntimeError("ffmpeg not found. Install: brew install ffmpeg (macOS) or apt install ffmpeg (Linux)")
        cmd = [
            "ffmpeg", "-i", input_path,
            "-c:a", codec, "-b:a", bitrate,
            "-vn", "-y", output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg conversion failed: {result.stderr}")
        return output_path

    @staticmethod
    def to_opus(input_path: str, output_path: Optional[str] = None) -> str:
        """Convert to opus/ogg format (required by Feishu voice messages)."""
        if output_path is None:
            output_path = str(Path(input_path).with_suffix(".ogg"))
        return AudioConverter.convert(input_path, output_path, codec="libopus", bitrate="48k")

    @staticmethod
    def get_duration(file_path: str) -> float:
        """Get audio duration in seconds."""
        cmd = ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "json", file_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe failed: {result.stderr}")
        data = json.loads(result.stdout)
        return float(data["format"]["duration"])
