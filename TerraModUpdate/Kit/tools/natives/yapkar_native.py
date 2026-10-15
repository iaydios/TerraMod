"""Native module for Y'apkar? Lambda (chr 1292).  Self-contained: own region, own hook sites, own helper copies.

Marks (SkillType.capacity):
  4901 Delusion   Lambda heals 10% max HP every turn (immunity itself is the game's Status Guard).  While Lambda lives, a Y'apkar (557) of the
                  same side also heals 10%/turn and gets a copy of the immunity modifier.
  4902 Madness    visible = pincer/chain fire attack.  Hidden id+1 (DEF%, 4911) and id+2 (SDEF%, 4912): 557 gets +BUFF_PERCENT DEF and SDEF.
                  Hidden id+3..id+5 = ice / dark / thunder column attacks, id+6..id+9 = fire / ice / dark / thunder ROW attacks, id+10..id+13 = X-shape attacks, appended to the emitted list by the SkillAttack hook (SAH).
  4903 Craving    (shown as Awakening) visible = pincer/chain solar attack.  Hidden id+1 (ATK%, 4913), id+2 (SATK%, 4914): 557 gets +BUFF_PERCENT.
                  Hidden id+3..id+5 = moon / gravity / photon column attacks, id+6..id+9 = sun / moon / gravity / photon ROW attacks, id+10..id+13 = X-shape attacks.
  4904 Awakening  (shown as Aura) while Lambda lives, every dead 557 of her side is revived at REVIVE_FRACTION HP each turn.
Hooks: BattleManager.PreEvaluateStatusManager (once per turn) and the SkillAttack coroutine (list of emitted skill ids).
"""
from nativelib import (Module, find_skill, find_mod, add_mod, GET_SKILL_DB, GETTYPE, NEWOBJ, MOD_CTOR, ADDMOD5, GETHP, f32bits)

HEAL, HPDEC, REVIVE = 0x1091EF4, 0xCA6FB4, 0x107F3B0
LIST_ADD = 0x1ECD688
ENUM_WRAP, ENUM_GET, ENUM_NEXT, ENUM_CUR, ENUM_DISP = 0x1E8E3C0, 0x1B2F18C, 0x1B245C0, 0x1B24628, 0x1B24568
SITE_TICK, SITE_TICK_BACK = 0xCD9AC4, 0xCD9AC8      # PreEvaluateStatusManager: ldr x19,[x19,#0x1f0]   (x19 = BattleManager)
SITE_SAH, SITE_SAH_BACK = 0xCC3EEC, 0xCC3EF0        # <SkillAttack>c__Iterator7.MoveNext: ldr x20,[x19,#0x18]
LAMBDA_ID, BASE_ID = 1292, 557
M_DELUSION, M_MADNESS, M_CRAVING, M_AWAKEN = 4901, 4902, 4903, 4904
ELEM_FIRST, ELEM_COUNT = 3, 11          # hidden id+3..id+13: 3 more column elements + 4 row elements + 4 X-shape elements (visible skill = pincer+column; row twins = pincer+row)
H_FIRST = 4911
BUFF_PERCENT = 100.0                 # Sam 2026-10-13: symbiosis +100%
REVIVE_FRACTION = 0.5                # Sam: field revive 1/2 HP (also used for the endless 557 revive)

REGIONS = [(0xB3398C, 8352)]         # Mono.Security.X509.PKCS12.GetBytes (never executed)
MARKS = {4901, 4902, 4903, 4904, 4911, 4912, 4913, 4914, 4941, 4942, 4943, 4944, 4945, 4946, 4947, 4951, 4952, 4953, 4954, 4955, 4956, 4957, 4961, 4962, 4963, 4964, 4971, 4972, 4973, 4974}


