import os
import struct
import zlib


class Chunk:
    def __init__(self, chunk_type: bytes, data: bytes, length_override: int = None, crc_override: int = None):
        self.chunk_type = chunk_type
        self.data = data
        self.length_override = length_override
        self.crc_override = crc_override

    def serialize(self) -> bytes:
        length = self.length_override if self.length_override is not None else len(self.data)
        chunk = struct.pack("!I", length) + self.chunk_type
        chunk += self.data[:length]
        if self.crc_override is not None:
            crc = self.crc_override
        else:
            crc = zlib.crc32(self.chunk_type + self.data) & 0xffffffff
        chunk += struct.pack("!I", crc)
        return chunk


class PNGBuilder:
    PNG_SIGNATURE = b'\x89PNG\r\n\x1a\n'

    def __init__(self):
        self.chunks = []

    def add_chunk(self, chunk: Chunk) -> 'PNGBuilder':
        self.chunks.append(chunk)
        return self

    def save(self, filename: str):
        with open(filename, 'wb') as f:
            f.write(self.PNG_SIGNATURE)
            for chunk in self.chunks:
                f.write(chunk.serialize())


class DefaultChunks:
    @staticmethod
    def IHDR(width: int, height: int, bit_depth: int = 8, color_type: int = 2,
             compression: int = 0, filter_method: int = 0, interlace: int = 0) -> Chunk:
        data = struct.pack("!IIBBBBB", width, height, bit_depth, color_type,
                           compression, filter_method, interlace)
        return Chunk(b'IHDR', data)

    @staticmethod
    def PLTE() -> Chunk:
        pass
    @staticmethod
    def IDAT(raw_pixels: bytes) -> Chunk:
        compressed = zlib.compress(raw_pixels)
        return Chunk(b'IDAT', compressed)

    @staticmethod
    def IEND() -> Chunk:
        return Chunk(b'IEND', b'')

    @staticmethod
    def bKGD() -> Chunk:
        pass
    @staticmethod
    def cHRM() -> Chunk:
        pass
    @staticmethod
    def gAMA() -> Chunk:
        pass
    @staticmethod
    def gAMA() -> Chunk:
        pass
    @staticmethod
    def hIST() -> Chunk:
        pass

    @staticmethod
    def pHYs(x_ppu: int, y_ppu: int, unit: int = 1) -> Chunk:
        data = struct.pack("!IIB", x_ppu, y_ppu, unit)
        return Chunk(b'pHYs', data)

    @staticmethod
    def sBIT() -> Chunk:
        pass

    @staticmethod
    def tEXt(keyword: str, text: str) -> Chunk:
        payload = keyword.encode('latin1') + b"\x00" + text.encode('latin1')
        return Chunk(b'tEXt', payload)

    @staticmethod
    def tIME()-> Chunk:
        pass
    @staticmethod
    def tRNS()-> Chunk:
        pass


