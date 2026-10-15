"""Native patch framework for the Terra Battle character mods (arm64 libil2cpp.so).

Every character owns ONE native module (tools/natives/<name>_native.py).  A module is self-contained:
  * its own dead-code regions (functions of the unused Mono.Security code) where its helper/hook caves live,
  * its own hook sites (single instructions of the game replaced by a branch into one of its caves),
  * its own copies of every helper routine (find a skill by mark, find/add a status modifier, ...).
Nothing is shared between characters at run time, so any subset of the characters can be installed together.

The build refuses (SystemExit) when two modules overlap: same region bytes, same hook site, a hook inside another
module's region, or a cave that calls into another module's region.

Module API (see natives/*.py):
    m = Module("kana", regions=[(0xB32B60, 3500), ...])
    m.cave("name", [asm lines])           # helper or hook cave; `@name` = address of another cave of the SAME module
    m.hook(0xADDR, "original asm", "cave_name")   # site -> `b cave`; the cave must run the displaced instruction itself
    m.site(0xADDR, "original asm", [lines])       # free-form site patch
Lines accept `@0xADDR` (absolute game address, pc-relative / page-relative for adrp), `@name`, `{FX_x}` placeholders
filled from ctx["fx"], and numeric local labels (`1:` ... `b 1b`).
"""
import os
import re
import struct
import subprocess
import tempfile

# ------------------------------------------------------------------------------------------ game constants (code, not state)
GETTYPE, NEWOBJ, MOD_CTOR, ADDMOD5, EVALUATE = 0xF06550, 0xBFD180, 0x11663E4, 0x102BF94, 0x10285DC
ISBOSS, GETHP, GETATK, SETHP, HEAL = 0x1079B20, 0x10792F0, 0x10794F0, 0x1087E88, 0x1091EF4
RANDOM_RANGE_I = 0xD352C8
LIST_ADD = 0x1ECD688
GET_SKILL_DB = ["adrp x9, @0x2ab3000", "ldr x9, [x9, #0x4a8]", "ldr x9, [x9]", "ldr x9, [x9, #0xa0]", "ldr x0, [x9, #8]"]


def f32bits(x):
    return struct.unpack("<I", struct.pack("<f", x))[0]


def movf(reg_w, sreg, value):
    b = f32bits(value)
    return ["movz %s, #0x%x" % (reg_w, b & 0xFFFF), "movk %s, #0x%x, lsl #16" % (reg_w, b >> 16), "fmov %s, %s" % (sreg, reg_w)]


