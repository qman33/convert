"""LZX bit reader for XNB XMemCompress streams."""

from __future__ import annotations

import struct


class LzxBitReader:
    def __init__(self, data: bytes, offset: int = 0) -> None:
        self.data = data
        self.pos = offset
        self._bit_offset = 0

    @property
    def bit_position(self) -> int:
        return self._bit_offset

    @bit_position.setter
    def bit_position(self, offset: int) -> None:
        if offset < 0:
            offset = 16 - offset
        self._bit_offset = offset % 16
        byte_seek = ((offset - (abs(offset) % 16)) // 16) * 2
        self.pos += byte_seek

    def read_byte(self) -> int:
        value = self.data[self.pos]
        self.pos += 1
        return value

    def peek_u16_le(self) -> int:
        return struct.unpack_from("<H", self.data, self.pos)[0]

    def read_lzx_bits(self, bits: int) -> int:
        bits_left = bits
        read = 0
        while bits_left > 0:
            peek = self.peek_u16_le()
            bits_in_frame = min(max(bits_left, 0), 16 - self._bit_offset)
            offset = 16 - self._bit_offset - bits_in_frame
            mask = (1 << bits_in_frame) - 1
            value = (peek & (mask << offset)) >> offset
            bits_left -= bits_in_frame
            self.bit_position = self._bit_offset + bits_in_frame
            read |= value << bits_left
        return read

    def peek_lzx_bits(self, bits: int) -> int:
        saved_pos = self.pos
        saved_bit = self._bit_offset
        value = self.read_lzx_bits(bits)
        self.pos = saved_pos
        self._bit_offset = saved_bit
        return value

    def read_lzx_int16(self) -> int:
        lsb = self.read_byte()
        msb = self.read_byte()
        return (lsb << 8) | msb

    def align(self) -> None:
        if self._bit_offset > 0:
            self.bit_position = self._bit_offset + (16 - self._bit_offset)

    def seek(self, delta: int) -> None:
        self.pos = max(self.pos + delta, 0)
