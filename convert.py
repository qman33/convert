#!/usr/bin/env python3
"""Convert media files to another format in the same directory."""

import sys
from pathlib import Path

from conversions import ALL_CONVERSIONS, ConversionError, get_conversion


def print_usage() -> None:
    print("Usage: convert <from> <to> <path\\to\\file>")
    print()
    print("Supported conversions:")
    for conversion in ALL_CONVERSIONS:
        example = f"file{conversion.source_ext}"
        print(
            f"  convert {conversion.source} {conversion.target} "
            f"C:\\path\\to\\{example}"
        )


def resolve_source(path_arg: str, expected_ext: str) -> Path:
    src = Path(path_arg).resolve()
    if not src.is_file():
        raise ConversionError(f"file not found: {src}")
    if src.suffix.lower() != expected_ext:
        raise ConversionError(f"expected a {expected_ext} file, got: {src.name}")
    return src


def main() -> int:
    if len(sys.argv) != 4:
        print_usage()
        return 1

    conversion = get_conversion(sys.argv[1], sys.argv[2])
    if conversion is None:
        print(f"Error: unsupported conversion: {sys.argv[1]} -> {sys.argv[2]}")
        print()
        print_usage()
        return 1

    try:
        src = resolve_source(sys.argv[3], conversion.source_ext)
        dst = src.with_suffix(conversion.target_ext)
        if dst.exists():
            dst.unlink()
        conversion.convert(src, dst)
    except ConversionError as exc:
        print(f"Error: {exc}")
        return 1

    print(f"Created: {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
