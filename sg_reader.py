import os
import struct
import io
from typing import List, Dict, Optional, Set, Mapping
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
    _KEEP_ALL = object()  # private sentinel
    def __init__(self, sg_filename: str):
        self.sg_filename = sg_filename
        self.base_path = os.path.dirname(sg_filename)
        self.base_name = os.path.splitext(os.path.basename(sg_filename))[0]
        self.header: Optional[SgHeader] = None
        self.bitmaps: List[SgBitmapRecord] = []
        self.images: List[SgImageRecord] = []
        self._555_files: Dict[str, bytes] = {}


    def load(self) -> Dict[str, List[Image.Image]]:
        with open(self.sg_filename, 'rb') as f:
            stream = io.BytesIO(f.read())

        self.header = SgHeader(stream)
        self._load_bitmaps(stream)
        stream.seek(680 + self._max_bitmap_records() * 200)

        include_alpha = self.header.version >= 0xd6
        self._load_images(stream, include_alpha)

        return self._convert_images_to_pil(selection=None)

    def load_filtered(self, *specs, free_after: bool = True) -> Dict[str, List[Image.Image]]:
        """
        Varargs selection:
          - "empire_bits"                  -> keep all indices for that name
          - ("The_empire", 0)              -> keep index 0 only
          - ("empire_panels", [1,2,3])     -> keep specific indices
          - ("empire_bits", "*") or (...)  -> keep all indices
        """
        with open(self.sg_filename, 'rb') as f:
            stream = io.BytesIO(f.read())

        self.header = SgHeader(stream)
        self._load_bitmaps(stream)
        stream.seek(680 + self._max_bitmap_records() * 200)

        include_alpha = self.header.version >= 0xd6
        self._load_images(stream, include_alpha)

        selection = self._build_selection(specs)
        out = self._convert_images_to_pil(selection=selection)

        if free_after:
            self.images.clear()
            self.bitmaps.clear()
            self._555_files.clear()
            self.header = None

        return out

    def _build_selection(self, specs):
        """
        Returns dict: { name -> _KEEP_ALL or set(indices) }
        """
        sel = {}
        for spec in specs:
            if isinstance(spec, str):
                name = spec
                sel[name] = self._KEEP_ALL
            elif isinstance(spec, tuple) and len(spec) == 2:
                name, which = spec
                if which in ("*", Ellipsis):
                    sel[name] = self._KEEP_ALL
                elif isinstance(which, int):
                    sel.setdefault(name, set()).add(which)
                elif isinstance(which, (list, tuple, set)):
                    sel.setdefault(name, set()).update(int(i) for i in which)
                else:
                    raise ValueError(f"Bad selection for {name}: {which!r}")
            else:
                raise ValueError(f"Bad spec: {spec!r}")
        return sel
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
        for _ in range(self.header.num_image_records + 1):  # include possible dummy
            self.images.append(SgImageRecord(stream, include_alpha))

    def _find_555_file(self, bitmap_record: SgBitmapRecord, is_external: bool) -> Optional[bytes]:
        expected_name = bitmap_record.filename if is_external else self.base_name
        target_basename = os.path.splitext(os.path.basename(expected_name))[0] + ".555"
        
        search_paths = [
            self.base_path,
            os.path.join(self.base_path, "555")
        ]
        
        # Try direct paths first (case-sensitive)
        for base_dir in search_paths:
            exact_path = os.path.join(base_dir, target_basename)
            if os.path.exists(exact_path):
                with open(exact_path, "rb") as f:
                    return f.read()
        
        # Case-insensitive fallback
        for base_dir in search_paths:
            if not os.path.isdir(base_dir):
                continue  # Skip if not a valid dir
            for root, _, files in os.walk(base_dir):
                for fname in files:
                    if fname.lower() == target_basename.lower():
                        found_path = os.path.join(root, fname)
                        print(f"[INFO] Found .555 file (case-insensitive): {found_path}")
                        with open(found_path, "rb") as f:
                            return f.read()
    
        print(f"[WARN] Could not find .555 file for: {bitmap_record.filename} (external={is_external})")
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
        elif record.type in [256, 257, 276]:
            return self._load_sprite_image(buffer, record)

        else:
            print(f"Unknown record type: {record.type}, skipping image with offset {record.offset}")
            return None
        # Add handling for other types here if needed
        return None
    
    def _load_sprite_image(self, buffer: bytes, record: SgImageRecord) -> Optional[Image.Image]:
        width, height = record.width, record.height
        image = np.zeros((height, width, 4), dtype=np.uint8)
        x = y = i = 0
        length = record.length
    
        try:
            while i < length:
                c = buffer[i]
                i += 1
    
                if c == 255:
                    skip = buffer[i]
                    i += 1
                    x += skip
                    while x >= width:
                        x -= width
                        y += 1
                else:
                    for _ in range(c):
                        if i + 1 >= length:
                            break  # Prevent overflow
                        pixel = buffer[i] | (buffer[i + 1] << 8)
                        i += 2
                        r = ((pixel >> 10) & 0x1F) << 3
                        g = ((pixel >> 5) & 0x1F) << 3
                        b = (pixel & 0x1F) << 3
                        # Improve brightness (duplicate high bits into low bits)
                        r |= (r >> 5)
                        g |= (g >> 5)
                        b |= (b >> 5)
                        a = 0 if pixel == 0xf81f else 255
                        if 0 <= x < width and 0 <= y < height:
                            image[y, x] = [r, g, b, a]
                        x += 1
                        if x >= width:
                            x = 0
                            y += 1
            return Image.fromarray(image, mode='RGBA')
        except Exception as e:
            print(f"[ERROR] Failed to decode sprite image (type 256/257/276): {e}")
            return None

    def _convert_images_to_pil(self, selection=None) -> Dict[str, List[Image.Image]]:
        result: Dict[str, List[Image.Image]] = {}
        index_per_name: Dict[str, int] = {}
    
        for img_record in self.images:
            bitmap_id = img_record.bitmap_id
            if bitmap_id >= len(self.bitmaps):
                print(f"Warning: Invalid bitmap_id {bitmap_id}, max allowed is {len(self.bitmaps)-1}")
                continue
    
            bitmap = self.bitmaps[bitmap_id]
            # normalize to basename without extension
            name = os.path.splitext(os.path.basename(bitmap.filename))[0] or f"bitmap_{bitmap_id}"
            idx = index_per_name.get(name, 0)
    
            # selection check BEFORE decoding
            if selection is not None:
                rule = selection.get(name)
                if rule is None:
                    index_per_name[name] = idx + 1
                    continue
                if rule is not self._KEEP_ALL and idx not in rule:
                    index_per_name[name] = idx + 1
                    continue
    
            img = self._load_image_data(img_record, bitmap)
            if img:
                result.setdefault(name, []).append(img)
    
            index_per_name[name] = idx + 1
    
        return result


