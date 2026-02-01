"""Generate simple THRYX wallet icons"""
import struct
import zlib

def create_png(size, color=(99, 102, 241)):
    """Create a simple colored square PNG icon"""
    
    def png_chunk(chunk_type, data):
        chunk_len = struct.pack('>I', len(data))
        chunk_crc = struct.pack('>I', zlib.crc32(chunk_type + data) & 0xffffffff)
        return chunk_len + chunk_type + data + chunk_crc
    
    # PNG signature
    signature = b'\x89PNG\r\n\x1a\n'
    
    # IHDR chunk
    ihdr_data = struct.pack('>IIBBBBB', size, size, 8, 2, 0, 0, 0)
    ihdr = png_chunk(b'IHDR', ihdr_data)
    
    # IDAT chunk (image data)
    raw_data = b''
    
    # Create gradient-like image
    for y in range(size):
        raw_data += b'\x00'  # Filter byte
        for x in range(size):
            # Simple gradient from purple to indigo
            r = int(color[0] + (139 - color[0]) * x / size)
            g = int(color[1] + (92 - color[1]) * y / size)
            b = int(color[2] + (246 - color[2]) * (x + y) / (size * 2))
            
            # Add "T" letter in center
            center = size // 2
            t_width = size // 6
            t_height = size // 3
            
            in_t = False
            # Horizontal bar of T
            if abs(y - center + t_height//2) < t_width//2 and abs(x - center) < t_height//2:
                in_t = True
            # Vertical bar of T
            if abs(x - center) < t_width//3 and y > center - t_height//2 and y < center + t_height:
                in_t = True
            
            if in_t:
                r, g, b = 255, 255, 255
            
            raw_data += bytes([r, g, b])
    
    compressed = zlib.compress(raw_data, 9)
    idat = png_chunk(b'IDAT', compressed)
    
    # IEND chunk
    iend = png_chunk(b'IEND', b'')
    
    return signature + ihdr + idat + iend

# Generate icons
for size in [16, 48, 128]:
    png_data = create_png(size)
    with open(f'icons/icon{size}.png', 'wb') as f:
        f.write(png_data)
    print(f'Created icon{size}.png')

print('Done!')
