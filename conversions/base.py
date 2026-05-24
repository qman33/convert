"""Shared conversion types."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class ConversionError(Exception):
    """Raised when a conversion fails."""


class Conversion(Protocol):
    source: str
    target: str
    source_ext: str
    target_ext: str

    def convert(self, src: Path, dst: Path) -> None: ...


@dataclass(frozen=True)
class ConversionKey:
    source: str
    target: str

    @classmethod
    def parse(cls, source: str, target: str) -> "ConversionKey":
        return cls(source.lower(), target.lower())