def build(ctx):
    m = Module("yapkar", REGIONS)
    m.marks = MARKS
    m.cave("fs", find_skill())
    m.cave("fm", find_mod())
    m.cave("am", add_mod(1))

    # x0 = entity: heal 10% of max HP (at least 1) if alive
    m.cave("heal10", [
        "stp x29, x30, [sp, #-32]!", "mov x29, sp", "str x19, [sp, #16]", "mov x19, x0",
        "cbz x19, 9f", "ldr x8, [x19, #0x38]", "cbz x8, 9f", "ldrb w9, [x8, #0x36]", "cbnz w9, 9f",
        "ldr x1, [x8, #0x60]", "mov x0, xzr", "mov x2, xzr", "bl @%#x" % HPDEC, "cmp w0, #1", "b.lt 9f",
        "mov x0, x19", "mov x1, xzr", "bl @%#x" % GETHP, "fcvtzs w1, s0",
        "mov w9, #10", "sdiv w1, w1, w9", "mov w8, #1", "cmp w1, #1", "csel w1, w1, w8, ge",
        "mov x0, x19", "mov w2, wzr", "mov w3, wzr", "bl @%#x" % HEAL,
        "9: ldr x19, [sp, #16]", "ldp x29, x30, [sp], #32", "ret",
    ])
    # x0 = entity: value of every helper modifier (mark 4911..4914) := 0.  Leaf.
    m.cave("zero", [
        "mov x2, x0", "cbz x2, 9f",
        "ldr x3, [x2, #0x48]", "cbz x3, 9f",
        "ldr x4, [x3, #0x10]", "cbz x4, 9f",
        "ldr w5, [x4, #0x18]", "ldr x4, [x4, #0x10]", "cbz x4, 9f",
        "ldr w6, [x4, #0x18]", "cmp w5, w6", "csel w5, w5, w6, lo", "add x4, x4, #0x20", "mov w6, wzr",
        "mov w10, #%d" % H_FIRST,
        "1: cmp w6, w5", "b.hs 9f", "ldr x7, [x4, x6, lsl #3]", "add w6, w6, #1", "cbz x7, 1b",
        "ldr x8, [x7, #0x40]", "cbz x8, 1b", "ldr w9, [x8, #0x84]", "sub w9, w9, w10", "cmp w9, #3", "b.hi 1b",
        "str wzr, [x7, #0x24]", "b 1b",
        "9: ret",
    ])
    # x0 = entity, w1 = helper skill id: make sure the entity has that modifier (life 2) with value BUFF_PERCENT
    bp = f32bits(BUFF_PERCENT)
    m.cave("sync", [
        "stp x29, x30, [sp, #-48]!", "mov x29, sp", "stp x19, x20, [sp, #16]", "str x21, [sp, #32]",
        "mov x19, x0", "mov w20, w1",
    ] + GET_SKILL_DB + [
        "cbz x0, 9f", "mov w1, w20", "mov x2, xzr", "bl @%#x" % GETTYPE, "cbz x0, 9f", "mov x21, x0",
        "mov x0, x19", "mov x1, x21", "bl @fm", "cbnz x0, 2f",
        "mov x0, x19", "mov x1, x21", "mov w2, #2", "bl @am", "cbz x0, 9f", "b 3f",
        "2: mov w8, #2", "stp w8, w8, [x0, #0x18]",
        "3: movz w8, #0x%x, lsl #16" % (bp >> 16), "str w8, [x0, #0x24]",
        "9: ldr x21, [sp, #32]", "ldp x19, x20, [sp, #16]", "ldp x29, x30, [sp], #48", "ret",
    ])
    # x0 = entity (a 557), w1 = enabled, x2 = Delusion SkillType* (0 if none), w3 = Madness id (0), w4 = Craving id (0)
    m.cave("apply", [
        "stp x29, x30, [sp, #-80]!", "mov x29, sp", "stp x19, x20, [sp, #16]", "stp x21, x22, [sp, #32]", "stp x23, x24, [sp, #48]",
        "mov x19, x0", "mov w20, w1", "mov x21, x2", "mov w22, w3", "mov w23, w4",
        "cbnz w20, 1f",
        "mov x0, x19", "bl @zero", "b 9f",
        "1: cbz x21, 3f",
        "mov x0, x19", "bl @heal10",
        "mov x0, x19", "mov x1, x21", "bl @fm", "cbnz x0, 2f",
        "mov x0, x19", "mov x1, x21", "mov w2, #2", "bl @am", "b 3f",
        "2: mov w8, #2", "stp w8, w8, [x0, #0x18]",
        "3: cbz w22, 4f",
        "mov x0, x19", "add w1, w22, #1", "bl @sync",
        "mov x0, x19", "add w1, w22, #2", "bl @sync",
        "4: cbz w23, 9f",
        "mov x0, x19", "add w1, w23, #1", "bl @sync",
        "mov x0, x19", "add w1, w23, #2", "bl @sync",
        "9: ldp x23, x24, [sp, #48]", "ldp x21, x22, [sp, #32]", "ldp x19, x20, [sp, #16]", "ldp x29, x30, [sp], #80", "ret",
    ])
    # x0 = BattleManager, w1 = side of Lambda: revive every dead 557 of that side at REVIVE_FRACTION HP (same walk as BattleManager.ReviveAll)
    m.cave("rev", [
        "stp x29, x30, [sp, #-96]!", "mov x29, sp", "stp x19, x20, [sp, #16]", "stp x21, x22, [sp, #32]", "str x23, [sp, #48]",
        "mov w20, w1", "ldr x19, [x0, #0x1f0]", "cbz x19, 9f",
        "adrp x9, @0x2a44000", "ldr x9, [x9, #0xa20]", "mov x0, x19", "ldr x1, [x9]", "bl @%#x" % ENUM_WRAP, "cbz x0, 9f",
        "adrp x9, @0x2acc000", "ldr x9, [x9, #0x930]", "ldr x1, [x9]", "add x8, sp, #64", "bl @%#x" % ENUM_GET,
        "adrp x21, @0x2a2f000", "ldr x21, [x21, #0x810]", "adrp x22, @0x2add000", "ldr x22, [x22, #0x90]",
        "1: ldr x1, [x21]", "add x0, sp, #64", "bl @%#x" % ENUM_NEXT, "tbz w0, #0, 8f",
        "ldr x1, [x22]", "add x0, sp, #64", "bl @%#x" % ENUM_CUR, "mov x23, x0", "cbz x23, 1b",
        "ldr x8, [x23, #0x38]", "cbz x8, 1b", "ldr w9, [x8, #0x2c]", "cmp w9, w20", "b.ne 1b",
        "ldrb w9, [x8, #0x38]", "cbnz w9, 1b", "ldrb w9, [x8, #0x36]", "cbz w9, 1b",
        "ldr x9, [x23, #0x30]", "cbz x9, 1b", "ldr w10, [x9, #0x14]", "mov w11, #%d" % BASE_ID, "cmp w10, w11", "b.ne 1b",
        "mov x0, x23", "movz w8, #0x%x, lsl #16" % (f32bits(REVIVE_FRACTION) >> 16), "fmov s0, w8", "mov w1, #1", "mov x2, xzr", "bl @%#x" % REVIVE,
        "b 1b",
        "8: adrp x9, @0x2a92000", "ldr x9, [x9, #0x6b0]", "add x0, sp, #64", "ldr x1, [x9]", "bl @%#x" % ENUM_DISP,
        "9: ldr x23, [sp, #48]", "ldp x21, x22, [sp, #32]", "ldp x19, x20, [sp, #16]", "ldp x29, x30, [sp], #96", "ret",
    ])
    # x0 = BattleManager.  Grid at bm+0x1e8 (Entity[,]).  Pass 1 finds a living Lambda; pass 2 walks every living 557.
    m.cave("main", [
        "stp x29, x30, [sp, #-112]!", "mov x29, sp",
        "stp x19, x20, [sp, #16]", "stp x21, x22, [sp, #32]", "stp x23, x24, [sp, #48]", "stp x25, x26, [sp, #64]", "stp x27, x28, [sp, #80]",
        "mov x19, x0", "mov x24, xzr", "mov x25, xzr", "mov w26, wzr", "mov w27, wzr", "mov w28, wzr",
        "ldr x20, [x19, #0x1e8]", "cbz x20, 9f",
        "ldr x8, [x20, #0x10]", "cbz x8, 9f",
        "ldr x9, [x8]", "ldr x21, [x8, #0x10]", "cbz x21, 9f", "mul x21, x9, x21",
        "mov x22, xzr",
        "1: cmp x22, x21", "b.hs 2f",
        "add x8, x20, x22, lsl #3", "ldr x23, [x8, #0x20]", "add x22, x22, #1",
        "cbz x23, 1b",
        "ldr x8, [x23, #0x38]", "cbz x8, 1b", "ldrb w9, [x8, #0x36]", "cbnz w9, 1b",
        "ldr x8, [x23, #0x30]", "cbz x8, 1b", "ldr w9, [x8, #0x14]", "mov w10, #%d" % LAMBDA_ID, "cmp w9, w10", "b.ne 1b",
        "mov x24, x23",
        "2: cbz x24, 5f",
        "ldr x8, [x24, #0x38]", "ldr w28, [x8, #0x2c]",
        "mov x0, x24", "mov w1, #%d" % M_DELUSION, "bl @fs", "mov x25, x0",
        "mov x0, x24", "mov w1, #%d" % M_MADNESS, "bl @fs", "cmp x0, #0", "csel w26, w1, wzr, ne",
        "mov x0, x24", "mov w1, #%d" % M_CRAVING, "bl @fs", "cmp x0, #0", "csel w27, w1, wzr, ne",
        "mov x0, x24", "mov w1, #%d" % M_AWAKEN, "bl @fs", "cmp x0, #0", "cset w8, ne", "str w8, [sp, #96]",
        "ldr w8, [sp, #96]", "cbz w8, 4f",
        "mov x0, x19", "mov w1, w28", "bl @rev",
        "4: cbz x25, 5f",
        "mov x0, x24", "bl @heal10",
        "5: mov x22, xzr",
        "6: cmp x22, x21", "b.hs 9f",
        "add x8, x20, x22, lsl #3", "ldr x23, [x8, #0x20]", "add x22, x22, #1",
        "cbz x23, 6b",
        "ldr x8, [x23, #0x38]", "cbz x8, 6b", "ldrb w9, [x8, #0x36]", "cbnz w9, 6b",
        "ldr w11, [x8, #0x2c]",
        "ldr x8, [x23, #0x30]", "cbz x8, 6b", "ldr w9, [x8, #0x14]", "mov w10, #%d" % BASE_ID, "cmp w9, w10", "b.ne 6b",
        "mov w1, wzr", "cbz x24, 7f", "cmp w11, w28", "b.ne 7f", "mov w1, #1",
        "7: mov x0, x23", "mov x2, x25", "mov w3, w26", "mov w4, w27", "bl @apply",
        "b 6b",
        "9: ldp x27, x28, [sp, #80]", "ldp x25, x26, [sp, #64]", "ldp x23, x24, [sp, #48]", "ldp x21, x22, [sp, #32]", "ldp x19, x20, [sp, #16]",
        "ldp x29, x30, [sp], #112", "ret",
    ])
    m.cave("tick", [
        "stp x29, x30, [sp, #-16]!", "mov x0, x19", "bl @main", "ldp x29, x30, [sp], #16",
        "ldr x19, [x19, #0x1f0]", "b @%#x" % SITE_TICK_BACK,
    ])
    # SkillAttack coroutine: for every Madness / Craving skill in the emitted-id list, append the hidden element skills (id+3..id+13)
    m.cave("sah", [
        "stp x29, x30, [sp, #-96]!", "mov x29, sp",
        "stp x19, x20, [sp, #16]", "stp x21, x22, [sp, #32]", "stp x23, x24, [sp, #48]", "stp x25, x26, [sp, #64]",
        "ldr x20, [x19, #0x18]", "cbz x20, 9f",
        "ldr w21, [x20, #0x18]", "mov w22, wzr",
        "1: cmp w22, w21", "b.ge 9f",
        "ldr x8, [x20, #0x10]", "cbz x8, 9f", "ldr w9, [x8, #0x18]", "cmp w22, w9", "b.hs 9f",
        "add x8, x8, x22, lsl #2", "ldr w23, [x8, #0x20]", "add w22, w22, #1",
        "cbz w23, 1b",
    ] + GET_SKILL_DB + [
        "cbz x0, 9f", "mov w1, w23", "mov x2, xzr", "bl @%#x" % GETTYPE, "cbz x0, 1b",
        "ldr w9, [x0, #0x84]", "mov w10, #%d" % M_MADNESS, "cmp w9, w10", "b.eq 2f", "mov w10, #%d" % M_CRAVING, "cmp w9, w10", "b.ne 1b",
        "2: mov w24, #%d" % ELEM_FIRST,
        "3: mov x0, x20", "add w1, w23, w24",
        "adrp x2, @0x2ad5000", "ldr x2, [x2, #0x848]", "ldr x2, [x2]", "bl @%#x" % LIST_ADD,
        "add w24, w24, #1", "cmp w24, #%d" % (ELEM_FIRST + ELEM_COUNT), "b.lt 3b", "b 1b",
        "9: ldp x25, x26, [sp, #64]", "ldp x23, x24, [sp, #48]", "ldp x21, x22, [sp, #32]", "ldp x19, x20, [sp, #16]", "ldp x29, x30, [sp], #96",
        "ldr x20, [x19, #0x18]", "b @%#x" % SITE_SAH_BACK,
    ])
    m.hook(SITE_TICK, "ldr x19, [x19, #0x1f0]", "tick")
    m.hook(SITE_SAH, "ldr x20, [x19, #0x18]", "sah")
    return m
