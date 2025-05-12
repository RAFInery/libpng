import os
import struct
import zlib

# Directory for error-triggering seeds
output_dir = './mnt/data/png_seeds_errors'
os.makedirs(output_dir, exist_ok=True)


# Helper to write PNG with custom chunks
def write_png(chunks, filename):
    png_signature = b'\x89PNG\r\n\x1a\n'
    with open(os.path.join(output_dir, filename), 'wb') as f:
        f.write(png_signature)
        for chunk_type, data, crc_override, length_override in chunks:
            length = length_override if length_override is not None else len(data)
            f.write(struct.pack("!I", length))
            f.write(chunk_type)
            f.write(data[:length])  # truncate if length < data
            # compute CRC or use override
            if crc_override is not None:
                crc = crc_override
            else:
                crc = zlib.crc32(chunk_type + data) & 0xffffffff
            f.write(struct.pack("!I", crc))


# Standard IHDR and IDAT for a 1x1 black pixel
ihdr_data = struct.pack("!IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
ihdr = (b'IHDR', ihdr_data, None, None)

raw_image = b'\x00' + struct.pack("BBB", 0, 0, 0)
compressed = zlib.compress(raw_image)
idat = (b'IDAT', compressed, None, None)

iend = (b'IEND', b'', None, None)

# Pre-calc correct pHYs data
phys_data = struct.pack("!IIB", 2835, 2835, 1)

# Define error seeds
seeds = {
    'wrong_length.png': [
        ihdr,
        (b'pHYs', phys_data, None, 8),  # length too small
        idat,
        iend
    ],
    'long_length.png': [
        ihdr,
        (b'pHYs', phys_data, None, 100),  # length too large
        idat,
        iend
    ],
    'wrong_crc.png': [
        ihdr,
        (b'pHYs', phys_data, 0xdeadbeef, None),  # bad CRC
        idat,
        iend
    ],
    'truncated_data.png': [
        ihdr,
        (b'pHYs', phys_data, None, 5),  # truncated data
        # intentionally no IDAT/IEND
    ],
    'duplicate_phys.png': [
        ihdr,
        (b'pHYs', phys_data, None, None),
        (b'pHYs', phys_data, None, None),
        idat,
        iend
    ],
    'phys_after_idat.png': [
        ihdr,
        idat,
        (b'pHYs', phys_data, None, None),
        iend
    ]
}

# Generate files
for name, chunks in seeds.items():
    write_png(chunks, name)

# List generated files
os.listdir(output_dir)
