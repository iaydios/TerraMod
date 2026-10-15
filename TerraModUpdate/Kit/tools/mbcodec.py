"""Schema-inferring MonoBehaviour codec for Terra Battle databases.

learn(raw, json) walks the original raw bytes guided by the extracted JSON and
records, for every field path, its binary kind (i32 / f32 / plain str / encrypted
str / u8 ...). encode(json, schema) then re-serializes (possibly modified) JSON.
Correctness is proven by encode(original_json) == original_raw byte-for-byte.
"""
import re
import struct

HEADER = 32  # m_GameObject, m_Enabled(+align), m_Script, m_Name("")
META_OFF = 0x601CAD


def load_tables(metadata: bytes):
    inv = metadata[META_OFF:META_OFF + 256]
    if len(set(inv)) != 256:
        raise ValueError("decryption table at expected offset is not a permutation")
    fwd = [0] * 256
    for i, v in enumerate(inv):
        fwd[v] = i
    return inv, fwd


def dec(b, inv):
    return bytes(reversed([inv[x] for x in b])).decode("utf-8", errors="replace")


def enc(s, fwd):
    return bytes(fwd[x] for x in reversed(s.encode("utf-8")))


def norm(path):
    return re.sub(r"\[\d+\]", "[]", path)


class Learner:
    def __init__(self, raw, inv):
        self.raw, self.inv, self.o, self.schema = raw, inv, HEADER, {}

    def put(self, path, kind):
        p = norm(path)
        old = self.schema.get(p)
        if old and old != kind:
            # empty strings can't tell plain from encrypted; keep the informative one
            if {old, kind} <= {"s", "es", "s?"}:
                kind = old if old != "s?" else kind
            else:
                raise ValueError(f"conflicting kinds at {p}: {old} vs {kind}")
        self.schema[p] = kind

    def walk(self, v, path):
        r = self.raw
        if isinstance(v, dict):
            for k, x in v.items():
                self.walk(x, f"{path}.{k}")
        elif isinstance(v, list):
            (n,) = struct.unpack_from("<i", r, self.o)
            if n != len(v):
                raise ValueError(f"list len mismatch at {path} @{self.o}: {n} vs {len(v)}")
            self.o += 4
            for i, x in enumerate(v):
                self.walk(x, f"{path}[{i}]")
        elif isinstance(v, str):
            (n,) = struct.unpack_from("<i", r, self.o)
            b = r[self.o + 4:self.o + 4 + n]
            if n == 0:
                kind = "s?"
            elif b == v.encode("utf-8"):
                kind = "s"
            elif dec(b, self.inv) == v:
                kind = "es"
            else:
                raise ValueError(f"string mismatch at {path} @{self.o}")
            self.o = (self.o + 4 + n + 3) & ~3
            self.put(path, kind)
        elif isinstance(v, float):
            (x,) = struct.unpack_from("<f", r, self.o)
            if x != v and not (x != x and v != v):
                raise ValueError(f"float mismatch at {path} @{self.o}: {x} vs {v}")
            self.o += 4
            self.put(path, "f")
        elif isinstance(v, int):
            (x,) = struct.unpack_from("<i", r, self.o)
            if x != v:
                raise ValueError(f"int mismatch at {path} @{self.o}: {x} vs {v}")
            self.o += 4
            self.put(path, "i")
        else:
            raise TypeError(f"{path}: {type(v)}")


def learn(raw, data, inv, skip=("m_GameObject", "m_Enabled", "m_Script", "m_Name")):
    L = Learner(raw, inv)
    for k, v in data.items():
        if k not in skip:
            L.walk(v, k)
    if L.o != len(raw):
        raise ValueError(f"trailing bytes: parsed {L.o} of {len(raw)}")
    # an always-empty string whose sibling fields (same parent struct, e.g. the other
    # languages of a NameString) are encrypted is an encrypted string too
    for p, k in list(L.schema.items()):
        if k == "s?":
            parent = p.rsplit(".", 1)[0]
            sib = [v for q, v in L.schema.items() if q.rsplit(".", 1)[0] == parent and q != p]
            if "es" in sib:
                L.schema[p] = "es"
            elif "s" in sib:
                L.schema[p] = "s"
    return L.schema


def encode(data, schema, header, fwd, skip=("m_GameObject", "m_Enabled", "m_Script", "m_Name")):
    out = bytearray(header)

    def w(v, path):
        if isinstance(v, dict):
            for k, x in v.items():
                w(x, f"{path}.{k}")
        elif isinstance(v, list):
            out.extend(struct.pack("<i", len(v)))
            for i, x in enumerate(v):
                w(x, f"{path}[{i}]")
        else:
            p = norm(path)
            kind = schema.get(p)
            if kind is None:
                raise KeyError(f"unknown field {p} (not present in original data)")
            if kind in ("s", "es", "s?"):
                if not isinstance(v, str):
                    raise TypeError(f"{p} must be a string")
                b = enc(v, fwd) if kind == "es" else v.encode("utf-8")
                if kind == "s?" and v:
                    raise ValueError(f"{p}: can't tell if encrypted (all originals empty)")
                out.extend(struct.pack("<i", len(b)) + b)
                while len(out) % 4:
                    out.append(0)
            elif kind == "f":
                out.extend(struct.pack("<f", float(v)))
            elif kind == "i":
                if isinstance(v, float) or isinstance(v, str):
                    raise TypeError(f"{p} must be an integer")
                out.extend(struct.pack("<i", v))

    for k, v in data.items():
        if k not in skip:
            w(v, k)
    return bytes(out)
