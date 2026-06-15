"""XNB payload decompression helpers."""

from __future__ import annotations

import struct

from .base import ConversionError
from .xnb_lzx import decompress_lzx

XNB_HEADER_SIZE = 10
XNB_COMPRESSED_PROLOGUE_SIZE = 14

FLAG_LZX = 0x80
FLAG_LZ4 = 0x40


def _require_lz4():
    try:
        import lz4.block
    except ImportError as exc:
        raise ConversionError(
            "lz4 is not installed.\nRun: pip install -r requirements.txt"
        ) from exc
    return lz4.block


def decompress_lz4(compressed: bytes, decompressed_size: int) -> bytes:
    lz4_block = _require_lz4()
    try:
        result = lz4_block.decompress(compressed, uncompressed_size=decompressed_size)
    except Exception as exc:
        raise ConversionError(f"LZ4 decompression failed: {exc}") from exc
    if len(result) != decompressed_size:
        raise ConversionError(
            f"LZ4 decompressed size mismatch: {len(result)} (expected {decompressed_size})"
        )
    return result


def decompress_xnb_body(data: bytes) -> bytes:
    if len(data) < XNB_HEADER_SIZE:
        raise ConversionError("file is too small to be a valid XNB file")

    flags = data[5]
    file_size = struct.unpack_from("<I", data, 6)[0]

    if not (flags & FLAG_LZX or flags & FLAG_LZ4):
        return data[XNB_HEADER_SIZE:]

    if len(data) < XNB_COMPRESSED_PROLOGUE_SIZE:
        raise ConversionError("compressed XNB file is truncated")

    if flags & FLAG_LZX and flags & FLAG_LZ4:
        raise ConversionError("XNB file has multiple compression flags set")

    decompressed_size = struct.unpack_from("<I", data, 10)[0]
    compressed_end = min(file_size, len(data))
    compressed = data[XNB_COMPRESSED_PROLOGUE_SIZE:compressed_end]

    if flags & FLAG_LZX:
        body = decompress_lzx(compressed, decompressed_size)
    else:
        body = decompress_lz4(compressed, decompressed_size)

    return body
