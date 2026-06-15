"""LZX decompression for XNB files (XMemCompress).

Ported from xnbcli's Lzx.js, itself derived from MonoGame/libmspack.
"""

from __future__ import annotations

from .base import ConversionError
from .xnb_lzx_bitreader import LzxBitReader

MIN_MATCH = 2
NUM_CHARS = 256

BLOCKTYPE_VERBATIM = 1
BLOCKTYPE_ALIGNED = 2
BLOCKTYPE_UNCOMPRESSED = 3

PRETREE_MAXSYMBOLS = 20
PRETREE_TABLEBITS = 6
MAINTREE_MAXSYMBOLS = NUM_CHARS + 50 * 8
MAINTREE_TABLEBITS = 12
LENGTH_MAXSYMBOLS = 249 + 1
LENGTH_TABLEBITS = 12
ALIGNED_MAXSYMBOLS = 8
ALIGNED_TABLEBITS = 7
NUM_PRIMARY_LENGTHS = 7
NUM_SECONDARY_LENGTHS = 249

EXTRA_BITS: list[int] = []
POSITION_BASE: list[int] = []


def _init_static_tables() -> None:
    global EXTRA_BITS, POSITION_BASE
    if EXTRA_BITS:
        return

    extra_bits: list[int] = []
    j = 0
    for i in range(0, 51, 2):
        extra_bits.extend([j, j])
        if i != 0 and j < 17:
            j += 1
    EXTRA_BITS = extra_bits

    j = 0
    position_base: list[int] = []
    for i in range(51):
        position_base.append(j)
        j += 1 << extra_bits[i]
    POSITION_BASE = position_base


