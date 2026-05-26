"""Video format conversions."""

from .ffmpeg import (
    AAC_BITRATE,
    FfmpegConversion,
    H264_CRF,
    H264_PRESET,
    VORBIS_QUALITY,
)

CONVERSIONS: tuple[FfmpegConversion, ...] = (
    FfmpegConversion(
        source="mp4",
        target="ogv",
        source_ext=".mp4",
        target_ext=".ogv",
        args=(
            "-c:v",
            "libtheora",
            "-q:v",
            "10",
            "-speed",
            "0",
            "-c:a",
            "libvorbis",
            "-q:a",
            VORBIS_QUALITY,
        ),
    ),
    FfmpegConversion(
        source="ogv",
        target="mp4",
        source_ext=".ogv",
        target_ext=".mp4",
        args=(
            "-c:v",
            "libx264",
            "-crf",
            H264_CRF,
            "-preset",
            H264_PRESET,
            "-c:a",
            "aac",
            "-b:a",
            AAC_BITRATE,
        ),
    ),
)
