"""FFmpeg-backed conversions."""

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .base import ConversionError

VORBIS_QUALITY = "6"
MP3_QUALITY = "0"
H264_CRF = "15"
H264_PRESET = "slow"
AAC_BITRATE = "320k"


def get_ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise ConversionError(
            "imageio-ffmpeg is not installed.\nRun: pip install -r requirements.txt"
        ) from exc

    return imageio_ffmpeg.get_ffmpeg_exe()


@dataclass(frozen=True)
class FfmpegConversion:
    source: str
    target: str
    source_ext: str
    target_ext: str
    args: tuple[str, ...]

    def convert(self, src: Path, dst: Path) -> None:
        cmd = [
            get_ffmpeg_exe(),
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            str(src),
            *self.args,
            str(dst),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            message = result.stderr.strip() if result.stderr else "ffmpeg conversion failed."
            raise ConversionError(message)
