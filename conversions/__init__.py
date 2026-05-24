"""Conversion registry."""

from typing import Optional

from .audio import CONVERSIONS as AUDIO_CONVERSIONS
from .base import Conversion, ConversionError, ConversionKey
from .video import CONVERSIONS as VIDEO_CONVERSIONS

ALL_CONVERSIONS: tuple[Conversion, ...] = AUDIO_CONVERSIONS + VIDEO_CONVERSIONS

REGISTRY: dict[ConversionKey, Conversion] = {
    ConversionKey.parse(c.source, c.target): c for c in ALL_CONVERSIONS
}


def get_conversion(source: str, target: str) -> Optional[Conversion]:
    return REGISTRY.get(ConversionKey.parse(source, target))
