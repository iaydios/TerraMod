"""Native module for Ma'curi Lambda (chr 1289).  Self-contained: own regions, own hook sites, own helper copies.

Marks (SkillType.capacity):
  5101 Mechanical Reflect (buddy)  the game's own Counterattack (kind 2, condition 4, template skill 47) with power 2.5: when the owner is pincered it counters every pincering enemy with 2.5 x ATK
                          non-elemental physical damage (the game runs the counter itself, right after the monster's attack).  HP lock: damage that would kill the owner leaves 1 HP, and the lock holds for every hit of the same monster attack; the next attack (SkillAttack start releases the lock) kills a owner left at 1 HP.
                          Every kill made by that counter heals the owner to full and adds one to a kill counter (permanent modifier of the hidden skill id+1);
                          all damage the owner deals is then x (1 + 0.25 x kills) for the rest of the battle, no cap.
  5110 Spear Tomb               visible pincer/chain attack (power 1.0).  When it is among the emitted skill ids it is emitted two more times (3 hits).
  5120 Coercion (equip)         damage dealt to an enemy below COERCION_PERCENT of its max HP is x COERCION_MULT (the Ten Thousand Spears skill, mark 5130, excluded).
  5130 Ten Thousand Spears      plain 10000 damage pincer attack, only carries the mark.
  5140 Thirst for Blood (character skill 1) every time the owner deals damage it heals HEAL_ATK_FACTOR x its ATK.
Hook sites (all unique to this module):
  0x10917CC  Entity.SkillDamage: adrp x8,...   (x0 victim, w1 damage, x2 SkillType, x3 attacker)   -> HP lock, reflect kill (counter + full heal), life steal
  0xCC3EF8   <SkillAttack>c__Iterator7.MoveNext: adrp x8,...  (x19 coroutine, [x19+0x18] = List<int> of emitted skill ids) -> Spear Tomb x3
  0xF0CE10   SkillEvaluator._damageAction: fmul s9,s10,s9  (x19 attacker, x20 target, x21 SkillType) -> Coercion + reflect kill bonus
"""
from nativelib import (Module, find_skill, find_mod, add_mod, get_skill_type, GET_SKILL_DB, GETTYPE, GETHP, GETATK, HEAL, LIST_ADD, f32bits, movf)

HPDEC = 0xCA6FB4
M_REFLECT, M_TOMB, M_COERCION, M_SPEARS, M_THIRST = 5101, 5110, 5120, 5130, 5140
KILL_BONUS = 0.25                    # +25 % damage per reflect kill, stacking without limit
TOMB_EXTRA = 2                       # emitted 2 more times -> 3 hits
COERCION_PERCENT = 33                # target HP strictly below 33 % of max HP
COERCION_MULT = 1.5
HEAL_ATK_FACTOR = 0.5

REGIONS = [(0xAFC890, 2800), (0xB2FB9C, 2744)]      # AuthenticodeDeformatter.VerifyCounterSignature, PKCS12.ReadSafeBag (never executed)
MARKS = {M_REFLECT, M_TOMB, M_COERCION, M_SPEARS, M_THIRST}
FLAG_PAGE, FLAG_OFF = 0x2B8C000, 0xAF3        # init-flag byte of never-executed Mono.Security code (Gugba uses +0xAF0): "lock held during this attack"
SITE_DMG, SITE_DMG_BACK = 0x10917CC, 0x10917D0
SITE_SAH, SITE_SAH_BACK = 0xCC3EF8, 0xCC3EFC
SITE_POW, SITE_POW_BACK = 0xF0CE10, 0xF0CE14


