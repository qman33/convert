"""XNB Texture2D binary format helpers."""

from __future__ import annotations

import struct
from dataclasses import dataclass

from .base import ConversionError
from .xnb_compress import decompress_xnb_body

XNB_MAGIC = b"XNB"
XNB_PLATFORM = b"w"
XNB_VERSION = 5
XNB_FLAGS = 0

TEXTURE2D_READER = "Microsoft.Xna.Framework.Content.Texture2DReader"
SURFACE_FORMAT_COLOR = 0
SURFACE_FORMAT_DXT1 = 4
SURFACE_FORMAT_DXT3 = 5
SURFACE_FORMAT_DXT5 = 6

KNOWN_NON_TEXTURE_READERS: dict[str, str] = {
    "xTile.Pipeline.TideReader": "a Tiled map (.tide), not an image",
    "Microsoft.Xna.Framework.Content.SpriteFontReader": "a sprite font, not an image",
    "Microsoft.Xna.Framework.Content.SoundEffectReader": "a sound effect, not an image",
    "Microsoft.Xna.Framework.Content.SongReader": "a song, not an image",
    "Microsoft.Xna.Framework.Content.EffectReader": "a shader effect, not an image",
}

SUPPORTED_VERSIONS = {4, 5}
SUPPORTED_PLATFORMS = {b"w", b"d", b"m", b"x"}


@dataclass(frozen=True)
class TextureData:
    width: int
    height: int
    pixels_bgra: bytes


