"""Video format conversions."""

from .ffmpeg import FfmpegConversion

CONVERSIONS: tuple[FfmpegConversion, ...] = (
    FfmpegConversion(
        source="mp4",
        target="ogv",
        source_ext=".mp4",
        target_ext=".ogv",
        args=("-c:v", "libtheora", "-c:a", "libvorbis"),
    ),
)