def build(ctx):
    m = Module("macuri", REGIONS, flags=[(FLAG_PAGE, FLAG_OFF)])
    m.marks = MARKS
    m.cave("fs", find_skill())
    m.cave("fm", find_mod())
    m.cave("am", add_mod(1))
    m.cave("gst", get_skill_type())
    # s0 = value of the permanent modifier made from hidden skill w1 on entity x0 (0 if none)
    m.cave("wval", [
        "stp x29, x30, [sp, #-32]!", "mov x29, sp", "str x19, [sp, #16]", "mov x19, x0",
        "bl @gst", "cbz x0, 8f", "mov x1, x0", "mov x0, x19", "bl @fm", "cbz x0, 8f", "ldr s0, [x0, #0x24]", "b 9f",
        "8: movi d0, #0",
        "9: ldr x19, [sp, #16]", "ldp x29, x30, [sp], #32", "ret",
    ])

    # Entity.SkillDamage entry.  Free registers: x19..x28 (the game's prologue already saved them); x0..x4 and s0 are arguments.
    m.cave("dmg", [
        "stp x29, x30, [sp, #-112]!", "mov x29, sp",
        "stp x0, x1, [sp, #16]", "stp x2, x3, [sp, #32]", "stp x4, x5, [sp, #48]", "str d0, [sp, #64]",
        "mov x19, x0", "mov w20, w1", "mov x21, x3",
        "cbz x19, 9f", "cmp w20, #1", "b.lt 9f",
        # ---- Mechanical Reflect, HP lock: damage that would kill the owner leaves it at 1 HP; at 1 HP already the damage goes through (the owner dies on the next hit) (current HP = HPDEC(data+0x60), as in the Coercion cave)
        "mov x0, x19", "mov w1, #%d" % M_REFLECT, "bl @fs", "cbz x0, 3f",
        "ldr x8, [x19, #0x38]", "cbz x8, 3f", "ldr x1, [x8, #0x60]", "mov x0, xzr", "mov x2, xzr", "bl @%#x" % HPDEC,
        "cmp w0, #1", "b.le 2f", "sub w9, w0, #1", "cmp w20, w9", "b.lt 3f",
        "mov w20, w9", "str w20, [sp, #24]", "adrp x9, @%#x" % FLAG_PAGE, "mov w10, #1", "strb w10, [x9, #%#x]" % FLAG_OFF, "b 3f",
        "2: adrp x9, @%#x" % FLAG_PAGE, "ldrb w10, [x9, #%#x]" % FLAG_OFF, "cbz w10, 3f",
        "mov w20, wzr", "str w20, [sp, #24]", "b 9f",
        # ---- Mechanical Reflect, kill: the damage comes from the counter skill (mark 5101) and is lethal -> kill counter (hidden id+1) += 1 and the attacker is healed to full
        "3: cmp w20, #1", "b.lt 9f", "ldr x22, [sp, #32]", "cbz x22, 5f", "ldr w8, [x22, #0x84]", "mov w9, #%d" % M_REFLECT, "cmp w8, w9", "b.ne 5f", "cbz x21, 5f",
        "ldr x8, [x19, #0x38]", "cbz x8, 5f", "ldr x1, [x8, #0x60]", "mov x0, xzr", "mov x2, xzr", "bl @%#x" % HPDEC, "cmp w20, w0", "b.lt 5f",
        "mov x0, x21", "mov w1, #%d" % M_REFLECT, "bl @fs", "cbz x0, 5f",
        "add w1, w1, #1", "bl @gst", "cbz x0, 5f", "mov x22, x0",
        "mov x0, x21", "mov x1, x22", "bl @fm", "cbnz x0, 4f",
        "mov x0, x21", "mov x1, x22", "mov w2, #-1", "bl @am", "cbz x0, 5f", "str wzr, [x0, #0x24]",
        "4: ldr s0, [x0, #0x24]", "fmov s1, #1.0", "fadd s0, s0, s1", "str s0, [x0, #0x24]",
        "mov x0, x21", "mov x1, xzr", "bl @%#x" % GETHP, "fcvtzs w1, s0", "cmp w1, #1", "b.lt 5f",
        "mov x0, x21", "mov w2, wzr", "mov w3, wzr", "bl @%#x" % HEAL,
        # ---- Thirst for Blood: the attacker heals HEAL_ATK_FACTOR x ATK for every damaging hit
        "5: cmp w20, #1", "b.lt 9f", "cbz x21, 9f", "cmp x21, x19", "b.eq 9f",
        "ldr x8, [x21, #0x38]", "cbz x8, 9f", "ldrb w9, [x8, #0x36]", "cbnz w9, 9f",
        "mov x0, x21", "mov w1, #%d" % M_THIRST, "bl @fs", "cbz x0, 9f",
        "mov x0, x21", "mov x1, xzr", "bl @%#x" % GETATK,
        "scvtf s0, w0",
    ] + movf("w8", "s1", HEAL_ATK_FACTOR) + [
        "fmul s0, s0, s1", "fcvtzs w1, s0", "mov w8, #1", "cmp w1, #1", "csel w1, w1, w8, ge",
        "mov x0, x21", "mov w2, wzr", "mov w3, wzr", "bl @%#x" % HEAL,
        "9: ldr d0, [sp, #64]", "ldp x4, x5, [sp, #48]", "ldp x2, x3, [sp, #32]", "ldp x0, x1, [sp, #16]", "ldp x29, x30, [sp], #112",
        "adrp x8, @0x2aae000", "b @%#x" % SITE_DMG_BACK,
    ])

    # SkillAttack coroutine: every Spear Tomb in the emitted-id list is emitted TOMB_EXTRA more times (only the original entries are scanned)
    m.cave("sah", [
        "stp x29, x30, [sp, #-96]!", "mov x29, sp",
        "stp x19, x20, [sp, #16]", "stp x21, x22, [sp, #32]", "stp x23, x24, [sp, #48]", "stp x25, x26, [sp, #64]",
        "adrp x9, @%#x" % FLAG_PAGE, "strb wzr, [x9, #%#x]" % FLAG_OFF,         # a new attack starts: the HP lock is released
        "ldr x20, [x19, #0x18]", "cbz x20, 9f",
        "ldr w21, [x20, #0x18]", "mov w22, wzr",
        "1: cmp w22, w21", "b.ge 9f",
        "ldr x8, [x20, #0x10]", "cbz x8, 9f", "ldr w9, [x8, #0x18]", "cmp w22, w9", "b.hs 9f",
        "add x8, x8, x22, lsl #2", "ldr w23, [x8, #0x20]", "add w22, w22, #1",
        "cbz w23, 1b",
    ] + GET_SKILL_DB + [
        "cbz x0, 9f", "mov w1, w23", "mov x2, xzr", "bl @%#x" % GETTYPE, "cbz x0, 1b",
        "ldr w9, [x0, #0x84]", "mov w10, #%d" % M_TOMB, "cmp w9, w10", "b.ne 1b",
        "mov w24, #%d" % TOMB_EXTRA,
        "3: mov x0, x20", "mov w1, w23",
        "adrp x2, @0x2ad5000", "ldr x2, [x2, #0x848]", "ldr x2, [x2]", "bl @%#x" % LIST_ADD,
        "subs w24, w24, #1", "b.ne 3b", "b 1b",
        "9: ldp x25, x26, [sp, #64]", "ldp x23, x24, [sp, #48]", "ldp x21, x22, [sp, #32]", "ldp x19, x20, [sp, #16]", "ldp x29, x30, [sp], #96",
        "adrp x8, @0x2ac1000", "b @%#x" % SITE_SAH_BACK,
    ])

    # SkillEvaluator._damageAction power: x19 attacker, x20 target, x21 SkillType.  The surrounding code re-loads x0..x4, so only x30 and the
    # callee-saved registers matter.
    m.cave("pow", [
        "fmul s9, s10, s9",
        "stp x29, x30, [sp, #-32]!", "mov x29, sp",
        "cbz x19, 9f", "cbz x20, 9f", "cbz x21, 9f",
        "ldr w8, [x21, #0x84]", "mov w9, #%d" % M_SPEARS, "cmp w8, w9", "b.eq 8f",
        "mov x0, x19", "mov w1, #%d" % M_COERCION, "bl @fs", "cbz x0, 8f",
        "ldr x8, [x20, #0x38]", "cbz x8, 8f", "ldrb w9, [x8, #0x36]", "cbnz w9, 8f",
        "ldr x1, [x8, #0x60]", "mov x0, xzr", "mov x2, xzr", "bl @%#x" % HPDEC, "str w0, [sp, #16]",
        "mov x0, x20", "mov x1, xzr", "bl @%#x" % GETHP, "fcvtzs w9, s0",
        "ldr w8, [sp, #16]", "mov w10, #100", "smull x8, w8, w10", "mov w10, #%d" % COERCION_PERCENT, "smull x9, w9, w10", "cmp x8, x9", "b.ge 8f",
    ] + movf("w8", "s1", COERCION_MULT) + [
        "fmul s9, s9, s1",
        # Mechanical Reflect: every damage hit of the owner is x (1 + KILL_BONUS x kills made by the counter)
        "8: mov x0, x19", "mov w1, #%d" % M_REFLECT, "bl @fs", "cbz x0, 9f",
        "add w1, w1, #1", "mov x0, x19", "bl @wval",
    ] + movf("w8", "s1", KILL_BONUS) + [
        "fmul s0, s0, s1", "fmov s1, #1.0", "fadd s0, s0, s1", "fmul s9, s9, s0",
        "9: ldp x29, x30, [sp], #32",
        "b @%#x" % SITE_POW_BACK,
    ])
    m.hook(SITE_DMG, "adrp x8, @0x2aae000", "dmg")
    m.hook(SITE_SAH, "adrp x8, @0x2ac1000", "sah")
    m.hook(SITE_POW, "fmul s9, s10, s9", "pow")
    return m
