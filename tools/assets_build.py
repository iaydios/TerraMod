"""Build Terra Battle character resource files (Pieces / Illust bundles, Profile JPGs).

Uses an existing game bundle as template: renames it, swaps the texture for a new
RGBA32 image, gives it a fresh CAB name / bundle name, and ENCA-encrypts it.
"""
import hashlib
import os
import struct
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assets import decrypt_enca, encrypt_enca, serialized_objects  # noqa: E402
from unityfs import Bundle, SerializedFile  # noqa: E402


def _str(s: bytes) -> bytes:
    b = struct.pack("<i", len(s)) + s
    return b + b"\0" * ((-len(b)) % 4)


def replace_aligned_strings(data: bytes, mapping: dict) -> bytes:
    """Replace length-prefixed, 4-aligned strings (whole-value matches only)."""
    out = bytearray()
    i = 0
    while i < len(data):
        hit = None
        if i % 4 == 0 and i + 4 <= len(data):
            (n,) = struct.unpack_from("<i", data, i)
            if 0 < n < 512 and i + 4 + n <= len(data):
                s = data[i + 4:i + 4 + n]
                if s in mapping:
                    hit = (s, 4 + n + ((-(4 + n)) % 4))
        if hit:
            out += _str(mapping[hit[0]])
            i += hit[1]
        else:
            out.append(data[i])
            i += 1
    return bytes(out)


def build_texture(od: bytes, new_name: bytes, img: Image.Image) -> bytes:
    (n,) = struct.unpack_from("<i", od, 0)
    head_end = (4 + n + 3) & ~3
    w, h = img.size
    pix = img.convert("RGBA").transpose(Image.FLIP_TOP_BOTTOM).tobytes()
    (old_size,) = struct.unpack_from("<i", od, head_end + 16)
    data_pos = od.rfind(struct.pack("<i", old_size))
    assert data_pos > head_end and struct.unpack_from("<i", od, data_pos)[0] == old_size
    mid = bytearray(od[head_end:data_pos])
    struct.pack_into("<iiiii", mid, 8, w, h, len(pix), 4, 1)  # width, height, size, RGBA32, mips
    tail = od[data_pos + 4 + old_size:]
    return _str(new_name) + bytes(mid) + struct.pack("<i", len(pix)) + pix + tail


def make_bundle(template_path, inv, old_name, new_name, img, prefix):
    """old_name/new_name like 'img_64' / 'img_3001'. Returns encrypted bytes."""
    tpl_file = os.path.basename(template_path)
    old_prefix = tpl_file[:32]
    b = Bundle(decrypt_enca(open(template_path, "rb").read(), inv))
    (cab,) = b.order
    data, fl = b.files[cab]
    sf = SerializedFile(data)
    folder = "pieces" if old_name.startswith("img_") else "illust"
    mapping = {
        f"{old_prefix}{old_name}.bin".encode(): f"{prefix}{new_name}.bin".encode(),
        f"assets/images/{folder}/{old_name}.png".encode(): f"assets/images/{folder}/{new_name}.png".encode(),
        old_name.encode(): new_name.encode(),
    }
    for pid, cid, od in list(serialized_objects(data)):
        if cid == 28:
            sf.replace(pid, build_texture(od, new_name.encode(), img))
        elif cid == 142:
            sf.replace(pid, replace_aligned_strings(od, mapping))
    new_cab = "CAB-" + hashlib.md5(f"terramod/{prefix}{new_name}".encode()).hexdigest()
    b.files = {new_cab: [sf.bytes(), fl]}
    b.order = [new_cab]
    plain = b.save()
    return encrypt_enca(plain, inv), plain


def make_manifest(template_manifest, old_name, new_name, plain_bundle):
    txt = open(template_manifest, encoding="utf-8").read()
    import zlib
    txt = txt.replace(old_name + ".png", new_name + ".png")
    import re
    txt = re.sub(r"CRC: \d+", f"CRC: {zlib.crc32(plain_bundle)}", txt)
    return txt


ASSET_SALT = "tbguardmistkeycodehiso"  # recovered from the client; verified on original files


def prefix_for(name: str) -> str:
    """32-hex prefix the game expects: md5(name + salt), e.g. name='img_64' or 'profile_64'."""
    return hashlib.md5((name + ASSET_SALT).encode()).hexdigest()
