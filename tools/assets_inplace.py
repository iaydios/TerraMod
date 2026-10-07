"""Faithful in-place Terra Battle asset bundle builder.

Takes an ORIGINAL game bundle whose name has the same length as the new one
(e.g. img_2124 -> img_3001) and only overwrites bytes in place:
  * names (bundle file name, container path, texture name, CAB id) - equal length
  * texture pixels - same width/height/format, so the same byte count
The serialized file layout stays byte-for-byte identical to the original.
Blocks are written uncompressed (flag 0x40, like the original's streamed flag).
"""
import ctypes
import hashlib
import os
import struct
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from assets import decrypt_enca, encrypt_enca, serialized_objects, texture_info  # noqa: E402
from assets_build import prefix_for  # noqa: E402
from unityfs import Bundle, lz4_compress  # noqa: E402

_etc = ctypes.CDLL(os.path.join(os.path.dirname(os.path.abspath(__file__)), "libetc2.so"))


def encode_texture(img: Image.Image, w: int, h: int, fmt: int) -> bytes:
    im = img.convert("RGBA").resize((w, h), Image.LANCZOS) if img.size != (w, h) else img.convert("RGBA")
    im = im.transpose(Image.FLIP_TOP_BOTTOM)  # Unity stores bottom-up
    if fmt == 4:  # RGBA32
        return im.tobytes()
    if fmt == 3:  # RGB24
        return im.convert("RGB").tobytes()
    if fmt == 47:  # ETC2_RGBA8
        r, g, b, a = im.split()
        bgra = Image.merge("RGBA", (b, g, r, a)).tobytes()
        src = ctypes.create_string_buffer(bgra, len(bgra))
        dst = ctypes.create_string_buffer(w * h)
        _etc.etc2_rgba(src, dst, w, h)
        return dst.raw
    raise ValueError(f"unsupported texture format {fmt}")


def save_uncompressed(b: Bundle) -> bytes:
    (name,) = b.order
    data, fl = b.files[name]
    node = struct.pack(">qqI", 0, len(data), fl) + name.encode() + b"\0"
    binfo = b"\0" * 16 + struct.pack(">i", 1) + struct.pack(">IIH", len(data), len(data), 0x40)
    binfo += struct.pack(">i", 1) + node
    cbinfo = lz4_compress(binfo)
    head = b"UnityFS\0" + struct.pack(">I", 6) + b.player_version.encode() + b"\0" + b.engine_version.encode() + b"\0"
    total = len(head) + 20 + len(cbinfo) + len(data)
    head += struct.pack(">qIII", total, len(cbinfo), len(binfo), 0x43)
    return head + cbinfo + data


def repath_ids(sfile: bytes, new_name: str) -> bytes:
    """Give every non-AssetBundle object a new PathID derived from the new asset path
    (object table + PPtr references inside the AssetBundle object)."""
    from unityfs import SerializedFile
    sf = SerializedFile(sfile)
    raw = bytearray(sfile)
    folder = {"img_": "pieces", "illust_": "illust", "buddy_": "buddyimages", "bimg_": "buddythumbs"}[
        next(p for p in ("img_", "illust_", "buddy_", "bimg_") if new_name.startswith(p))]
    mapping = {}
    for pid, ob in sf.objects.items():
        if ob["class"] == 142:
            continue
        h = hashlib.md5(f"assets/images/{folder}/{new_name}.png#{ob['class']}".encode()).digest()
        npid = abs(struct.unpack("<q", h[:8])[0]) | 2
        if pid < 1:
            npid = -npid  # keep the object table sorted by PathID, like the original (Unity requires it)
        mapping[pid] = npid
        struct.pack_into("<q", raw, ob["entry"], npid)
    for pid, ob in sf.objects.items():
        if ob["class"] != 142:
            continue
        s0 = sf.data_offset + ob["start"]
        seg = bytes(raw[s0:s0 + ob["size"]])
        for old, new in mapping.items():
            seg = seg.replace(struct.pack("<q", old), struct.pack("<q", new))
        raw[s0:s0 + ob["size"]] = seg
    return bytes(raw)


def build(template_path, inv, old_name, new_name, img):
    assert len(old_name) == len(new_name), "names must have equal length"
    tpl = os.path.basename(template_path)
    old_pre, new_pre = tpl[:32], prefix_for(new_name)
    assert old_pre == prefix_for(old_name), "template prefix mismatch"
    b = Bundle(decrypt_enca(open(template_path, "rb").read(), inv))
    (cab,) = b.order
    data, fl = b.files[cab]
    new_cab = "CAB-" + hashlib.md5(f"terramod/{new_name}".encode()).hexdigest()
    raw = bytearray(data)
    # pixels in place
    for pid, cid, od in serialized_objects(bytes(raw)):
        if cid == 28:
            ti = texture_info(od)
            px = encode_texture(img, ti["width"], ti["height"], ti["format"])
            assert len(px) == ti["size"]
            pos = bytes(raw).find(od)
            k = od.rfind(struct.pack("<i", ti["size"]))
            raw[pos + k + 4:pos + k + 4 + ti["size"]] = px
    out = bytes(raw)
    for a, c in ((old_pre + old_name, new_pre + new_name), (cab[4:], new_cab[4:]), (old_name, new_name)):
        out = out.replace(a.encode(), c.encode())
    assert len(out) == len(data)
    out = repath_ids(out, new_name)
    from unityfs import SerializedFile
    ids = list(SerializedFile(out).objects.keys())
    assert ids == sorted(ids), f"object table not sorted by PathID: {ids}"
    b.files = {new_cab: [out, fl]}
    b.order = [new_cab]
    plain = save_uncompressed(b)
    return encrypt_enca(plain, inv), plain, new_pre + new_name + ".bin"