class LzxDecoder:
    def __init__(self, window_bits: int) -> None:
        _init_static_tables()
        self.window_size = 1 << window_bits
        if window_bits < 15 or window_bits > 21:
            raise ConversionError("LZX window size out of range")

        posn_slots = 50 if window_bits == 21 else (42 if window_bits == 20 else window_bits << 1)
        self.r0 = 1
        self.r1 = 1
        self.r2 = 1
        self.main_elements = NUM_CHARS + (posn_slots << 3)
        self.header_read = False
        self.block_remaining = 0
        self.block_type = 0
        self.window_posn = 0

        self.pretree_table: list[int] = []
        self.pretree_len = [0] * PRETREE_MAXSYMBOLS
        self.aligned_table: list[int] = []
        self.aligned_len = [0] * ALIGNED_MAXSYMBOLS
        self.length_table: list[int] = []
        self.length_len = [0] * LENGTH_MAXSYMBOLS
        self.maintree_table: list[int] = []
        self.maintree_len = [0] * MAINTREE_MAXSYMBOLS
        self.win = bytearray(self.window_size)

    def decompress(self, buffer: LzxBitReader, frame_size: int, block_size: int) -> bytes:
        if not self.header_read:
            intel = buffer.read_lzx_bits(1)
            if intel != 0:
                raise ConversionError("LZX intel E8 transform is not supported")
            self.header_read = True

        togo = frame_size
        block_start = buffer.pos

        while togo > 0:
            if self.block_remaining == 0:
                self.block_type = buffer.read_lzx_bits(3)
                hi = buffer.read_lzx_bits(16)
                lo = buffer.read_lzx_bits(8)
                self.block_remaining = (hi << 8) | lo

                if self.block_type == BLOCKTYPE_ALIGNED:
                    for i in range(8):
                        self.aligned_len[i] = buffer.read_lzx_bits(3)
                    self.aligned_table = self._decode_table(
                        ALIGNED_MAXSYMBOLS, ALIGNED_TABLEBITS, self.aligned_len
                    )

                if self.block_type in (BLOCKTYPE_ALIGNED, BLOCKTYPE_VERBATIM):
                    self._read_lengths(buffer, self.maintree_len, 0, 256)
                    self._read_lengths(buffer, self.maintree_len, 256, self.main_elements)
                    self.maintree_table = self._decode_table(
                        MAINTREE_MAXSYMBOLS, MAINTREE_TABLEBITS, self.maintree_len
                    )
                    self._read_lengths(buffer, self.length_len, 0, NUM_SECONDARY_LENGTHS)
                    self.length_table = self._decode_table(
                        LENGTH_MAXSYMBOLS, LENGTH_TABLEBITS, self.length_len
                    )
                elif self.block_type == BLOCKTYPE_UNCOMPRESSED:
                    buffer.align()
                    self.r0 = self._read_i32(buffer)
                    self.r1 = self._read_i32(buffer)
                    self.r2 = self._read_i32(buffer)
                else:
                    raise ConversionError(f"invalid LZX block type: {self.block_type}")

            while self.block_remaining > 0 and togo > 0:
                this_run = min(self.block_remaining, togo)
                togo -= this_run
                self.block_remaining -= this_run

                self.window_posn &= self.window_size - 1
                if self.window_posn + this_run > self.window_size:
                    raise ConversionError("LZX run exceeds window frame")

                if self.block_type == BLOCKTYPE_ALIGNED:
                    self._decompress_aligned(buffer, this_run)
                elif self.block_type == BLOCKTYPE_VERBATIM:
                    self._decompress_verbatim(buffer, this_run)
                elif self.block_type == BLOCKTYPE_UNCOMPRESSED:
                    if (buffer.pos + this_run) > block_start + block_size:
                        raise ConversionError("LZX uncompressed block overrun")
                    for i in range(this_run):
                        self.win[self.window_posn + i] = buffer.data[buffer.pos + i]
                    buffer.pos += this_run
                    self.window_posn += this_run
                else:
                    raise ConversionError("invalid LZX block type during run")

        if togo != 0:
            raise ConversionError("LZX EOF reached with data left to go")

        buffer.align()
        start_window_pos = (
            (self.window_size if self.window_posn == 0 else self.window_posn) - frame_size
        )
        return bytes(self.win[start_window_pos : start_window_pos + frame_size])

    @staticmethod
    def _read_i32(buffer: LzxBitReader) -> int:
        value = int.from_bytes(buffer.data[buffer.pos : buffer.pos + 4], "little", signed=True)
        buffer.pos += 4
        return value

    def _read_lengths(
        self, buffer: LzxBitReader, table: list[int], first: int, last: int
    ) -> None:
        for i in range(20):
            self.pretree_len[i] = buffer.read_lzx_bits(4)
        self.pretree_table = self._decode_table(
            PRETREE_MAXSYMBOLS, PRETREE_TABLEBITS, self.pretree_len
        )

        i = first
        while i < last:
            symbol = self._read_huff_symbol(
                buffer,
                self.pretree_table,
                self.pretree_len,
                PRETREE_MAXSYMBOLS,
                PRETREE_TABLEBITS,
            )
            if symbol == 17:
                zeros = buffer.read_lzx_bits(4) + 4
                for _ in range(zeros):
                    table[i] = 0
                    i += 1
            elif symbol == 18:
                zeros = buffer.read_lzx_bits(5) + 20
                for _ in range(zeros):
                    table[i] = 0
                    i += 1
            elif symbol == 19:
                same = buffer.read_lzx_bits(1) + 4
                symbol = self._read_huff_symbol(
                    buffer,
                    self.pretree_table,
                    self.pretree_len,
                    PRETREE_MAXSYMBOLS,
                    PRETREE_TABLEBITS,
                )
                symbol = table[i] - symbol
                if symbol < 0:
                    symbol += 17
                for _ in range(same):
                    table[i] = symbol
                    i += 1
            else:
                symbol = table[i] - symbol
                if symbol < 0:
                    symbol += 17
                table[i] = symbol
                i += 1

    def _decode_table(self, symbols: int, bits: int, length: list[int]) -> list[int]:
        table: list[int] = []
        pos = 0
        table_mask = 1 << bits
        bit_mask = table_mask >> 1

        for _bit_num in range(1, bits + 1):
            for symbol in range(symbols):
                if length[symbol] == _bit_num:
                    leaf = pos
                    pos += bit_mask
                    if pos > table_mask:
                        raise ConversionError("LZX decode table overrun")
                    for fill in range(bit_mask):
                        if len(table) <= leaf + fill:
                            table.extend([0] * (leaf + fill + 1 - len(table)))
                        table[leaf + fill] = symbol
            bit_mask >>= 1

        if pos == table_mask:
            return table

        if len(table) < table_mask:
            table.extend([0] * (table_mask - len(table)))
        for symbol in range(pos, table_mask):
            table[symbol] = 0xFFFF

        next_symbol = symbols if (table_mask >> 1) < symbols else (table_mask >> 1)
        pos <<= 16
        table_mask <<= 16
        bit_mask = 1 << 15

        for bit_num in range(bits + 1, 17):
            for symbol in range(symbols):
                if length[symbol] != bit_num:
                    continue
                leaf = pos >> 16
                for fill in range(bit_num - bits):
                    if table[leaf] == 0xFFFF:
                        needed = (next_symbol << 1) + 2
                        if len(table) < needed:
                            table.extend([0] * (needed - len(table)))
                        table[next_symbol << 1] = 0xFFFF
                        table[(next_symbol << 1) + 1] = 0xFFFF
                        table[leaf] = next_symbol
                        next_symbol += 1
                    leaf = table[leaf] << 1
                    if (pos >> (15 - fill)) & 1:
                        leaf += 1
                if len(table) <= leaf:
                    table.extend([0] * (leaf + 1 - len(table)))
                table[leaf] = symbol
                pos += bit_mask
                if pos > table_mask:
                    raise ConversionError("LZX decode table overrun during long codes")
            bit_mask >>= 1

        if pos == table_mask:
            return table
        raise ConversionError("LZX decode table did not reach table mask")

    def _read_huff_symbol(
        self,
        buffer: LzxBitReader,
        table: list[int],
        length: list[int],
        symbols: int,
        bits: int,
    ) -> int:
        bit = buffer.peek_lzx_bits(32) & 0xFFFFFFFF
        i = table[buffer.peek_lzx_bits(bits)]
        if i >= symbols:
            j = 1 << (32 - bits)
            while True:
                j >>= 1
                i <<= 1
                i |= 1 if (bit & j) else 0
                if j == 0:
                    return 0
                i = table[i]
                if i < symbols:
                    break
        buffer.bit_position = buffer.bit_position + length[i]
        return i

    def _decompress_verbatim(self, buffer: LzxBitReader, this_run: int) -> None:
        while this_run > 0:
            main_element = self._read_huff_symbol(
                buffer,
                self.maintree_table,
                self.maintree_len,
                MAINTREE_MAXSYMBOLS,
                MAINTREE_TABLEBITS,
            )
            if main_element < NUM_CHARS:
                self.win[self.window_posn] = main_element
                self.window_posn += 1
                this_run -= 1
                continue

            main_element -= NUM_CHARS
            match_length = main_element & NUM_PRIMARY_LENGTHS
            if match_length == NUM_PRIMARY_LENGTHS:
                match_length += self._read_huff_symbol(
                    buffer,
                    self.length_table,
                    self.length_len,
                    LENGTH_MAXSYMBOLS,
                    LENGTH_TABLEBITS,
                )
            match_length += MIN_MATCH
            match_offset = main_element >> 3

            if match_offset > 2:
                if match_offset != 3:
                    extra = EXTRA_BITS[match_offset]
                    match_offset = POSITION_BASE[match_offset] - 2 + buffer.read_lzx_bits(extra)
                else:
                    match_offset = 1
                self.r2, self.r1, self.r0 = self.r1, self.r0, match_offset
            elif match_offset == 0:
                match_offset = self.r0
            elif match_offset == 1:
                match_offset = self.r1
                self.r1, self.r0 = self.r0, match_offset
            else:
                match_offset = self.r2
                self.r2, self.r0 = self.r0, match_offset

            self._copy_match_bytes(match_offset, match_length)
            this_run -= match_length

    def _decompress_aligned(self, buffer: LzxBitReader, this_run: int) -> None:
        while this_run > 0:
            main_element = self._read_huff_symbol(
                buffer,
                self.maintree_table,
                self.maintree_len,
                MAINTREE_MAXSYMBOLS,
                MAINTREE_TABLEBITS,
            )
            if main_element < NUM_CHARS:
                self.win[self.window_posn] = main_element
                self.window_posn += 1
                this_run -= 1
                continue

            main_element -= NUM_CHARS
            match_length = main_element & NUM_PRIMARY_LENGTHS
            if match_length == NUM_PRIMARY_LENGTHS:
                match_length += self._read_huff_symbol(
                    buffer,
                    self.length_table,
                    self.length_len,
                    LENGTH_MAXSYMBOLS,
                    LENGTH_TABLEBITS,
                )
            match_length += MIN_MATCH
            match_offset = main_element >> 3

            if match_offset > 2:
                extra = EXTRA_BITS[match_offset]
                match_offset = POSITION_BASE[match_offset] - 2
                if extra > 3:
                    extra -= 3
                    match_offset += buffer.read_lzx_bits(extra) << 3
                    match_offset += self._read_huff_symbol(
                        buffer,
                        self.aligned_table,
                        self.aligned_len,
                        ALIGNED_MAXSYMBOLS,
                        ALIGNED_TABLEBITS,
                    )
                elif extra == 3:
                    match_offset += self._read_huff_symbol(
                        buffer,
                        self.aligned_table,
                        self.aligned_len,
                        ALIGNED_MAXSYMBOLS,
                        ALIGNED_TABLEBITS,
                    )
                elif extra > 0:
                    match_offset += buffer.read_lzx_bits(extra)
                else:
                    match_offset = 1
                self.r2, self.r1, self.r0 = self.r1, self.r0, match_offset
            elif match_offset == 0:
                match_offset = self.r0
            elif match_offset == 1:
                match_offset = self.r1
                self.r1, self.r0 = self.r0, match_offset
            else:
                match_offset = self.r2
                self.r2, self.r0 = self.r0, match_offset

            self._copy_match_bytes(match_offset, match_length)
            this_run -= match_length

    def _copy_match_bytes(self, match_offset: int, match_length: int) -> None:
        rundest = self.window_posn
        self.window_posn += match_length

        if rundest >= match_offset:
            runsrc = rundest - match_offset
            for i in range(match_length):
                self.win[rundest + i] = self.win[runsrc + i]
            return

        runsrc = rundest + (self.window_size - match_offset)
        copy_length = match_offset - rundest
        if copy_length < match_length:
            for i in range(copy_length):
                self.win[rundest + i] = self.win[runsrc + i]
            rundest += copy_length
            match_length -= copy_length
            runsrc = 0
        for i in range(match_length):
            self.win[rundest + i] = self.win[runsrc + i]


def decompress_lzx(compressed: bytes, decompressed_size: int) -> bytes:
    reader = LzxBitReader(compressed)
    decoder = LzxDecoder(16)
    output = bytearray()
    pos = 0
    compressed_todo = len(compressed)

    while pos < compressed_todo:
        flag = reader.read_byte()
        if flag == 0xFF:
            frame_size = reader.read_lzx_int16()
            block_size = reader.read_lzx_int16()
            pos += 5
        else:
            reader.seek(-1)
            block_size = reader.read_lzx_int16()
            frame_size = 0x8000
            pos += 2

        if block_size == 0 or frame_size == 0:
            break
        if block_size > 0x10000 or frame_size > 0x10000:
            raise ConversionError("invalid LZX block or frame size")

        block_start = reader.pos
        chunk = decoder.decompress(reader, frame_size, block_size)
        output.extend(chunk)
        pos += block_size
        reader.pos = block_start + block_size
        reader._bit_offset = 0

    result = bytes(output)
    if len(result) != decompressed_size:
        raise ConversionError(
            f"LZX decompressed size mismatch: {len(result)} (expected {decompressed_size})"
        )
    return result
