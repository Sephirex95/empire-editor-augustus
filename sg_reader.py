import os
import struct
import io
from typing import List, Dict, Optional
from PIL import Image
import numpy as np


class SgImageRecord:
    def __init__(self, stream: io.BytesIO, include_alpha: bool = False):
        self.offset = struct.unpack('<I', stream.read(4))[0]
        self.length = struct.unpack('<I', stream.read(4))[0]
        self.uncompressed_length = struct.unpack('<I', stream.read(4))[0]
        stream.read(4)  # Skip 4 zero bytes
        self.invert_offset = struct.unpack('<i', stream.read(4))[0]
        self.width = struct.unpack('<h', stream.read(2))[0]
        self.height = struct.unpack('<h', stream.read(2))[0]
        stream.read(26)  # Skip 26 unknown bytes
        self.type = struct.unpack('<H', stream.read(2))[0]
        self.flags = stream.read(4)
        self.bitmap_id = struct.unpack('<B', stream.read(1))[0]
        stream.read(7)  # Skip 7 bytes

        if include_alpha:
            self.alpha_offset = struct.unpack('<I', stream.read(4))[0]
            self.alpha_length = struct.unpack('<I', stream.read(4))[0]
        else:
            self.alpha_offset = 0
            self.alpha_length = 0


class SgBitmapRecord:
    def __init__(self, stream: io.BytesIO):
        self.filename = stream.read(65).rstrip(b'\x00').decode('ascii', errors='ignore')
        self.comment = stream.read(51).rstrip(b'\x00').decode('ascii', errors='ignore')
        self.width = struct.unpack('<I', stream.read(4))[0]
        self.height = struct.unpack('<I', stream.read(4))[0]
        self.num_images = struct.unpack('<I', stream.read(4))[0]
        self.start_index = struct.unpack('<I', stream.read(4))[0]
        self.end_index = struct.unpack('<I', stream.read(4))[0]
        stream.read(64)  # Skip padding


class SgHeader:
    def __init__(self, stream: io.BytesIO):
        self.sg_filesize = struct.unpack('<I', stream.read(4))[0]
        self.version = struct.unpack('<I', stream.read(4))[0]
        self.unknown1 = struct.unpack('<I', stream.read(4))[0]
        self.max_image_records = struct.unpack('<i', stream.read(4))[0]
        self.num_image_records = struct.unpack('<i', stream.read(4))[0]
        self.num_bitmap_records = struct.unpack('<i', stream.read(4))[0]
        self.num_bitmap_records_without_system = struct.unpack('<i', stream.read(4))[0]
        self.total_filesize = struct.unpack('<I', stream.read(4))[0]
        self.filesize_555 = struct.unpack('<I', stream.read(4))[0]
        self.filesize_external = struct.unpack('<I', stream.read(4))[0]
        stream.seek(680)  # Skip to end of header


