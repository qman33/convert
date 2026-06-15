"""PNG and ICO icon conversions."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .base import ConversionError

# Standard Windows icon sizes (largest embedded image is 256x256).
_ICON_SIZES: tuple[int, ...] = (16, 24, 32, 48, 64, 128, 256)


def _require_pillow():
    try:
        from PIL import Image
    except ImportError as exc:
        raise ConversionError(
            "Pillow is not installed.\nRun: pip install -r requirements.txt"
        ) from exc
    return Image


def _square_rgba(image):
    """Place image on a transparent square canvas, preserving aspect ratio."""
    width, height = image.size
    if width == height:
        return image
    side = max(width, height)
    Image = _require_pillow()
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    canvas.paste(image, ((side - width) // 2, (side - height) // 2), image)
    return canvas


def _icon_sizes_for(image) -> list[tuple[int, int]]:
    """Return square ICO sizes to embed, never upscaling beyond the source."""
    side = min(max(image.size), _ICON_SIZES[-1])
    sizes = [(size, size) for size in _ICON_SIZES if size <= side]
    if not sizes:
        sizes = [(side, side)]
    elif sizes[-1] != (side, side) and side not in _ICON_SIZES:
        sizes.append((side, side))
    return sizes


def _largest_embedded_size(ico) -> tuple[int, int]:
    available = ico.info.get("sizes")
    if not available:
        return ico.size
    return max(available, key=lambda size: size[0] * size[1])


@dataclass(frozen=True)
class PngToIcoConversion:
    source: str = "png"
    target: str = "ico"
    source_ext: str = ".png"
    target_ext: str = ".ico"

    def convert(self, src: Path, dst: Path) -> None:
        Image = _require_pillow()
        with Image.open(src) as image:
            rgba = _square_rgba(image.convert("RGBA"))
            sizes = _icon_sizes_for(rgba)
            rgba.save(
                dst,
                format="ICO",
                sizes=sizes,
                bitmap_format="png",
            )


@dataclass(frozen=True)
class IcoToPngConversion:
    source: str = "ico"
    target: str = "png"
    source_ext: str = ".ico"
    target_ext: str = ".png"

    def convert(self, src: Path, dst: Path) -> None:
        Image = _require_pillow()
        with Image.open(src) as ico:
            best_size = _largest_embedded_size(ico)
            if ico.size != best_size:
                ico.size = best_size
            ico.load()
            ico.convert("RGBA").save(
                dst,
                format="PNG",
                compress_level=1,
            )


CONVERSIONS: tuple[PngToIcoConversion, IcoToPngConversion] = (
    PngToIcoConversion(),
    IcoToPngConversion(),
)
