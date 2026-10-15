"""Tiny il2cpp (metadata v24) method-address resolver for arm64 libil2cpp.so.

find_methods(metadata, so, names) -> {name: [(typeName, address), ...]}
"""
import struct
import sys


def cstr(b, o):
    return b[o:b.index(b"\0", o)].decode("utf-8", "replace")


class Meta:
    def __init__(self, m):
        self.m = m
        magic, ver = struct.unpack_from("<Ii", m, 0)
        assert magic == 0xFAB11BAF, hex(magic)
        self.version = ver
        h = struct.unpack_from("<%di" % 64, m, 8)
        # v24 header pairs (offset,size) in order
        names = ["stringLiteral", "stringLiteralData", "string", "events", "properties", "methods",
                 "parameterDefaultValues", "fieldDefaultValues", "fieldAndParameterDefaultValueData",
                 "fieldMarshaledSizes", "parameters", "fields", "genericParameters",
                 "genericParameterConstraints", "genericContainers", "nestedTypes", "interfaces",
                 "vtableMethods", "interfaceOffsets", "typeDefinitions", "rgctxEntries", "images",
                 "assemblies"]
        self.sec = {n: (h[2 * i], h[2 * i + 1]) for i, n in enumerate(names)}

    def s(self, idx):
        return cstr(self.m, self.sec["string"][0] + idx)

    def methods(self):
        off, size = self.sec["methods"]
        rec = 56 if self.version >= 24 else 64
        for i in range(size // rec):
            f = struct.unpack_from("<12i4H", self.m, off + i * rec)
            yield {"name": f[0], "declaringType": f[1], "methodIndex": f[6], "token": f[11],
                   "paramCount": f[15]}

    def type_name(self, ti):
        off, size = self.sec["typeDefinitions"]
        rec = getattr(self, "_rec", None)
        if rec is None:
            for r in (92, 88, 96, 100, 104, 84):
                if size % r == 0:
                    try:
                        names = [self.s(struct.unpack_from("<i", self.m, off + k * r)[0]) for k in range(0, size // r, max(1, size // r // 50))]
                        if all(n and n.replace("_", "a").replace("`", "a").replace("<", "a").replace(">", "a").replace(".", "a").replace("-", "a").replace("$", "a").replace("=", "a").isalnum() for n in names):
                            rec = r; break
                    except Exception:
                        pass
            self._rec = rec
        name_idx, ns_idx = struct.unpack_from("<ii", self.m, off + ti * rec)
        ns = self.s(ns_idx)
        return (ns + "." if ns else "") + self.s(name_idx)

    def type_count(self):
        # count from images: sum typeCount
        off, size = self.sec["images"]
        total = 0
        for i in range(size // 40):
            f = struct.unpack_from("<10i", self.m, off + i * 40)
            total += f[3]
        return total


class Elf:
    def __init__(self, b):
        self.b = b
        (phoff,) = struct.unpack_from("<Q", b, 0x20)
        phentsize, phnum = struct.unpack_from("<HH", b, 0x36)
        self.loads = []
        dyn = None
        for i in range(phnum):
            p_type, p_flags, p_off, p_vaddr, _, p_filesz, p_memsz, _ = struct.unpack_from("<IIQQQQQQ", b, phoff + i * phentsize)
            if p_type == 1:
                self.loads.append((p_vaddr, p_off, p_filesz, p_memsz, p_flags))
            if p_type == 2:
                dyn = (p_off, p_filesz)
        self.relocs = {}
        d = {}
        for i in range(dyn[1] // 16):
            tag, val = struct.unpack_from("<qQ", b, dyn[0] + i * 16)
            if tag == 0:
                break
            d[tag] = val
        rela, relasz = d.get(7), d.get(8)
        if rela:
            ro = self.v2o(rela)
            for i in range(relasz // 24):
                off, info, add = struct.unpack_from("<QQq", b, ro + i * 24)
                if info & 0xFFFFFFFF == 1027:  # R_AARCH64_RELATIVE
                    self.relocs[off] = add

    def v2o(self, va):
        for v, o, fs, ms, _ in self.loads:
            if v <= va < v + fs:
                return va - v + o
        return None

    def q(self, va):
        if va in self.relocs:
            return self.relocs[va]
        o = self.v2o(va)
        return struct.unpack_from("<Q", self.b, o)[0] if o is not None else None

    def is_code(self, va):
        return any(v <= va < v + ms and f & 1 for v, o, fs, ms, f in self.loads)

    def is_data(self, va):
        return any(v <= va < v + ms and not f & 1 for v, o, fs, ms, f in self.loads)


def find_code_registration(elf, count):
    # look for {u64 count; ptr -> array of `count` code pointers}
    for v, o, fs, ms, f in elf.loads:
        if f & 1:
            continue
        for va in range(v, v + fs - 16, 8):
            if elf.q(va) == count:
                p = elf.q(va + 8)
                if p and elf.is_data(p):
                    ok = all(elf.is_code(elf.q(p + 8 * k) or 0) or elf.q(p + 8 * k) == 0 for k in (0, 1, 2, count // 2, count - 1))
                    if ok and elf.is_code(elf.q(p) or 0):
                        yield va, p


def find_methods(meta_bytes, so_bytes, names):
    meta = Meta(meta_bytes)
    elf = Elf(so_bytes)
    ms = list(meta.methods())
    count = max(m["methodIndex"] for m in ms) + 1
    regs = list(find_code_registration(elf, count))
    if not regs:
        raise RuntimeError(f"CodeRegistration not found (count={count})")
    _, ptrs = regs[0]
    out = {}
    for m in ms:
        n = meta.s(m["name"])
        if n in names and m["methodIndex"] >= 0:
            out.setdefault(n, []).append((meta.type_name(m["declaringType"]), hex(elf.q(ptrs + 8 * m["methodIndex"]))))
    return out, regs


if __name__ == "__main__":
    mb = open(sys.argv[1], "rb").read()
    sb = open(sys.argv[2], "rb").read()
    res, regs = find_methods(mb, sb, set(sys.argv[3:]))
    print("CodeRegistration candidates:", [(hex(a), hex(b)) for a, b in regs][:3])
    for k, v in res.items():
        print(k, v)
