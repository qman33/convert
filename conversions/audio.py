"""Audio format conversions."""

from .ffmpeg import FfmpegConversion

CONVERSIONS: tuple[FfmpegConversion, ...] = (
    FfmpegConversion(
        source="mp3",
        target="ogg",
        source_ext=".mp3",
        target_ext=".ogg",
        args=("-c:a", "libvorbis", "-q:a", "4"),
    ),
)
