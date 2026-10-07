"""Small, verified code patches for the arm64 libil2cpp.so of Terra Battle 5.5.7.

Two opt-in skill features, each switched on only by data in a SkillType, so every
original skill keeps its exact behaviour:

  * star range  -- SkillType.range == 10 (X) with sx >= 7 also hits the full row
                   and column (a "米" / 8-way pattern to the board edges).
                   Patch: BattleManager.IterateX cell test.
  * random power -- SkillType.successRate == 4242 (a field only status skills read) multiplies the skill damage by
                   a weighted random step (MULT_BASE + MULT_STEP*k, see MULT_PROBS), drawn with GameRandom.Range (the game's synced RNG).
                   Patch: SkillEvaluator._damageAction power multiply.

Code caves live in Mono.Security.Authenticode.AuthenticodeDeformatter.VerifyCounterSignature
(2800 bytes, only reachable from Authenticode file-signature checks that the game never runs).
Every patched location is checked against the expected original bytes first.
"""
import struct
import subprocess
import tempfile

CAVE = 0xAFC890            # AuthenticodeDeformatter::VerifyCounterSignature
CAVE_X = CAVE
CAVE_R = CAVE + 0x40
GAME_RANDOM_RANGE_F = 0xD350CC   # GameRandom::Range(float, float)
RANDOM_MARK = 4242

SITE_X = 0xCE4604          # IterateX: cmp w8, w9 ; b.ne 0xce46b8
SITE_X_SKIP = 0xCE46B8
SITE_R = 0xF0CE10          # _damageAction: fmul s9, s10, s9


def _llvm(lines):
    with tempfile.NamedTemporaryFile("w", suffix=".s", delete=False) as f:
        f.write("\n".join(lines) + "\n")
        p = f.name
    out = subprocess.run(["llvm-mc", "-triple=aarch64", "-show-encoding", p],
                         capture_output=True, text=True, check=True).stdout
    enc = []
    for line in out.splitlines():
        if "encoding: [" in line:
            bs = line.split("encoding: [")[1].split("]")[0].split(",")
            enc.append(bytes(int(b, 16) for b in bs))
    assert len(enc) == len(lines), out
    return enc


def _b(pc, tgt, link=False):
    off = (tgt - pc) // 4
    return struct.pack("<I", (0x94000000 if link else 0x14000000) | (off & 0x3FFFFFF))


def _bcond(pc, tgt, cond):
    off = (tgt - pc) // 4
    assert -(1 << 18) <= off < (1 << 18)
    return struct.pack("<I", 0x54000000 | ((off & 0x7FFFF) << 5) | cond)


def _cbz(pc, tgt, reg):
    off = (tgt - pc) // 4
    assert -(1 << 18) <= off < (1 << 18)
    return struct.pack("<I", 0x34000000 | ((off & 0x7FFFF) << 5) | reg)


EQ, NE, GE, LT = 0x0, 0x1, 0xA, 0xB


def cave_x_code():
    a = CAVE_X
    mov1, cmp89, cmpr, mov0, ret = _llvm(["mov w16, #1", "cmp w8, w9", "cmp w21, #7", "mov w16, #0", "ret"])
    L1 = a + 8 * 4
    L0 = a + 7 * 4
    code = [mov1, cmp89, _bcond(a + 8, L1, EQ), cmpr, _bcond(a + 16, L0, LT),
            _cbz(a + 20, L1, 8), _cbz(a + 24, L1, 9), mov0, ret]
    return b"".join(code)


# Discrete random multiplier: MULT_BASE + MULT_STEP * k with probability MULT_PROBS[k] (percent).
# 1.0 / 1.5 / ... / 5.0, most likely 2.5.
MULT_BASE, MULT_STEP = 1.0, 0.5
MULT_PROBS = [8, 12, 16, 20, 16, 12, 8, 5, 3]


def multiplier_table():
    assert sum(MULT_PROBS) == 100
    probs = [p / 100 for p in MULT_PROBS]
    cum, c = [], 0.0
    for p in probs:
        c += p
        cum.append(c)
    cum[-1] = 2.0                               # catch-all for u == 1.0
    return probs, cum


def cave_r_code():
    """Assembled with llvm-mc; the bl to GameRandom.Range is patched in afterwards."""
    import os
    probs, cum = multiplier_table()
    src = """
    .text
    fmul s9, s10, s9
    ldr w16, [x21, #0x78]
    mov w17, #%d
    cmp w16, w17
    b.ne 9f
    stp x29, x30, [sp, #-16]!
    mov x29, sp
    movi d0, #0
    fmov s1, #1.0
    mov x0, xzr
CALL:
    nop
    adr x16, TABLE
    mov w17, #0
1:  ldr s1, [x16, w17, uxtw #2]
    fcmp s0, s1
    b.lt 2f
    add w17, w17, #1
    cmp w17, #%d
    b.lt 1b
2:  scvtf s1, w17
    ldr s2, STEP
    fmul s1, s1, s2
    ldr s2, BASE
    fadd s1, s1, s2
    fmul s9, s9, s1
    ldp x29, x30, [sp], #16
9:  ret
    .p2align 2
STEP:
    .float %r
BASE:
    .float %r
TABLE:
""" % (RANDOM_MARK, len(cum) - 1, MULT_STEP, MULT_BASE) + "".join("    .float %.9f\n" % c for c in cum)
    with tempfile.TemporaryDirectory() as td:
        sp, op, bp = (os.path.join(td, n) for n in ("c.s", "c.o", "c.bin"))
        open(sp, "w").write(src)
        subprocess.run(["llvm-mc", "-triple=aarch64", "-filetype=obj", sp, "-o", op], check=True)
        subprocess.run(["llvm-objcopy", "-O", "binary", "--only-section=.text", op, bp], check=True)
        code = bytearray(open(bp, "rb").read())
    call_off = 10 * 4                            # index of the CALL nop
    assert code[call_off:call_off + 4] == bytes.fromhex("1f2003d5"), code[call_off:call_off + 4].hex()
    code[call_off:call_off + 4] = _b(CAVE_R + call_off, GAME_RANDOM_RANGE_F, link=True)
    return bytes(code)


EXPECT = {
    SITE_X: _llvm(["cmp w8, w9"])[0] + _bcond(SITE_X + 4, SITE_X_SKIP, NE),
    SITE_R: _llvm(["fmul s9, s10, s9"])[0],
}


def patch(so: bytes, v2o, features=("star_range", "random_power")) -> bytes:
    b = bytearray(so)

    def put(va, data, expect=None):
        o = v2o(va)
        if expect is not None and bytes(b[o:o + len(expect)]) != expect:
            raise SystemExit(f"native patch: unexpected bytes at {va:#x} (wrong libil2cpp.so?)")
        b[o:o + len(data)] = data

    if "star_range" in features:
        cx = cave_x_code()
        assert len(cx) <= CAVE_R - CAVE_X
        put(SITE_X, _b(SITE_X, CAVE_X, link=True) + _cbz(SITE_X + 4, SITE_X_SKIP, 16), EXPECT[SITE_X])
        put(CAVE_X, cx)
    if "random_power" in features:
        cr = cave_r_code()
        assert len(cr) <= 0x400
        put(SITE_R, _b(SITE_R, CAVE_R, link=True), EXPECT[SITE_R])
        put(CAVE_R, cr)
    return bytes(b)
