"""Native module for Kana Lambda (chr 1290).  Self-contained: own regions, own hook sites, own helper copies.

Marks (SkillType.capacity):
  4611 Heartbeat     moving an ally with Kana gives that ally a 1-turn all-stats modifier (hidden skill id+1, status 53, spower 1.1).
  4601 Virus Bullet  pincer/chain poison attack.  The poison is forced (the resist roll is skipped, except on Kana herself) and every poison tick heals Kana
                     by the tick damage.  (also carried by the Heart-Throb Virus of the buddy weapon only through successRate 4444, see LINE)
  4612 Contrast      a MAGIC damage hit on Kana from a monster is nullified and adds one stack of the hidden permanent Pink Heart Poison
                     (hidden skill id+1, mark 4614) to the attacker.  Physical hits are not touched.
  4613 Queen Bee     pincer/chain: every living ENEMY (entity kind 1) gets one more stack of that poison.  The poison skill is the one hidden behind
                     Contrast (id+1 of the mark 4612 skill), so Queen Bee needs Contrast unlocked.
  4614 Pink Heart Poison  hidden permanent poison.  Tick = Kana ATK x 2 x 0.5 x stacks, healed back to Kana.
  successRate 4444   pincer line: the skill hits the whole row (left/right pincer) or column (up/down pincer) -- Heart-Throb Virus of the buddy.
Hook sites (all unique to this module):
  0xCD30D8   BattleManager swap: bl Entity.OnHit(mover, displaced)                -> Heartbeat
  0x10BEA0C  ChrBaseParams.EmitMultiSkill after the emit check: and w8,w23,#0x1f  -> Queen Bee
  0x10917A8  Entity.SkillDamage entry: stp d9,d8,[sp,#-0x70]!                     -> Contrast
  0x11668B8  StatusModifier.PoisonDamage: bl GameRandom.Range                      -> poison tick heals the caster
  0x102C270  StatusManager.AddModifier: and w8,w24,#1                              -> forced poison
  0xCC4048   <SkillAttack> iterator: bl SkillEvaluator.ExecSkill                   -> pincer line
"""
from nativelib import (Module, find_skill, find_mod, add_mod, get_skill_type, GET_SKILL_DB, GETTYPE, GETATK, HEAL, EVALUATE, f32bits, movf)

ONHIT, HPDEC, RANGE_F, EXEC_SKILL = 0x108D02C, 0xCA6FB4, 0xD350CC, 0xF06AAC
IS_MAGIC = 0x1024BE0                     # SkillType.IsTypeOfMagic
HEART_MARK, BULLET_MARK, CONTRAST_MARK, QUEEN_MARK, QUEEN_POISON_MARK = 4611, 4601, 4612, 4613, 4614
LINE_MARK = 4444
SITE_PUSH, SITE_EMIT, SITE_DMG = 0xCD30D8, 0x10BEA0C, 0x10917A8
SITE_RED, SITE_FORCE, SITE_LINE = 0x11668B8, 0x102C270, 0xCC4048

REGIONS = [(0xB32B60, 3500), (0x9FC314, 3460)]     # PKCS12.CertificateSafeBag (two generic instances, never executed)
MARKS = {HEART_MARK, BULLET_MARK, CONTRAST_MARK, QUEEN_MARK, QUEEN_POISON_MARK}


