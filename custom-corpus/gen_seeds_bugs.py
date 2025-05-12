import os
import struct
import zlib

# Directory for bug-triggering seeds
output_dir = './mnt/data/png_seeds_bugs'
os.makedirs(output_dir, exist_ok=True)

def write_png(chunks, filename):
    png_signature = b'\x89PNG\r\n\x1a\n'
    path = os.path.join(output_dir, filename)
    with open(path, 'wb') as f:
        f.write(png_signature)
        for ctype, data, length_override, crc_override in chunks:
            length = length_override if length_override is not None else len(data)
            f.write(struct.pack("!I", length))
            f.write(ctype)
            f.write(data[:length])
            crc = crc_override if crc_override is not None else (zlib.crc32(ctype + data) & 0xffffffff)
            f.write(struct.pack("!I", crc))
    return path

# Standard IHDR and IDAT
ihdr_data = struct.pack("!IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
ihdr = (b'IHDR', ihdr_data, None, None)
raw_image = b'\x00' + struct.pack("BBB", 0, 0, 0)
idat_data = zlib.compress(raw_image)
idat = (b'IDAT', idat_data, None, None)
iend = (b'IEND', b'', None, None)

# Bug seeds based on known issues
seeds = [
    # Chunk length integer overflow (CVE-2011-3045)
    ([ihdr, (b'pHYs', b'\x00'*9, 0xFFFFFFFF, None), idat, iend], 'bug_overflow_length.png'),
    # PLTE entries count mismatch
    ([ihdr, (b'PLTE', b'\x00\xff', None, None), idat, iend], 'bug_plte_mismatch.png'),
    # Truncated iCCP chunk causing infinite loop
    ([ihdr, (b'iCCP', b'ICC_PROFILE\x00' + b'\x12'*5, None, None), idat, iend], 'bug_iccp_truncated.png'),
    # tEXt chunk wrong CRC frees improperly
    ([ihdr, (b'tEXt', b'Comment\x00Hello', None, 0x12345678), idat, iend], 'bug_text_bad_crc.png'),
    # tIME chunk invalid date (month=13)
    ([ihdr, (b'tIME', struct.pack("!HBBBBB", 2025, 5, 13, 12, 0, 0), None, None), idat, iend], 'bug_time_invalid.png'),
    # sBIT chunk with invalid bitdepth (grayscale chunk too long)
    ([ihdr, (b'sBIT', b'\x08\x08\x08\x08', None, None), idat, iend], 'bug_sbit_invalid.png'),
]

generated = []
for chunks, name in seeds:
    path = write_png(chunks, name)
    generated.append(name)

generated