class SgFileReader:
    def __init__(self, sg_filename: str):
        self.sg_filename = sg_filename
        self.base_path = os.path.dirname(sg_filename)
        self.base_name = os.path.splitext(os.path.basename(sg_filename))[0]
        self.header: Optional[SgHeader] = None
        self.bitmaps: List[SgBitmapRecord] = []
        self.images: List[SgImageRecord] = []
        self._555_files: Dict[str, bytes] = {}

    def load(self) -> Dict[str, List[Image.Image]]:
        """Load SG file and return dictionary of bitmap name -> list of PIL Images."""
        with open(self.sg_filename, 'rb') as f:
            stream = io.BytesIO(f.read())

        self.header = SgHeader(stream)
        self._load_bitmaps(stream)
        stream.seek(680 + self._max_bitmap_records() * 200)

        include_alpha = self.header.version >= 0xd6
        self._load_images(stream, include_alpha)

        return self._convert_images_to_pil()

    def _max_bitmap_records(self) -> int:
        if self.header.version == 0xcf:
            return 50
        elif self.header.version == 0xd3:
            return 100
        else:
            return 200

    def _load_bitmaps(self, stream: io.BytesIO):
        for _ in range(self.header.num_bitmap_records):
            self.bitmaps.append(SgBitmapRecord(stream))

    def _load_images(self, stream: io.BytesIO, include_alpha: bool):
        _ = SgImageRecord(stream, include_alpha)  # skip dummy
        for _ in range(self.header.num_image_records):
            self.images.append(SgImageRecord(stream, include_alpha))

    def _find_555_file(self, bitmap_record: SgBitmapRecord, is_external: bool) -> Optional[bytes]:
        name = bitmap_record.filename if is_external else self.sg_filename
        basename = os.path.splitext(os.path.basename(name))[0] + ".555"

        for path in [
            os.path.join(self.base_path, basename),
            os.path.join(self.base_path, '555', basename)
        ]:
            if os.path.exists(path):
                with open(path, 'rb') as f:
                    return f.read()

        # Case-insensitive fallback
        for root, _, files in os.walk(self.base_path):
            for f in files:
                if f.lower() == basename.lower():
                    with open(os.path.join(root, f), 'rb') as file:
                        return file.read()
        return None

    def _get_555_data(self, bitmap_record: SgBitmapRecord, is_external: bool) -> Optional[bytes]:
        key = f"{bitmap_record.filename}_{is_external}"
        if key not in self._555_files:
            self._555_files[key] = self._find_555_file(bitmap_record, is_external)
        return self._555_files[key]

    def _convert_555_to_rgba(self, pixel_array: np.ndarray) -> np.ndarray:
        """Convert 16-bit 555 array to 8-bit RGBA numpy array"""
        r = ((pixel_array >> 10) & 0x1F) << 3
        g = ((pixel_array >> 5) & 0x1F) << 3
        b = (pixel_array & 0x1F) << 3

        # Improve brightness by duplicating high bits into low bits
        r |= (r >> 5)
        g |= (g >> 5)
        b |= (b >> 5)

        # Transparent magenta
        alpha = np.where(pixel_array == 0xf81f, 0, 255).astype(np.uint8)

        rgba = np.stack([r, g, b, alpha], axis=-1).astype(np.uint8)
        return rgba

    def _load_plain_image(self, buffer: bytes, record: SgImageRecord) -> Optional[Image.Image]:
        expected_length = record.width * record.height * 2
        if len(buffer) < expected_length:
            return None

        pixel_data = np.frombuffer(buffer[:expected_length], dtype='<H')
        pixel_data = pixel_data.reshape((record.height, record.width))
        rgba = self._convert_555_to_rgba(pixel_data)

        return Image.fromarray(rgba, mode='RGBA')

    def _load_image_data(self, record: SgImageRecord, bitmap_record: SgBitmapRecord) -> Optional[Image.Image]:
        is_external = bool(record.flags[0])
        data_555 = self._get_555_data(bitmap_record, is_external)
        if not data_555:
            return None

        offset = record.offset - (1 if is_external else 0)
        data_length = record.length + record.alpha_length

        if offset + data_length > len(data_555):
            return None

        buffer = data_555[offset:offset + data_length]

        if record.type in [0, 1, 10, 12, 13]:
            return self._load_plain_image(buffer, record)

        # Add handling for other types here if needed
        return None

    def _convert_images_to_pil(self) -> Dict[str, List[Image.Image]]:
        result: Dict[str, List[Image.Image]] = {}

        for img_record in self.images:
            bitmap_id = img_record.bitmap_id
            if bitmap_id >= len(self.bitmaps):
                continue

            bitmap = self.bitmaps[bitmap_id]
            name = os.path.splitext(bitmap.filename)[0] or f"bitmap_{bitmap_id}"

            img = self._load_image_data(img_record, bitmap)
            if img:
                result.setdefault(name, []).append(img)

        return result
