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
    def PLTE(entries: list[tuple[int, int, int]]) -> Chunk:
        # Pack each RGB triple
        raw = b''.join(bytes([r, g, b]) for r, g, b in entries)
        return Chunk(b'PLTE', raw)

    @staticmethod
    def IDAT(raw_pixels: bytes) -> Chunk:
        compressed = zlib.compress(raw_pixels)
        return Chunk(b'IDAT', compressed)

    @staticmethod
    def IEND() -> Chunk:
        return Chunk(b'IEND', b'')

    @staticmethod
    def bKGD(rgb: tuple[int, int, int]) -> Chunk:
        # Background color for truecolor
        data = struct.pack("!HHH", rgb[0], rgb[1], rgb[2])
        return Chunk(b'bKGD', data)

    @staticmethod
    def cHRM(white_x: int, white_y: int,
             red_x: int, red_y: int,
             green_x: int, green_y: int,
             blue_x: int, blue_y: int) -> Chunk:
        data = struct.pack("!IIIIIIII",
                           white_x, white_y,
                           red_x, red_y,
                           green_x, green_y,
                           blue_x, blue_y)
        return Chunk(b'cHRM', data)

    @staticmethod
    def gAMA(gamma: float) -> Chunk:
        # Gamma stored as gamma*100000, unsigned 32-bit
        val = int(gamma * 100000)
        data = struct.pack("!I", val)
        return Chunk(b'gAMA', data)

    @staticmethod
    def hIST(freqs: list[int]) -> Chunk:
        # Histogram: one uint16 per palette entry
        data = b''.join(struct.pack("!H", f) for f in freqs)
        return Chunk(b'hIST', data)

    @staticmethod
    def pHYs(x_ppu: int, y_ppu: int, unit: int = 1) -> Chunk:
        data = struct.pack("!IIB", x_ppu, y_ppu, unit)
        return Chunk(b'pHYs', data)

    @staticmethod
    def sBIT(bits: list[int]) -> Chunk:
        # Significant bits: number of bits for each channel
        data = bytes(bits)
        print(data)
        return Chunk(b'sBIT', data)

    @staticmethod
    def tEXt(keyword: str, text: str) -> Chunk:
        payload = keyword.encode('latin1') + b"\x00" + text.encode('latin1')
        return Chunk(b'tEXt', payload)

    @staticmethod
    def tIME(year: int, month: int, day: int, hour: int, minute: int, second: int) -> Chunk:
        data = struct.pack("!HBBBBB", year, month, day, hour, minute, second)
        return Chunk(b'tIME', data)

    @staticmethod
    def tRNS(transparency) -> Chunk:
        # Transparency: for palette, list of alpha values; for truecolor, tuple of uint16
        if isinstance(transparency, list):
            data = bytes(transparency)
        elif isinstance(transparency, tuple) and len(transparency) == 3:
            data = struct.pack("!HHH", *transparency)
        else:
            raise ValueError("Unsupported tRNS format")
        return Chunk(b'tRNS', data)


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
        (2835, 2835, 2, 'edge_invalid_unit_specifier.png'),
        (2835, 2835, 12, 'edge_invalid_unit_specifier2.png'),
        (-1, 444, -1, 'edge_invalid_unit_specifier3.png'),
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

    #4) Edge case seeds
    edge_case_seeds = {
        'ec_plte_6.png': [DefaultChunks.IHDR(4,4, color_type=6),
                          Chunk(b'PLTE', b''),
                          Chunk(b'PLTE', bytes([100, 0, 0, 0, 255, 0, 0, 0, 255])),
                          DefaultChunks.IDAT(raw_black),
                          DefaultChunks.IEND()
                          ],
        'ec_plte_6_trns_idat_badcrc.png': [
            DefaultChunks.IHDR(4, 4, color_type=6),
            Chunk(b'PLTE', bytes([255, 0, 0, 0, 255, 0, 0, 0, 255])),
            Chunk(b'tRNS', bytes([128, 64, 0]), crc_override=0),
            Chunk(b'IDAT', zlib.compress(b'\x00' * (4 * 4 * 4)), crc_override=0),
            DefaultChunks.IEND()
        ],
        'significance_bits_ok.png': [

            DefaultChunks.IHDR(4, 4, bit_depth=8, color_type=3),
            DefaultChunks.PLTE([
                (255, 0, 0),
                (0, 255, 0),
                (0, 0, 255)
            ]),
            DefaultChunks.IDAT(
                b''.join([b'\x00' + bytes([0, 1, 2, 0]) for _ in range(4)])  # filter byte + 4px row
            ),
            DefaultChunks.IEND(),
            DefaultChunks.sBIT([8, 8, 8]),
        ],
        'significance_bits_bad.png': [

            DefaultChunks.IHDR(4, 4, bit_depth=8, color_type=3),
            DefaultChunks.PLTE([
                (255, 0, 0),
                (0, 255, 0),
                (0, 0, 255)
            ]),
            DefaultChunks.sBIT([255, 0, 0, 255, 0, 255, 0, 255, 0, 255, 0, 255]),
            DefaultChunks.IDAT(
                b''.join([b'\x00' + bytes([0, 1, 2, 0]) for _ in range(4)])  # filter byte + 4px row
            ),
            DefaultChunks.IEND(),
        ],
        'significance_bits_bad_2.png': [

            DefaultChunks.IHDR(4, 4, bit_depth=8, color_type=3),
            DefaultChunks.PLTE([
                (255, 0, 0),
                (0, 255, 0),
                (0, 0, 255)
            ]),
            DefaultChunks.sBIT([]),
            DefaultChunks.IDAT(
                b''.join([b'\x00' + bytes([0, 1, 2, 0]) for _ in range(4)])  # filter byte + 4px row
            ),
            DefaultChunks.IEND(),
        ],
        'ok_text.png': [

            DefaultChunks.IHDR(4, 4, bit_depth=8, color_type=3),
            DefaultChunks.PLTE([
                (255, 0, 0),
                (0, 255, 0),
                (0, 0, 255)
            ]),
            DefaultChunks.IDAT(
                b''.join([b'\x00' + bytes([0, 1, 2, 0]) for _ in range(4)])  # filter byte + 4px row
            ),
            DefaultChunks.IEND(),
            Chunk(b'tEXt', b"Title" + b"\x00" + b"The Everything PNG"),

        ],
        'improper_text.png': [
            DefaultChunks.IHDR(4, 4, bit_depth=8, color_type=3),
            DefaultChunks.PLTE([
                (255, 0, 0),  # Red
                (0, 255, 0),  # Green
                (0, 0, 255)  # Blue
            ]),
            DefaultChunks.IDAT(
                b''.join([b'\x00' + bytes([0, 1, 2, 0]) for _ in range(4)])  # filter byte + 4px row
            ),
            DefaultChunks.IEND(),
            Chunk(b'tEXt', b"Title" + b"\x00" + "The Funky PNG❤️".encode('utf-8')),

        ],
        'everything_correct.png': [

            DefaultChunks.IHDR(4, 4, bit_depth=8, color_type=3),
            DefaultChunks.PLTE([
                (255, 0, 0),
                (0, 255, 0),
                (0, 0, 255),
            ]),
            DefaultChunks.tRNS([255, 128, 0]),
            DefaultChunks.IDAT(
                b''.join([b'\x00' + bytes([0, 1, 2, 0]) for _ in range(4)])
            ),
            DefaultChunks.IEND(),

            # Ancillary chunks
            DefaultChunks.bKGD((0, 0, 0)),
            DefaultChunks.cHRM(
                white_x=31270, white_y=32900,
                red_x=64000, red_y=33000,
                green_x=30000, green_y=60000,
                blue_x=15000, blue_y=6000
            ),
            DefaultChunks.gAMA(0.45455),
            DefaultChunks.hIST([10, 20, 30]),
            DefaultChunks.pHYs(2835, 2835),
            DefaultChunks.sBIT([8, 8, 8]),
            DefaultChunks.tEXt("Title", "The Everything PNG"),
            DefaultChunks.tIME(2025, 5, 12, 14, 0, 0)
        ],
        'everything_incorrect.png': [
            # Critical chunks
            DefaultChunks.IHDR(4, 4, bit_depth=8, color_type=6),
            DefaultChunks.PLTE([
                (10, 0, 0),
                (1, 20, 5),
                (0, 100, 30),
            ]),
            DefaultChunks.tRNS([255, 12, 0]),
            DefaultChunks.IDAT(
                b''.join([b'\x00' + bytes([0, 1, 2, 0]) for _ in range(4)])
            ),
            DefaultChunks.IEND(),

            # Ancillary chunks
            DefaultChunks.bKGD((0, 255, 0)),
            DefaultChunks.cHRM(
                white_x=310, white_y=32900,
                red_x=640, red_y=330000,
                green_x=30000, green_y=600,
                blue_x=15, blue_y=600
            ),
            DefaultChunks.gAMA(12),
            DefaultChunks.hIST([10, 21, 30]),
            DefaultChunks.pHYs(2835, 235),
            DefaultChunks.sBIT([8, 4, 5]),
            Chunk(b'tEXt', b"Title"+ b"\x00" + "The Everything PNG🫶🫶🫶🫶".encode('utf-8')),
            DefaultChunks.tIME(20, 5, 12, 14, 100, 75)
        ]
    }

    # Combine all seed groups
    all_seeds = {**error_seeds, **phys_seeds, **bug_seeds, **edge_case_seeds}

    # Generate files
    for name, chunks in all_seeds.items():
        builder = PNGBuilder()
        for chunk in chunks:
            builder.add_chunk(chunk)
        builder.save(os.path.join(output_base, name))

    print(f"Saved {len(all_seeds)} PNG seeds to {output_base}")