def build(ctx):
    m = Module("kana", REGIONS)
    m.intended_writes = {"force": ["x24"]}          # the force cave sets bit 0 of w24 (AddModifier flags) on purpose; every other callee-saved register must come back unchanged
    m.marks = MARKS
    m.cave("fs", find_skill())
    m.cave("fm", find_mod())
    m.cave("am", add_mod(1))

    # ---- Heartbeat: x0 = mover, x1 = displaced entity (x2 = 0 as the original call expects)
    m.cave("heart", [
        "stp x29, x30, [sp, #-48]!", "mov x29, sp", "stp x19, x20, [sp, #16]", "stp x21, x22, [sp, #32]",
        "mov x19, x0", "mov x20, x1",
        "bl @%#x" % ONHIT,
        "cbz x19, 9f", "cbz x20, 9f", "cmp x19, x20", "b.eq 9f",
        "ldr x8, [x20, #0x38]", "cbz x8, 9f", "ldr w9, [x8, #0x2c]", "cbnz w9, 9f", "ldrb w9, [x8, #0x36]", "cbnz w9, 9f",
        "mov x0, x19", "mov w1, #%d" % HEART_MARK, "bl @fs", "cbz x0, 9f",
        "add w1, w1, #1",
    ] + GET_SKILL_DB + [
        "cbz x0, 9f", "mov x2, xzr", "bl @%#x" % GETTYPE, "cbz x0, 9f", "mov x21, x0",
        "mov x0, x20", "mov x1, x21", "bl @fm", "cbnz x0, 5f",
        "mov x0, x20", "mov x1, x21", "mov w2, #1", "bl @am", "b 6f",
        "5: mov w8, #1", "stp w8, w8, [x0, #0x18]",
        "6: ldr x0, [x20, #0x48]", "cbz x0, 9f", "mov w1, wzr", "mov x2, xzr", "mov w3, wzr", "bl @%#x" % EVALUATE,
        "9: ldp x21, x22, [sp, #32]", "ldp x19, x20, [sp, #16]", "ldp x29, x30, [sp], #48", "ret",
    ])

    # x0 = target entity, x1 = Kana (caster): one more stack of Kana's Pink Heart Poison on the target.  The poison SkillType is the id after Contrast.
    m.cave("stack", [
        "stp x29, x30, [sp, #-80]!", "mov x29, sp", "stp x19, x20, [sp, #16]", "stp x21, x22, [sp, #32]", "stp x23, x24, [sp, #48]",
        "mov x19, x0", "mov x20, x1",
        "mov x0, x20", "mov w1, #%d" % CONTRAST_MARK, "bl @fs", "cbz x0, 9f",
        "add w1, w1, #1",
    ] + GET_SKILL_DB + [
        "cbz x0, 9f", "mov x2, xzr", "bl @%#x" % GETTYPE, "cbz x0, 9f", "mov x21, x0",
        "mov x0, x20", "mov x1, xzr", "bl @%#x" % GETATK, "lsl w23, w0, #1",
        "mov x0, x19", "mov x1, x21", "bl @fm", "cbnz x0, 5f",
        "mov x0, x19", "mov x1, x21", "mov w2, #-1", "bl @am", "cbz x0, 9f", "mov x22, x0", "str wzr, [x22, #0x24]", "b 6f",
        "5: mov x22, x0",
        "6: str x20, [x22, #0x30]", "str w23, [x22, #0x28]", "ldr s0, [x22, #0x24]", "fmov s1, #1.0", "fadd s0, s0, s1", "str s0, [x22, #0x24]",
        "ldr x0, [x19, #0x48]", "cbz x0, 9f", "mov w1, wzr", "mov x2, xzr", "mov w3, wzr", "bl @%#x" % EVALUATE,
        "9: ldp x23, x24, [sp, #48]", "ldp x21, x22, [sp, #32]", "ldp x19, x20, [sp, #16]", "ldp x29, x30, [sp], #80", "ret",
    ])

    # ---- Queen Bee: x24 = SkillType, x22 = attacker, w23 = slot.  Every living enemy (kind 1) gets a stack; then the game emits the skill as usual.
    m.cave("queen", [
        "ldr w9, [x24, #0x84]", "mov w10, #%d" % QUEEN_MARK, "cmp w9, w10", "b.ne 9f",
        "stp x29, x30, [sp, #-96]!", "mov x29, sp", "stp x19, x20, [sp, #16]", "stp x21, x22, [sp, #32]", "stp x25, x26, [sp, #48]", "stp x27, x28, [sp, #64]",
        "mov x19, x22",
        "ldr x9, [x19, #0x268]", "cbz x9, 8f", "ldr x27, [x9, #0x1e8]", "cbz x27, 8f", "ldr x8, [x27, #0x10]", "cbz x8, 8f",
        "ldr w9, [x8]", "ldr x10, [x8, #0x10]", "mul x25, x9, x10", "mov x20, xzr",
        "1: cmp x20, x25", "b.hs 8f", "add x8, x27, x20, lsl #3", "ldr x22, [x8, #0x20]", "add x20, x20, #1", "cbz x22, 1b",
        "ldr x8, [x22, #0x38]", "cbz x8, 1b", "ldrb w9, [x8, #0x36]", "cbnz w9, 1b", "ldr w9, [x8, #0x2c]", "cmp w9, #1", "b.ne 1b",
        "mov x0, x22", "mov x1, x19", "bl @stack", "b 1b",
        "8: ldp x27, x28, [sp, #64]", "ldp x25, x26, [sp, #48]", "ldp x21, x22, [sp, #32]", "ldp x19, x20, [sp, #16]", "ldp x29, x30, [sp], #96",
        "9: and w8, w23, #0x1f", "b @0x10bea10",
    ])

    # ---- Contrast: Entity.SkillDamage(victim x0, damage w1, SkillType x2, attacker x3).  A magic hit from a monster on Kana becomes 0 and poisons the attacker.
    m.cave("contrast", [
        "stp x29, x30, [sp, #-112]!", "mov x29, sp",
        "stp x0, x1, [sp, #16]", "stp x2, x3, [sp, #32]", "stp x4, x5, [sp, #48]", "str d0, [sp, #64]",
        "stp x19, x20, [sp, #72]", "stp x21, x22, [sp, #88]",
        "cbz x0, 9f", "cbz x2, 9f", "cbz x3, 9f", "cmp w1, #1", "b.lt 9f",
        "mov x19, x0", "mov x20, x3", "mov x21, x2",
        "ldr x8, [x20, #0x38]", "cbz x8, 9f", "ldr w9, [x8, #0x2c]", "cmp w9, #1", "b.ne 9f", "ldrb w9, [x8, #0x36]", "cbnz w9, 9f",
        "mov x0, x19", "mov w1, #%d" % CONTRAST_MARK, "bl @fs", "cbz x0, 9f",
        "mov x0, x21", "bl @%#x" % IS_MAGIC, "tbz w0, #0, 9f",
        "str wzr, [sp, #24]",
        "mov x0, x20", "mov x1, x19", "bl @stack",
        "9: ldp x21, x22, [sp, #88]", "ldp x19, x20, [sp, #72]", "ldr d0, [sp, #64]", "ldp x4, x5, [sp, #48]", "ldp x2, x3, [sp, #32]", "ldp x0, x1, [sp, #16]",
        "ldp x29, x30, [sp], #112",
        "stp d9, d8, [sp, #-0x70]!", "b @0x10917ac",
    ])

    # ---- poison tick heals the caster (PoisonDamage: x20 = modifier, w21 = tick damage, s9 = stack count of the queen poison)
    m.cave("red", [
        "stp x29, x30, [sp, #-48]!", "mov x29, sp", "stp d0, d1, [sp, #16]", "str wzr, [sp, #40]",
        "ldr x8, [x20, #0x40]", "cbz x8, 9f", "ldr w9, [x8, #0x84]", "mov w10, #%d" % BULLET_MARK, "cmp w9, w10", "b.eq 1f",
        "mov w10, #%d" % QUEEN_POISON_MARK, "cmp w9, w10", "b.ne 9f", "mov w10, #1", "str w10, [sp, #40]",
        "1: ldr x0, [x20, #0x30]", "cbz x0, 9f", "ldr x8, [x0, #0x38]", "cbz x8, 9f",
        "ldrb w9, [x8, #0x36]", "cbnz w9, 9f",
        "str x0, [sp, #32]", "ldr x1, [x8, #0x60]", "mov x0, xzr", "mov x2, xzr", "bl @%#x" % HPDEC,
        "cmp w0, #1", "b.lt 9f",
        "mov w1, w21", "ldr w10, [sp, #40]", "cbz w10, 2f",
        "scvtf s0, w21", "fmul s0, s0, s9", "fmov s1, #0.5", "fmul s0, s0, s1", "fcvtns w1, s0", "mov w8, #1", "cmp w1, #1", "csel w1, w1, w8, ge",
        "2: ldr x0, [sp, #32]", "mov w2, wzr", "mov w3, wzr", "bl @%#x" % HEAL,
        "9: ldp d0, d1, [sp, #16]", "mov x0, xzr", "mov x1, xzr", "ldp x29, x30, [sp], #48", "b @%#x" % RANGE_F,
    ])
    # ---- forced poison: w24 = flags of AddModifier, x19 = modifier, x20 = caster context
    m.cave("force", [
        "ldr w8, [x19, #0x10]", "cmp w8, #1", "b.ne 9f",
        "ldr x8, [x19, #0x40]", "cbz x8, 9f", "ldr w9, [x8, #0x84]",
        "mov w10, #%d" % BULLET_MARK, "cmp w9, w10", "b.ne 9f",
        "ldr x9, [x19, #0x30]", "ldr x10, [x20, #0x18]", "cmp x9, x10", "b.eq 9f",
        "orr w24, w24, #1",
        "9: and w8, w24, #1", "ret",
    ])
    # ---- pincer line (successRate 4444): x19 = coroutine, x9 := SkillType; x2 = attacker, x3 = target list
    m.cave("line", [
        "ldr x9, [x19, #0x40]", "cbz x9, 9f", "ldr w10, [x9, #0x78]", "mov w11, #%d" % LINE_MARK, "cmp w10, w11", "b.ne 9f",
        "ldr x10, [x2, #0x38]", "cbz x10, 9f", "ldr w10, [x10, #0x50]",
        "ldr x12, [x3, #0x10]", "cbz x12, 9f", "ldr w13, [x3, #0x18]", "cbz w13, 9f",
        "ldr x12, [x12, #0x20]", "cbz x12, 9f", "ldr x12, [x12, #0x38]", "cbz x12, 9f", "ldr w12, [x12, #0x50]",
        "cmp w10, w12", "b.ne 6f",
        "mov w13, #5", "str w13, [x9, #0x64]", "str wzr, [x9, #0x68]", "b 9f",
        "6: mov w13, #7", "str wzr, [x9, #0x64]", "str w13, [x9, #0x68]",
        "9: b @%#x" % EXEC_SKILL,
    ])
    m.hook(SITE_PUSH, "bl @%#x" % ONHIT, "heart", link=True)
    m.hook(SITE_EMIT, "and w8, w23, #0x1f", "queen")
    m.hook(SITE_DMG, "stp d9, d8, [sp, #-0x70]!", "contrast")
    m.hook(SITE_RED, "bl @%#x" % RANGE_F, "red", link=True)
    m.hook(SITE_FORCE, "and w8, w24, #1", "force", link=True)
    m.hook(SITE_LINE, "bl @%#x" % EXEC_SKILL, "line", link=True)
    return m
