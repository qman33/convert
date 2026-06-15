#!/usr/bin/env python3
"""Convert media files to another format in the same directory."""

import sys
from pathlib import Path

from conversions import ALL_CONVERSIONS, ConversionError, get_conversion


def print_usage() -> None:
    print("Usage:")
    print("  convert <from> <to> <path\\to\\file>")
    print("  convert <to> <path\\to\\file>        (from is guessed from the file extension)")
    print()
    print("Supported conversions:")
    for conversion in ALL_CONVERSIONS:
        example = f"file{conversion.source_ext}"
        print(
            f"  convert {conversion.source} {conversion.target} "
            f"C:\\path\\to\\{example}"
        )


def parse_args(argv: list[str]) -> tuple[str, str, str] | None:
    """Return (source, target, path) from argv, or None if the arg count is wrong."""
    if len(argv) == 4:
        return argv[1], argv[2], argv[3]
    if len(argv) == 3:
        path = argv[2]
        suffix = Path(path).suffix.lower()
        if not suffix:
            raise ConversionError("can't tell format from filename")
        source = suffix.lstrip(".")
        return source, argv[1], path
    return None


def resolve_source(path_arg: str, expected_ext: str) -> Path:
    src = Path(path_arg).resolve()
    if not src.is_file():
        raise ConversionError(f"file not found: {src}")
    if src.suffix.lower() != expected_ext:
        raise ConversionError(f"expected a {expected_ext} file, got: {src.name}")
    return src


def main() -> int:
    try:
        parsed = parse_args(sys.argv)
    except ConversionError as exc:
        print(f"Error: {exc}")
        return 1

    if parsed is None:
        print_usage()
        return 1

    source, target, path_arg = parsed
    conversion = get_conversion(source, target)
    if conversion is None:
        print(f"Error: no conversion from {source} to {target}")
        print()
        print_usage()
        return 1

    try:
        src = resolve_source(path_arg, conversion.source_ext)
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
