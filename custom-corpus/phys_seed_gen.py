import os
import struct
import zlib

# Directory to save seeds
output_dir = './mnt/data/png_seeds'
os.makedirs(output_dir, exist_ok=True)

def create_png_with_phys(width, height, px_per_unit_x, px_per_unit_y, unit_specifier, filename):
    # PNG file signature
    png_signature = b'\x89PNG\r\n\x1a\n'
    
    # IHDR chunk
    ihdr_data = struct.pack("!IIBBBBB", width, height, 8, 2, 0, 0, 0)  # Truecolor RGB, 8-bit depth
    ihdr = b''.join([
        struct.pack("!I", len(ihdr_data)),
        b'IHDR',
        ihdr_data,
        struct.pack("!I", zlib.crc32(b'IHDR' + ihdr_data) & 0xffffffff)
    ])

    # pHYs chunk
    phys_data = struct.pack("!IIB", px_per_unit_x, px_per_unit_y, unit_specifier)
    phys = b''.join([
        struct.pack("!I", len(phys_data)),
        b'pHYs',
        phys_data,
        struct.pack("!I", zlib.crc32(b'pHYs' + phys_data) & 0xffffffff)
    ])

    # IDAT chunk: 1x1 red pixel
    raw_image = b'\x00' + struct.pack("BBB", 255, 0, 0)  # no filter, red pixel
    compressed = zlib.compress(raw_image)
    idat = b''.join([
        struct.pack("!I", len(compressed)),
        b'IDAT',
        compressed,
        struct.pack("!I", zlib.crc32(b'IDAT' + compressed) & 0xffffffff)
    ])

    # IEND chunk
    iend = b'\x00\x00\x00\x00IEND' + struct.pack("!I", zlib.crc32(b'IEND') & 0xffffffff)

    # Write PNG
    with open(os.path.join(output_dir, filename), 'wb') as f:
        f.write(png_signature + ihdr + phys + idat + iend)

# Generate seeds with various pHYs settings
seeds = [
    (1, 1, 3780, 3780, 1, 'seed_72dpi.png'),     # 72 DPI (pixels per meter ~2835)
    (1, 1, 2835, 2835, 1, 'seed_72dpi_m.png'),   # explicit pHYs for 72 DPI
    (1, 1, 11811, 11811, 1, 'seed_300dpi.png'),  # 300 DPI
    (1, 1, 3000, 6000, 1, 'seed_custom.png'),# custom x/y

    (1, 1, 0, 0, 0, 'edge_zero_units.png'),                # zero DPI, unspecified unit
    (1, 1, 1, 1, 0, 'edge_min_unit_unspecified.png'),       # minimum non-zero DPI, unspecified unit
    (1, 1, 0xFFFFFFFF, 0xFFFFFFFF, 1, 'edge_max_uint32.png'),  # max uint32 DPI
    (1, 1, 4294960000, 1, 1, 'edge_overflow_x.png'),       # near-overflow X, normal Y
    (1, 1, 1, 4294960000, 1, 'edge_overflow_y.png'),       # near-overflow Y, normal X
    (1, 1, 2835, 2835, 2, 'edge_invalid_unit_specifier.png') # valid DPI but invalid unit specifier


]

for w, h, xppu, yppu, unit, fname in seeds:
    create_png_with_phys(w, h, xppu, yppu, unit, fname)

# List generated files
generated_files = os.listdir(output_dir)
generated_files