def read_uleb128(data: bytes, pos: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while pos < len(data):
        byte = data[pos]
        pos += 1
        result |= (byte & 0x7F) << shift
        if (byte & 0x80) == 0:
            break
        shift += 7
    return result, pos


def write_uleb128(value: int) -> bytes:
    if value == 0:
        return b"\0"

    result = bytearray()
    while value:
        byte = value & 0x7F
        value >>= 7
        if value:
            byte |= 0x80
        result.append(byte)
    return bytes(result)


def read_string(data: bytes, pos: int) -> tuple[str, int]:
    length, pos = read_uleb128(data, pos)
    if length == 0:
        return "", pos
    end = pos + length
    if end > len(data):
        raise ConversionError("unexpected end of XNB file while reading string")
    return data[pos:end].decode("utf-8"), end


def write_string(text: str) -> bytes:
    encoded = text.encode("utf-8")
    return write_uleb128(len(encoded)) + encoded


def simplify_reader_type(type_name: str) -> str:
    """Strip assembly/generic suffixes from an XNB type reader name."""
    return type_name.split(",")[0].split("`")[0]


def is_texture2d_reader(type_name: str) -> bool:
    return simplify_reader_type(type_name) == TEXTURE2D_READER


def unsupported_reader_error(type_name: str) -> str:
    simple = simplify_reader_type(type_name)
    description = KNOWN_NON_TEXTURE_READERS.get(simple)
    if description:
        return (
            f"cannot convert to PNG: this XNB contains {description}\n"
            f"Reader: {simple}"
        )
    return (
        f"cannot convert to PNG: unsupported content reader\n"
        f"Reader: {simple}"
    )


def _require_texture2ddecoder():
    try:
        import texture2ddecoder
    except ImportError as exc:
        raise ConversionError(
            "texture2ddecoder is not installed.\nRun: pip install -r requirements.txt"
        ) from exc
    return texture2ddecoder


def _decode_surface_pixels(
    surface_format: int, width: int, height: int, data: bytes
) -> bytes:
    if surface_format == SURFACE_FORMAT_COLOR:
        expected_size = width * height * 4
        if len(data) != expected_size:
            raise ConversionError(
                f"unexpected mip data size: {len(data)} (expected {expected_size})"
            )
        return data

    t2d = _require_texture2ddecoder()
    if surface_format == SURFACE_FORMAT_DXT1:
        return bytes(t2d.decode_bc1(data, width, height))
    if surface_format == SURFACE_FORMAT_DXT3:
        raise ConversionError(
            "DXT3 surface format is not supported yet (SurfaceFormat.Dxt3)"
        )
    if surface_format == SURFACE_FORMAT_DXT5:
        return bytes(t2d.decode_bc3(data, width, height))

    raise ConversionError(f"unsupported surface format: {surface_format}")


def parse_xnb_texture(data: bytes) -> TextureData:
    if len(data) < 10:
        raise ConversionError("file is too small to be a valid XNB file")

    if data[:3] != XNB_MAGIC:
        raise ConversionError("expected XNB magic header")

    platform = data[3:4]
    version = data[4]

    if version not in SUPPORTED_VERSIONS:
        raise ConversionError(f"unsupported XNB version: {version}")

    if platform not in SUPPORTED_PLATFORMS:
        raise ConversionError(f"unsupported XNB platform: {platform!r}")

    body = decompress_xnb_body(data)
    return _parse_texture_body(body)


def _parse_texture_body(data: bytes) -> TextureData:
    pos = 0

    reader_count, pos = read_uleb128(data, pos)
    if reader_count != 1:
        raise ConversionError("only single-reader Texture2D XNB files are supported")

    reader_name, pos = read_string(data, pos)
    if not is_texture2d_reader(reader_name):
        raise ConversionError(unsupported_reader_error(reader_name))

    pos += 4  # reader type version (ignored)

    shared_fixups, pos = read_uleb128(data, pos)
    if shared_fixups != 0:
        raise ConversionError("shared resource fixups are not supported")

    reader_index, pos = read_uleb128(data, pos)
    if reader_index != 1:
        raise ConversionError(f"unexpected reader index: {reader_index}")

    if pos + 16 > len(data):
        raise ConversionError("unexpected end of XNB file while reading texture header")

    surface_format, width, height, mip_count = struct.unpack_from("<4i", data, pos)
    pos += 16

    if width <= 0 or height <= 0:
        raise ConversionError(f"invalid texture size: {width}x{height}")

    if mip_count != 1:
        raise ConversionError("only single-mip Texture2D files are supported")

    if pos + 4 > len(data):
        raise ConversionError("unexpected end of XNB file while reading mip size")

    data_size, = struct.unpack_from("<i", data, pos)
    pos += 4

    if data_size <= 0:
        raise ConversionError(f"unexpected mip data size: {data_size}")

    end = pos + data_size
    if end > len(data):
        raise ConversionError("unexpected end of XNB file while reading pixel data")

    pixels_bgra = _decode_surface_pixels(
        surface_format, width, height, data[pos:end]
    )
    return TextureData(width=width, height=height, pixels_bgra=pixels_bgra)


def build_xnb_texture(texture: TextureData) -> bytes:
    expected_size = texture.width * texture.height * 4
    if len(texture.pixels_bgra) != expected_size:
        raise ConversionError(
            f"pixel data size mismatch: {len(texture.pixels_bgra)} "
            f"(expected {expected_size})"
        )

    content = bytearray()
    content.extend(write_uleb128(1))
    content.extend(
        struct.pack(
            "<4i",
            SURFACE_FORMAT_COLOR,
            texture.width,
            texture.height,
            1,
        )
    )
    content.extend(struct.pack("<i", expected_size))
    content.extend(texture.pixels_bgra)

    type_manifest = bytearray()
    type_manifest.extend(write_uleb128(1))
    type_manifest.extend(write_string(TEXTURE2D_READER))
    type_manifest.extend(struct.pack("<i", 0))
    type_manifest.extend(write_uleb128(0))

    body = type_manifest + content
    file_size = 10 + len(body)

    output = bytearray()
    output.extend(XNB_MAGIC)
    output.extend(XNB_PLATFORM)
    output.append(XNB_VERSION)
    output.append(XNB_FLAGS)
    output.extend(struct.pack("<i", file_size))
    output.extend(body)
    return bytes(output)
