"""XNB texture conversions."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from .base import ConversionError
from .xnb_format import TextureData, build_xnb_texture, parse_xnb_texture


def _require_pillow():
    try:
        from PIL import Image
    except ImportError as exc:
        raise ConversionError(
            "Pillow is not installed.\nRun: pip install -r requirements.txt"
        ) from exc
    return Image


def is_premultiplied_bgra(pixels_bgra: bytes) -> bool:
    for i in range(0, len(pixels_bgra), 4):
        b = pixels_bgra[i]
        g = pixels_bgra[i + 1]
        r = pixels_bgra[i + 2]
        a = pixels_bgra[i + 3]
        if a == 0:
            continue
        if r > a or g > a or b > a:
            return False
    return True


def unpremultiply_bgra(pixels_bgra: bytes) -> bytes:
    """Convert premultiplied BGRA to straight-alpha BGRA (matches xnbcli)."""
    straight = bytearray(len(pixels_bgra))
    for i in range(0, len(pixels_bgra), 4):
        b = pixels_bgra[i]
        g = pixels_bgra[i + 1]
        r = pixels_bgra[i + 2]
        a = pixels_bgra[i + 3]
        if a == 0:
            straight[i : i + 4] = (0, 0, 0, 0)
        else:
            inverse_alpha = 255.0 / a
            straight[i] = min(255, math.ceil(b * inverse_alpha))
            straight[i + 1] = min(255, math.ceil(g * inverse_alpha))
            straight[i + 2] = min(255, math.ceil(r * inverse_alpha))
            straight[i + 3] = a
    return bytes(straight)


def premultiply_bgra(pixels_bgra: bytes) -> bytes:
    """Convert straight-alpha BGRA to premultiplied BGRA (matches xnbcli)."""
    premultiplied = bytearray(len(pixels_bgra))
    for i in range(0, len(pixels_bgra), 4):
        b = pixels_bgra[i]
        g = pixels_bgra[i + 1]
        r = pixels_bgra[i + 2]
        a = pixels_bgra[i + 3]
        if a == 0:
            premultiplied[i : i + 4] = (0, 0, 0, 0)
        else:
            alpha = a / 255.0
            premultiplied[i] = int(b * alpha)
            premultiplied[i + 1] = int(g * alpha)
            premultiplied[i + 2] = int(r * alpha)
            premultiplied[i + 3] = a
    return bytes(premultiplied)


def bgra_to_rgba(pixels_bgra: bytes) -> bytes:
    rgba = bytearray(len(pixels_bgra))
    for i in range(0, len(pixels_bgra), 4):
        b = pixels_bgra[i]
        g = pixels_bgra[i + 1]
        r = pixels_bgra[i + 2]
        a = pixels_bgra[i + 3]
        rgba[i] = r
        rgba[i + 1] = g
        rgba[i + 2] = b
        rgba[i + 3] = a
    return bytes(rgba)


def rgba_to_bgra(pixels_rgba: bytes) -> bytes:
    bgra = bytearray(len(pixels_rgba))
    for i in range(0, len(pixels_rgba), 4):
        r = pixels_rgba[i]
        g = pixels_rgba[i + 1]
        b = pixels_rgba[i + 2]
        a = pixels_rgba[i + 3]
        bgra[i] = b
        bgra[i + 1] = g
        bgra[i + 2] = r
        bgra[i + 3] = a
    return bytes(bgra)


def bgra_bytes_to_rgba_bytes(pixels_bgra: bytes) -> bytes:
    bgra = pixels_bgra
    if is_premultiplied_bgra(pixels_bgra):
        bgra = unpremultiply_bgra(pixels_bgra)
    return bgra_to_rgba(bgra)


def rgba_bytes_to_premultiplied_bgra(pixels_rgba: bytes) -> bytes:
    return premultiply_bgra(rgba_to_bgra(pixels_rgba))


def bgra_premultiplied_to_rgba_straight(
    pixels_bgra: bytes, width: int, height: int
) -> bytes:
    del width, height
    return bgra_bytes_to_rgba_bytes(pixels_bgra)


def rgba_straight_to_bgra_premultiplied(
    pixels_rgba: bytes, width: int, height: int
) -> bytes:
    del width, height
    return rgba_bytes_to_premultiplied_bgra(pixels_rgba)


@dataclass(frozen=True)
class XnbToPngConversion:
    source: str = "xnb"
    target: str = "png"
    source_ext: str = ".xnb"
    target_ext: str = ".png"

    def convert(self, src: Path, dst: Path) -> None:
        Image = _require_pillow()
        data = src.read_bytes()
        texture = parse_xnb_texture(data)
        rgba = bgra_bytes_to_rgba_bytes(texture.pixels_bgra)
        image = Image.frombytes("RGBA", (texture.width, texture.height), rgba)
        image.save(dst, format="PNG")


@dataclass(frozen=True)
class PngToXnbConversion:
    source: str = "png"
    target: str = "xnb"
    source_ext: str = ".png"
    target_ext: str = ".xnb"

    def convert(self, src: Path, dst: Path) -> None:
        Image = _require_pillow()
        with Image.open(src) as image:
            rgba_image = image.convert("RGBA")
            width, height = rgba_image.size
            bgra = rgba_bytes_to_premultiplied_bgra(rgba_image.tobytes())

        texture = TextureData(width=width, height=height, pixels_bgra=bgra)
        dst.write_bytes(build_xnb_texture(texture))


CONVERSIONS: tuple[XnbToPngConversion, PngToXnbConversion] = (
    XnbToPngConversion(),
    PngToXnbConversion(),
)
