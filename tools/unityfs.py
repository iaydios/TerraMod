"""Minimal UnityFS (bundle format 6) reader/writer + SerializedFile object table helper.

Only what is needed to swap one MonoBehaviour's raw bytes inside data.unity3d.
"""
import ctypes
import os
import struct

_lz4 = ctypes.CDLL(os.path.join(os.path.dirname(os.path.abspath(__file__)), "liblz4.so"))


def lz4_decompress(src: bytes, size: int) -> bytes:
    dst = ctypes.create_string_buffer(size)
    n = _lz4.LZ4_decompress_safe(src, dst, len(src), size)
    if n != size:
        raise ValueError(f"LZ4 decompress failed ({n} != {size})")
    return dst.raw


def lz4_compress(src: bytes) -> bytes:
    bound = _lz4.LZ4_compressBound(len(src))
    dst = ctypes.create_string_buffer(bound)
    n = _lz4.LZ4_compress_HC(src, dst, len(src), bound, 9)
    if n <= 0:
        raise ValueError("LZ4 compress failed")
    return dst.raw[:n]


def _decompress(data: bytes, usize: int, flags: int) -> bytes:
    kind = flags & 0x3F
    if kind == 0:
        return data
    if kind in (2, 3):
        return lz4_decompress(data, usize)
    if kind == 1:
        import lzma
        props = data[0]
        lc, lp, pb = props % 9, (props // 9) % 5, props // 45
        dict_size = struct.unpack_from("<I", data, 1)[0]
        d = lzma.LZMADecompressor(lzma.FORMAT_RAW, filters=[{"id": lzma.FILTER_LZMA1, "lc": lc, "lp": lp, "pb": pb, "dict_size": dict_size}])
        return d.decompress(data[5:], usize)[:usize]
    raise ValueError(f"unsupported compression {kind}")


def _cstr(b: bytes, o: int):
    e = b.index(b"\0", o)
    return b[o:e].decode(), e + 1


class Bundle:
    def __init__(self, raw: bytes):
        o = 0
        sig, o = _cstr(raw, o)
        assert sig == "UnityFS", sig
        (self.version,) = struct.unpack_from(">I", raw, o); o += 4
        self.player_version, o = _cstr(raw, o)
        self.engine_version, o = _cstr(raw, o)
        size, csize, usize, flags = struct.unpack_from(">qIII", raw, o); o += 20
        assert self.version == 6, self.version
        assert not flags & 0x80, "blocksinfo at end not supported"
        binfo = _decompress(raw[o:o + csize], usize, flags); o += csize
        p = 16
        (nblocks,) = struct.unpack_from(">i", binfo, p); p += 4
        blocks = []
        for _ in range(nblocks):
            blocks.append(struct.unpack_from(">IIH", binfo, p)); p += 10
        (nnodes,) = struct.unpack_from(">i", binfo, p); p += 4
        nodes = []
        for _ in range(nnodes):
            off, sz, fl = struct.unpack_from(">qqI", binfo, p); p += 20
            name, p = _cstr(binfo, p)
            nodes.append((off, sz, fl, name))
        chunks = []
        for us, cs, fl in blocks:
            chunks.append(_decompress(raw[o:o + cs], us, fl)); o += cs
        stream = b"".join(chunks)
        self.files = {}  # name -> [bytes, flags]
        self.order = []
        for off, sz, fl, name in nodes:
            self.files[name] = [stream[off:off + sz], fl]
            self.order.append(name)

    def save(self, compress=True, block_size=0x20000) -> bytes:
        stream = b""
        nodes = b""
        for name in self.order:
            data, fl = self.files[name]
            nodes += struct.pack(">qqI", len(stream), len(data), fl) + name.encode() + b"\0"
            stream += data
        blocks = []
        body = []
        for i in range(0, len(stream), block_size):
            chunk = stream[i:i + block_size]
            if compress:
                c = lz4_compress(chunk)
                blocks.append(struct.pack(">IIH", len(chunk), len(c), 3)); body.append(c)
            else:
                blocks.append(struct.pack(">IIH", len(chunk), len(chunk), 0)); body.append(chunk)
        binfo = b"\0" * 16 + struct.pack(">i", len(blocks)) + b"".join(blocks)
        binfo += struct.pack(">i", len(self.order)) + nodes
        cbinfo = lz4_compress(binfo)
        head = b"UnityFS\0" + struct.pack(">I", 6) + self.player_version.encode() + b"\0" + self.engine_version.encode() + b"\0"
        body = b"".join(body)
        total = len(head) + 20 + len(cbinfo) + len(body)
        head += struct.pack(">qIII", total, len(cbinfo), len(binfo), 0x43)
        return head + cbinfo + body


class SerializedFile:
    """Parses enough of a v17 SerializedFile to locate and replace object data."""

    def __init__(self, raw: bytes):
        self.raw = bytearray(raw)
        msize, fsize, ver, doff = struct.unpack_from(">IIII", raw, 0)
        assert ver == 17, ver
        self.data_offset = doff
        assert raw[16] == 0, "big-endian metadata not supported"
        o = 20
        self.unity_version, o = _cstr(raw, o)
        o += 4  # platform
        tree = raw[o]; o += 1
        (ntypes,) = struct.unpack_from("<i", raw, o); o += 4
        self.types = []
        for _ in range(ntypes):
            cid, stripped, sidx = struct.unpack_from("<iBh", raw, o); o += 7
            if cid == 114 or sidx >= 0:
                o += 16
            o += 16
            if tree:
                nn, sb = struct.unpack_from("<ii", raw, o); o += 8 + nn * 24 + sb
            self.types.append(cid)
        (nobj,) = struct.unpack_from("<i", raw, o); o += 4
        o = (o + 3) & ~3
        self.objects = {}
        for _ in range(nobj):
            pid, start, size, tidx = struct.unpack_from("<qIIi", raw, o)
            self.objects[pid] = {"entry": o, "start": start, "size": size, "class": self.types[tidx]}
            o += 20

    def get(self, pid: int) -> bytes:
        ob = self.objects[pid]
        s = self.data_offset + ob["start"]
        return bytes(self.raw[s:s + ob["size"]])

    def replace(self, pid: int, data: bytes):
        """Append new data at file end and repoint the object (old bytes left unused)."""
        ob = self.objects[pid]
        while len(self.raw) % 8:
            self.raw.append(0)
        start = len(self.raw) - self.data_offset
        self.raw += data
        struct.pack_into("<II", self.raw, ob["entry"] + 8, start, len(data))
        ob["start"], ob["size"] = start, len(data)
        struct.pack_into(">I", self.raw, 4, len(self.raw))

    def bytes(self) -> bytes:
        return bytes(self.raw)
