"""Audio format conversions."""

from .ffmpeg import FfmpegConversion, MP3_QUALITY, VORBIS_QUALITY

CONVERSIONS: tuple[FfmpegConversion, ...] = (
    FfmpegConversion(
        source="mp3",
        target="ogg",
        source_ext=".mp3",
        target_ext=".ogg",
        args=("-c:a", "libvorbis", "-q:a", VORBIS_QUALITY),
    ),
    FfmpegConversion(
        source="ogg",
        target="mp3",
        source_ext=".ogg",
        target_ext=".mp3",
        args=("-c:a", "libmp3lame", "-q:a", MP3_QUALITY),
    ),
    FfmpegConversion(
        source="mp3",
        target="wav",
        source_ext=".mp3",
        target_ext=".wav",
        args=("-c:a", "pcm_s16le"),
    ),
    FfmpegConversion(
        source="wav",
        target="mp3",
        source_ext=".wav",
        target_ext=".mp3",
        args=("-c:a", "libmp3lame", "-q:a", MP3_QUALITY),
    ),
)