# Test harness to generate seeds
if __name__ == '__main__':
    output_base = './mnt/data/png_seeds_oop'
    raw_black = b"\x00" + bytes([0, 0, 0])  # filter byte + black pixel
    os.makedirs(output_base, exist_ok=True)

    # 1) Error seeds
    error_seeds = {
        'wrong_length.png': [
            DefaultChunks.IHDR(1, 1),
            Chunk(b'pHYs', DefaultChunks.pHYs(2835, 2835, 1).data, length_override=8),
            DefaultChunks.IDAT(raw_black),
            DefaultChunks.IEND()
        ],
        'long_length.png': [
            DefaultChunks.IHDR(1, 1),
            Chunk(b'pHYs', DefaultChunks.pHYs(2835, 2835, 1).data, length_override=100),
            DefaultChunks.IDAT(raw_black),
            DefaultChunks.IEND()
        ],
        'wrong_crc.png': [
            DefaultChunks.IHDR(1, 1),
            Chunk(b'pHYs', DefaultChunks.pHYs(2835, 2835, 1).data, crc_override=0xdeadbeef),
            DefaultChunks.IDAT(raw_black),
            DefaultChunks.IEND()
        ],
        'truncated_data.png': [
            DefaultChunks.IHDR(1, 1),
            Chunk(b'pHYs', DefaultChunks.pHYs(2835, 2835, 1).data, length_override=5)
        ],  # no IDAT/IEND
        'duplicate_phys.png': [
            DefaultChunks.IHDR(1, 1),
            DefaultChunks.pHYs(2835, 2835, 1),
            DefaultChunks.pHYs(2835, 2835, 1),
            DefaultChunks.IDAT(raw_black),
            DefaultChunks.IEND()
        ],
        'phys_after_idat.png': [
            DefaultChunks.IHDR(1, 1),
            DefaultChunks.IDAT(raw_black),
            DefaultChunks.pHYs(2835, 2835, 1),
            DefaultChunks.IEND()
        ]
    }

    # 2) Standard + edge-case pHYs seeds
    ppu_values = [
        (3780, 3780, 1, 'seed_72dpi.png'),
        (2835, 2835, 1, 'seed_72dpi_m.png'),
        (11811, 11811, 1, 'seed_300dpi.png'),
        (3000, 6000, 1, 'seed_custom.png'),
        (0, 0, 0, 'edge_zero_units.png'),
        (1, 1, 0, 'edge_min_unit_unspecified.png'),
        (0xFFFFFFFF, 0xFFFFFFFF, 1, 'edge_max_uint32.png'),
        (4294960000, 1, 1, 'edge_overflow_x.png'),
        (1, 4294960000, 1, 'edge_overflow_y.png'),
        (2835, 2835, 2, 'edge_invalid_unit_specifier.png')
    ]
    phys_seeds = {}
    for xppu, yppu, unit, name in ppu_values:
        phys_seeds[name] = [
            DefaultChunks.IHDR(1, 1),
            DefaultChunks.pHYs(xppu, yppu, unit),
            DefaultChunks.IDAT(raw_black),
            DefaultChunks.IEND()
        ]

    # 3) Bug seeds
    bug_seeds = {
        'bug_overflow_length.png': [
            DefaultChunks.IHDR(1, 1),
            Chunk(b'pHYs', b'\x00' * 9, length_override=0xFFFFFFFF),
            DefaultChunks.IDAT(raw_black),
            DefaultChunks.IEND()
        ],
        'bug_plte_mismatch.png': [
            DefaultChunks.IHDR(1, 1),
            Chunk(b'PLTE', b'\x00\xff'),
            DefaultChunks.IDAT(raw_black),
            DefaultChunks.IEND()
        ],
        'bug_iccp_truncated.png': [
            DefaultChunks.IHDR(1, 1),
            Chunk(b'iCCP', b'ICC_PROFILE\x00' + b'\x12' * 5),
            DefaultChunks.IDAT(raw_black),
            DefaultChunks.IEND()
        ],
        'bug_text_bad_crc.png': [
            DefaultChunks.IHDR(1, 1),
            Chunk(b'tEXt', b'Comment\x00Hello', crc_override=0x12345678),
            DefaultChunks.IDAT(raw_black),
            DefaultChunks.IEND()
        ],
        'bug_time_invalid.png': [
            DefaultChunks.IHDR(1, 1),
            Chunk(b'tIME', struct.pack("!HBBBBB", 2025, 5, 13, 12, 0, 0)),
            DefaultChunks.IDAT(raw_black),
            DefaultChunks.IEND()
        ],
        'bug_sbit_invalid.png': [
            DefaultChunks.IHDR(1, 1),
            Chunk(b'sBIT', b'\x08\x08\x08\x08'),
            DefaultChunks.IDAT(raw_black),
            DefaultChunks.IEND()
        ]
    }

    # Combine all seed groups
    all_seeds = {**error_seeds, **phys_seeds, **bug_seeds}

    # Generate files
    for name, chunks in all_seeds.items():
        builder = PNGBuilder()
        for chunk in chunks:
            builder.add_chunk(chunk)
        builder.save(os.path.join(output_base, name))

    print(f"Saved {len(all_seeds)} PNG seeds to {output_base}")
