#!/usr/bin/env python3
"""Convert a single .mp3 file to .ogg in the same directory."""

import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: convert-mp3-to-ogg <path\\to\\file.mp3>")
        return 1

    src = Path(sys.argv[1]).resolve()
    if not src.is_file():
        print(f"Error: file not found: {src}")
        return 1
    if src.suffix.lower() != ".mp3":
        print(f"Error: expected a .mp3 file, got: {src.name}")
        return 1

    dst = src.with_suffix(".ogg")
    if dst.exists():
        dst.unlink()

    try:
        import imageio_ffmpeg

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        print("Error: imageio-ffmpeg is not installed.")
        print("Run: pip install -r requirements.txt")
        return 1

    cmd = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(src),
        "-c:a",
        "libvorbis",
        "-q:a",
        "4",
        str(dst),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Error: ffmpeg conversion failed.")
        if result.stderr:
            print(result.stderr.strip())
        return result.returncode

    print(f"Created: {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
