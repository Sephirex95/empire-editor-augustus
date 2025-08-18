import os
import struct
import io
from typing import List, Dict, Optional
from PIL import Image
import sys
from array import array as u16array

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
    
    def _convert_555_to_rgba_bytes(self, pixel_bytes: bytes, width: int, height: int) -> bytes:
        # Interpret as unsigned 16-bit little-endian
        a = u16array('H')
        a.frombytes(pixel_bytes[: width * height * 2])
        if sys.byteorder != 'little':
            a.byteswap()
    
        out = bytearray(width * height * 4)
        j = 0
        for px in a:
            r5 = (px >> 10) & 0x1F
            g5 = (px >> 5) & 0x1F
            b5 = px & 0x1F
            # scale 5→8 bits
            r = (r5 << 3) | (r5 >> 2)
            g = (g5 << 3) | (g5 >> 2)
            b = (b5 << 3) | (b5 >> 2)
            a8 = 0 if px == 0xF81F else 255
    
            out[j + 0] = r
            out[j + 1] = g
            out[j + 2] = b
            out[j + 3] = a8
            j += 4
        return bytes(out)
    
    def _load_plain_image(self, buffer: bytes, record: SgImageRecord):
        expected_length = record.width * record.height * 2
        if len(buffer) < expected_length:
            return None
        rgba_bytes = self._convert_555_to_rgba_bytes(
            buffer[:expected_length], record.width, record.height
        )
        return Image.frombytes("RGBA", (record.width, record.height), rgba_bytes)

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
        """Decode RLE-like sprite types (256/257/276) without NumPy."""
        width, height = record.width, record.height
        length = record.length
    
        # RGBA output buffer
        out = bytearray(width * height * 4)
    
        def put_px(x: int, y: int, r: int, g: int, b: int, a: int):
            if 0 <= x < width and 0 <= y < height:
                idx = (y * width + x) * 4
                out[idx:idx+4] = bytes((r, g, b, a))
    
        x = y = i = 0
        try:
            while i < length and y < height:
                c = buffer[i]
                i += 1
                if c == 255:
                    # Skip run
                    if i >= length:
                        break
                    skip = buffer[i]
                    i += 1
                    x += skip
                    while x >= width:
                        x -= width
                        y += 1
                        if y >= height:
                            break
                else:
                    # Literal run of 'c' pixels
                    for _ in range(c):
                        if i + 1 >= length or y >= height:
                            break
                        px = buffer[i] | (buffer[i + 1] << 8)
                        i += 2
                        r5 = (px >> 10) & 0x1F
                        g5 = (px >> 5) & 0x1F
                        b5 = px & 0x1F
                        r = (r5 << 3) | (r5 >> 2)
                        g = (g5 << 3) | (g5 >> 2)
                        b = (b5 << 3) | (b5 >> 2)
                        a8 = 0 if px == 0xF81F else 255
                        put_px(x, y, r, g, b, a8)
                        x += 1
                        if x >= width:
                            x = 0
                            y += 1
                            if y >= height:
                                break
            return Image.frombytes("RGBA", (width, height), bytes(out))
        except Exception as e:
            print(f"[ERROR] Failed to decode sprite image (type {record.type}): {e}")
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