def asm(base, lines, names=None, fx=None):
    """Assemble `lines` (llvm-mc) as if located at `base`.  `names` maps cave names to addresses (None = size pass)."""
    out, n = [], 0
    for ln in lines:
        head, sep, body = ln.partition(":")
        has_label = sep and head.strip().isdigit()
        body = body.strip() if has_label else ln.strip()
        label = (head.strip() + ": ") if has_label else ""
        if not body:
            continue
        body = re.sub(r"\{FX_(\w+)\}", lambda m: str(fx[m.group(1)]) if fx else "0", body)
        for m in re.finditer(r"@([A-Za-z_]\w*)", body):
            tgt = 0 if names is None else names[m.group(1)]
            body = body.replace(m.group(0), "@%#x" % tgt, 1)
        m = re.search(r"@(0x[0-9a-fA-F]+)", body)
        if m:
            tgt, pc = int(m.group(1), 16), base + 4 * n
            if names is None:
                delta = 0
            elif body.startswith("adrp"):
                delta = (tgt & ~0xFFF) - (pc & ~0xFFF)
            else:
                delta = tgt - pc
                assert delta % 4 == 0, body
            body = body.replace(m.group(0), "#%d" % delta)
        out.append(label + body)
        n += 1
    with tempfile.TemporaryDirectory() as td:
        sp, op, bp = (os.path.join(td, x) for x in ("c.s", "c.o", "c.bin"))
        open(sp, "w").write(".text\n" + "\n".join(out) + "\n")
        r = subprocess.run(["llvm-mc", "-triple=aarch64", "-filetype=obj", sp, "-o", op], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit("assembler error:\n" + r.stderr + "\n--- source ---\n" + open(sp).read())
        subprocess.run(["llvm-objcopy", "-O", "binary", "--only-section=.text", op, bp], check=True)
        return open(bp, "rb").read()


class Module:
    def __init__(self, name, regions, flags=()):
        self.name = name
        self.regions = list(regions)           # [(start_va, size)]
        self.flags = list(flags)               # [(page_va, offset)] .bss bytes this module may use as state (checked for overlap)
        self.caves = {}                        # name -> lines (insertion ordered)
        self.sites = []                        # (addr, orig_asm or None, lines)
        self.addr = {}                         # name -> va (after layout)
        self.fx_names = set()
        self.marks = set()

    # ---- definition -------------------------------------------------------------------------------------------
    def cave(self, name, lines):
        assert name not in self.caves, name
        self.caves[name] = list(lines)

    def hook(self, addr, orig_asm, cave, link=False):
        self.sites.append((addr, orig_asm, ["%s @%s" % ("bl" if link else "b", cave)]))

    def site(self, addr, orig_asm, lines):
        self.sites.append((addr, orig_asm, list(lines)))

    # ---- build ------------------------------------------------------------------------------------------------
    def layout(self):
        sizes = {n: len(asm(0, ls)) for n, ls in self.caves.items()}
        pos = []
        for start, size in self.regions:
            pos.append([start, start + size])
        self.addr, self.sizes = {}, sizes
        for n, sz in sizes.items():
            sz = (sz + 15) & ~15
            for r in pos:
                if r[0] + sz <= r[1]:
                    self.addr[n] = r[0]
                    r[0] += sz
                    break
            else:
                raise SystemExit("native module %s: no room left for cave %s (%d bytes)" % (self.name, n, sizes[n]))
        self.free = sum(r[1] - r[0] for r in pos)

    def assemble(self, ctx):
        """-> (cave_bytes {va: bytes}, site_patches [(va, expect_bytes, new_bytes)])"""
        fx = ctx.get("fx") or {}
        self.layout()
        caves = {}
        for n, ls in self.caves.items():
            caves[self.addr[n]] = asm(self.addr[n], ls, self.addr, fx)
            assert len(caves[self.addr[n]]) == self.sizes[n], n
        sites = []
        for addr, orig, lines in self.sites:
            expect = asm(addr, [x.strip() for x in orig.split(";")], self.addr, fx) if orig else None
            sites.append((addr, expect, asm(addr, lines, self.addr, fx)))
        return caves, sites


# ------------------------------------------------------------------------------------------------------ conflict checks
def check_modules(mods):
    """Hard errors for anything that would couple two characters."""
    owner_sites, ranges = {}, []
    for m in mods:
        for s, sz in m.regions:
            for (lo, hi, o) in ranges:
                if s < hi and lo < s + sz:
                    raise SystemExit("native conflict: region of %s overlaps region of %s" % (m.name, o))
            ranges.append((s, s + sz, m.name))
        for a, _, _ in m.sites:
            if a in owner_sites:
                raise SystemExit("native conflict: hook site %#x used by both %s and %s" % (a, owner_sites[a], m.name))
            owner_sites[a] = m.name
    for a, o in owner_sites.items():
        for lo, hi, ro in ranges:
            if lo <= a < hi:
                raise SystemExit("native conflict: hook site %#x of %s lies inside region of %s" % (a, o, ro))
    for m in mods:                                # no module may call/branch into another module's region
        for ls in list(m.caves.values()) + [x[2] for x in m.sites]:
            for ln in ls:
                for t in re.findall(r"@(0x[0-9a-fA-F]+)", ln):
                    tv = int(t, 16)
                    for lo, hi, ro in ranges:
                        if ro != m.name and lo <= tv < hi:
                            raise SystemExit("native conflict: %s references %#x inside region of %s" % (m.name, tv, ro))
    flags = {}
    for m in mods:
        for f in m.flags:
            if f in flags:
                raise SystemExit("native conflict: state byte %r used by %s and %s" % (f, flags[f], m.name))
            flags[f] = m.name
    marks = {}
    for m in mods:
        for k in m.marks:
            if k in marks:
                raise SystemExit("native conflict: skill mark %d used by %s and %s" % (k, marks[k], m.name))
            marks[k] = m.name


def apply_natives(so, v2o, names, ctx):
    """Install the native modules named in `names` into libil2cpp.so bytes.  Each name is a module in tools/natives/."""
    import importlib
    mods = []
    for n in names:
        mod = importlib.import_module(n)
        mods.append(mod.build(ctx))
    check_modules(mods)
    b = bytearray(so)
    for m in mods:
        caves, sites = m.assemble(ctx)
        for va, code in caves.items():
            o = v2o(va)
            b[o:o + len(code)] = code
        for va, expect, new in sites:
            o = v2o(va)
            if expect is not None and bytes(b[o:o + len(expect)]) != expect:
                raise SystemExit("native %s: unexpected bytes at %#x (wrong libil2cpp.so?)" % (m.name, va))
            b[o:o + len(new)] = new
        ctx.setdefault("log", []).append("native %s: %d caves (%d bytes used, %d free), %d hook sites" % (
            m.name, len(caves), sum(len(c) for c in caves.values()), m.free, len(sites)))
    return bytes(b)


# ------------------------------------------------------------------------------------------ snippet library
# Plain text generators.  Each character module registers its OWN copy of the snippets it needs as its own caves.
def find_skill():
    """x0 = entity, w1 = mark -> x0 = SkillType* of the first unlocked skill with that capacity mark (0 if none), w1 = skill id."""
    return [
        "stp x29, x30, [sp, #-80]!", "mov x29, sp",
        "stp x19, x20, [sp, #16]", "stp x21, x22, [sp, #32]", "stp x23, x24, [sp, #48]",
        "mov w19, w1", "mov x20, x0", "mov x0, xzr", "mov w1, wzr",
        "cbz x20, 8f",
        "ldr x21, [x20, #0x30]", "cbz x21, 8f",
        "ldr x22, [x21, #0xe0]", "cbz x22, 8f",
        "mov w23, wzr",
        "1: ldr w8, [x22, #0x18]", "cmp w23, w8", "b.ge 7f",
        "ldr w9, [x21, #0xdc]", "lsr w9, w9, w23", "tbnz w9, #0, 6f",
        "add x8, x22, x23, lsl #2", "ldr w24, [x8, #0x20]", "cbz w24, 6f",
    ] + GET_SKILL_DB + [
        "cbz x0, 7f", "mov w1, w24", "mov x2, xzr", "bl @%#x" % GETTYPE,
        "cbz x0, 6f", "ldr w9, [x0, #0x84]", "cmp w9, w19", "b.ne 6f",
        "mov w1, w24", "b 8f",
        "6: add w23, w23, #1", "b 1b",
        "7: mov x0, xzr", "mov w1, wzr",
        "8: ldp x23, x24, [sp, #48]", "ldp x21, x22, [sp, #32]", "ldp x19, x20, [sp, #16]", "ldp x29, x30, [sp], #80", "ret",
    ]


def find_range():
    """x0 = entity, w1 = lowest mark, w2 = span -> x0 = SkillType* of the first unlocked skill whose mark is in [w1, w1+w2], w1 = id, w2 = mark."""
    return [
        "stp x29, x30, [sp, #-96]!", "mov x29, sp",
        "stp x19, x20, [sp, #16]", "stp x21, x22, [sp, #32]", "stp x23, x24, [sp, #48]", "str x25, [sp, #64]",
        "mov w19, w1", "mov w25, w2", "mov x20, x0", "mov x0, xzr", "mov w1, wzr", "mov w2, wzr",
        "cbz x20, 8f",
        "ldr x21, [x20, #0x30]", "cbz x21, 8f",
        "ldr x22, [x21, #0xe0]", "cbz x22, 8f",
        "mov w23, wzr",
        "1: ldr w8, [x22, #0x18]", "cmp w23, w8", "b.ge 7f",
        "ldr w9, [x21, #0xdc]", "lsr w9, w9, w23", "tbnz w9, #0, 6f",
        "add x8, x22, x23, lsl #2", "ldr w24, [x8, #0x20]", "cbz w24, 6f",
    ] + GET_SKILL_DB + [
        "cbz x0, 7f", "mov w1, w24", "mov x2, xzr", "bl @%#x" % GETTYPE,
        "cbz x0, 6f", "ldr w9, [x0, #0x84]", "sub w10, w9, w19", "cmp w10, w25", "b.hi 6f",
        "mov w1, w24", "mov w2, w9", "b 8f",
        "6: add w23, w23, #1", "b 1b",
        "7: mov x0, xzr", "mov w1, wzr", "mov w2, wzr",
        "8: ldr x25, [sp, #64]", "ldp x23, x24, [sp, #48]", "ldp x21, x22, [sp, #32]", "ldp x19, x20, [sp, #16]", "ldp x29, x30, [sp], #96", "ret",
    ]


def find_mod():
    """x0 = entity, x1 = SkillType* -> x0 = the entity's StatusModifier made from that skill (0 if none).  Leaf."""
    return [
        "mov x2, x0", "mov x0, xzr", "cbz x2, 9f",
        "ldr x3, [x2, #0x48]", "cbz x3, 9f",
        "ldr x4, [x3, #0x10]", "cbz x4, 9f",
        "ldr w5, [x4, #0x18]", "ldr x4, [x4, #0x10]", "cbz x4, 9f",
        "ldr w6, [x4, #0x18]", "cmp w5, w6", "csel w5, w5, w6, lo", "add x4, x4, #0x20", "mov w6, wzr",
        "1: cmp w6, w5", "b.hs 9f", "ldr x7, [x4, x6, lsl #3]", "add w6, w6, #1", "cbz x7, 1b",
        "ldr x8, [x7, #0x40]", "cmp x8, x1", "b.ne 1b", "mov x0, x7",
        "9: ret",
    ]


def add_mod(force=1):
    """x0 = entity, x1 = SkillType*, w2 = life (-1 permanent) -> x0 = new StatusModifier.  force=1 skips the resist roll."""
    return [
        "stp x29, x30, [sp, #-64]!", "mov x29, sp", "stp x19, x20, [sp, #16]", "stp x21, x22, [sp, #32]",
        "mov x19, x0", "mov x20, x1", "mov w21, w2",
        "adrp x8, @0x2ab9000", "ldr x8, [x8, #0xbb0]", "ldr x0, [x8]", "bl @%#x" % NEWOBJ, "mov x22, x0",
        "mov x1, x20", "mov x2, x19", "mov w3, w21", "mov x4, xzr", "bl @%#x" % MOD_CTOR,
        "ldr x0, [x19, #0x48]", "cbz x0, 1f",
        "mov x1, x22", "mov w2, #100", "mov x3, xzr", "mov w4, #%d" % force, "mov w5, #1", "bl @%#x" % ADDMOD5,
        "1: mov x0, x22",
        "ldp x21, x22, [sp, #32]", "ldp x19, x20, [sp, #16]", "ldp x29, x30, [sp], #64", "ret",
    ]


def get_skill_type():
    """w1 = skill id -> x0 = SkillType* (0 if none)."""
    return ["stp x29, x30, [sp, #-16]!", "mov x29, sp"] + GET_SKILL_DB + [
        "cbz x0, 9f", "mov x2, xzr", "bl @%#x" % GETTYPE, "9: ldp x29, x30, [sp], #16", "ret"]


def fx_play():
    """x0 = entity, w1 = particleEffectSet id (1-based): one-shot particle on the entity."""
    return [
        "stp x29, x30, [sp, #-16]!", "mov x29, sp", "mov x2, x0",
        "adrp x8, @0x2a5f000", "ldr x8, [x8, #0x928]", "ldr x8, [x8]", "ldr x8, [x8, #0xa0]", "ldr x0, [x8]", "cbz x0, 9f",
        "mov x3, xzr", "adrp x8, @0x21c4000", "ldr s0, [x8, #0x86c]", "bl @0x10cb088",
        "9: ldp x29, x30, [sp], #16", "ret",
    ]
