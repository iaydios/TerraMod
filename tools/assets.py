"""Decrypt Terra Battle ENCA asset files and inspect/decode the Texture2D inside."""
import struct
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from unityfs import Bundle, _cstr  # noqa: E402

MAGIC = b"ENCA"


def _calc_index(index, size):
    low = index & 0xFF
    if (index >> 8) != ((size - 1) >> 8):
        low ^= 0xFF
    return (index & ~0xFF) | low


def _t(v):
    return ((v >> 4) | ((v & 0x0F) << 4)) ^ 0xFF


def decrypt_enca(src, inv):
    if not src.startswith(MAGIC):
        return src
    body = src[4:]
    size = len(body)
    plain = bytearray(size)
    for i, v in enumerate(body):
        plain[_calc_index(size - 1 - i, size)] = _t(inv[v])
    return bytes(plain)


def encrypt_enca(plain, inv):
    fwd = [0] * 256
    for i, v in enumerate(inv):
        fwd[v] = i
    tinv = [0] * 256
    for v in range(256):
        tinv[_t(v)] = v
    size = len(plain)
    body = bytearray(size)
    for i in range(size):
        body[i] = fwd[tinv[plain[_calc_index(size - 1 - i, size)]]]
    return MAGIC + bytes(body)


def serialized_objects(raw):
    """Yield (pathID, classID, data) from a v17 SerializedFile (type trees allowed)."""
    msize, fsize, ver, doff = struct.unpack_from(">IIII", raw, 0)
    o = 20
    _, o = _cstr(raw, o)
    o += 4
    tree = raw[o]; o += 1
    (nt,) = struct.unpack_from("<i", raw, o); o += 4
    types = []
    for _ in range(nt):
        cid, stripped, sidx = struct.unpack_from("<iBh", raw, o); o += 7
        if cid == 114 or sidx >= 0:
            o += 16
        o += 16
        if tree:
            nn, sb = struct.unpack_from("<ii", raw, o); o += 8 + nn * 24 + sb
        types.append(cid)
    (no,) = struct.unpack_from("<i", raw, o); o += 4
    o = (o + 3) & ~3
    for _ in range(no):
        pid, st, sz, ti = struct.unpack_from("<qIIi", raw, o); o += 20
        yield pid, types[ti], raw[doff + st: doff + st + sz]


def texture_info(data):
    o = 0
    (n,) = struct.unpack_from("<i", data, o)
    name = data[4:4 + n].decode(); o = (4 + n + 3) & ~3
    o += 4  # m_ForcedFallbackFormat
    o += 4  # m_DownscaleFallback + align
    w, h, csize, fmt, mips = struct.unpack_from("<iiiii", data, o)
    return {"name": name, "width": w, "height": h, "format": fmt, "mips": mips, "size": csize}


FORMATS = {1: "Alpha8", 3: "RGB24", 4: "RGBA32", 5: "ARGB32", 7: "RGB565", 13: "RGBA4444",
           34: "ETC_RGB4", 47: "ETC2_RGBA8", 45: "ETC2_RGB", 10: "DXT1", 12: "DXT5", 63: "ETC_RGB4Crunched",
           64: "ETC2_RGBA8Crunched", 28: "DXT1Crunched", 29: "DXT5Crunched"}


def inspect(path, inv):
    plain = decrypt_enca(open(path, "rb").read(), inv)
    b = Bundle(plain)
    out = []
    for name in b.order:
        data, fl = b.files[name]
        if fl & 4:
            for pid, cid, od in serialized_objects(data):
                if cid == 28:
                    ti = texture_info(od)
                    ti["format_name"] = FORMATS.get(ti["format"], str(ti["format"]))
                    out.append(ti)
                elif cid == 213:
                    out.append({"sprite_object": True})
    return out


if __name__ == "__main__":
    meta = open(sys.argv[1], "rb").read()
    inv = meta[0x601CAD:0x601CAD + 256]
    for p in sys.argv[2:]:
        print(os.path.basename(p), inspect(p, inv))
