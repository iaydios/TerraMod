"""Native module for Gugba Lambda (chr 1291).  Self-contained: own regions, own hook sites, own helper copies, own state byte.

Marks (SkillType.capacity):
  4801 Out of My Way  carrier may enter cells of non-boss monsters (drag-push).  Nothing else (Sam 2026-10-13: the effect is only pushing enemy blocks).
  4802 Whiskey        pincer, base 30 % (+ Skill Boost).  Each drink adds +25 % to one of ATK / DEF / SATK / SDEF (hidden skills id+1..id+4 = permanent
                      modifiers whose value is 25 x cups).  A stat holds 4 cups; a full stat is skipped, 16 cups in all, then drinking does nothing.
                      Taking any damage sets the four modifiers back to 0 (the cup count restarts).
  4806 Grandma's Will (buddy, tap skill, once per battle).  Tapping Gugba arms the next pincer and gives every living enemy a 1-turn DEF -99 % modifier
                      (hidden id+5, mark 4810; hook 0x1078E68 lifts the game's 30 % reduction cap for entities carrying it).  The armed pincer is turned into the fist (hidden id+1, mark 4805, pincer line): the first victim is
                      hit with a multiplier = number of times Gugba was hit this battle (capped at 20, at least 1), the cells behind it with
                      max(1, min(that, 7 - distance)); the first non-boss victim is dropped to 1 HP first, Gugba falls to 1 HP.  Hidden id+2 (4807) is the
                      "already used" marker, id+3 (4808) the stun every non-boss victim keeps, id+4 (4809) = the line "Enough..." (name of the skill) said once
                      when Gugba has been hit 20 times.
  4830 Rhythm Headbutt (pincer or chain, 30 %).  Plain physical hit of 1.0 x ATK; every use adds +1.0 x ATK for the rest of the battle (no cap), the next battle
                      starts again at 1.0.  Counter = the value of the hidden inert skill id+1 as a permanent modifier on Gugba (added when the skill is put into
                      the emitted list, read by the _damageAction hook as the damage factor).
Hook sites (all unique to this module):
  0x108E050 canMoveTo(1)  0x108EE64 CanMoveTo(2)  0x102816C InitEquipSkills  0xCD30E4 swap  0x10917DC Entity.SkillDamage  0xCB5150 PreSkillEffect
  0xCC0514 Evaluate epilogue  0x1086050 EmitHopBreak  0x1080B68 ShowHopBreakIcons  0x10BE774 EmitMultiSkill(tap)  0xCC3DD4 GetSkill  0xCC3DF4 List.Add
  0xF0CC1C _damageAction attenuation  0x1078E68 Entity.limitModifiedStatus
"""
from nativelib import (Module, find_skill, find_range, find_mod, add_mod, get_skill_type, fx_play, GET_SKILL_DB, GETTYPE, ISBOSS, GETATK, SETHP, EVALUATE,
                       RANDOM_RANGE_I, LIST_ADD, f32bits, movf)

PUSH_MARK, WHISKEY_MARK = 4801, 4802
FIST_MARK, TAP_MARK, USED_MARK, STUN_MARK, ENOUGH_MARK, DEBUFF_MARK = 4805, 4806, 4807, 4808, 4809, 4810
HEAD_MARK = 4830
CUP, MAX_CUPS = 25.0, 4                # +25 % per drink, 4 per stat
HITS_CAP = 20
FALLOFF = 7
EMITCORRECT, GETSKILL, ISROOT = 0x1079DC4, 0x10BE200, 0x10821AC
GETATT, SCREENSHAKE, STARTCO = 0xF0B054, 0xCE6828, 0x1FA3A7C
GETNAME, SHOWMSG = 0x1023F24, 0x1093C48
SHAKE_AMOUNT = 1.5
FX_HOP_RING, FX_HOP_FLASH, FX_SHOCK, FX_HOP_GATHER = 270, 372, 424, 271     # particleEffectSet ids; the game's pool holds ids 1..450 only (EffectManager array of 451), never add one
FLAG_PAGE, FLAG_OFF = 0x2B8C000, 0xAF0        # CheckSignature init-flag byte of never-executed Mono.Security code: "whiskey drunk" flag
SITE_CM1, SITE_CM2, SITE_EQUIP = 0x108E050, 0x108EE64, 0x102816C
SITE_DMG, SITE_PRE, SITE_END = 0x10917DC, 0xCB5150, 0xCC0514
SITE_HOP, SITE_ICONS, SITE_TAPEMIT, SITE_PICK, SITE_ADD, SITE_FIST, SITE_LIMIT = 0x1086050, 0x1080B68, 0x10BE774, 0xCC3DD4, 0xCC3DF4, 0xF0CC1C, 0x1078E68

REGIONS = [(0x9FD118, 8268), (0xAFB99C, 3420)]      # PKCS12.GetBytes (generic instance), AuthenticodeDeformatter.VerifySignature (never executed)
MARKS = {PUSH_MARK, WHISKEY_MARK, FIST_MARK, TAP_MARK, USED_MARK, STUN_MARK, ENOUGH_MARK, DEBUFF_MARK, HEAD_MARK}


def build(ctx):
    m = Module("gugba", REGIONS, flags=[(FLAG_PAGE, FLAG_OFF)])
    m.marks = MARKS
    m.cave("fs", find_skill())
    m.cave("fr", find_range())
    m.cave("fm", find_mod())
    m.cave("am", add_mod(1))
    m.cave("gst", get_skill_type())
    m.cave("fx", fx_play())

    # ================================================================ Out of My Way
    m.cave("cm1", [
        "cbz x20, 6f", "ldr x8, [x20, #0x38]", "cbz x8, 5f", "ldr w9, [x8, #0x2c]", "cmp w9, #1", "b.ne 5f",
        "mov x0, x19", "mov w1, #%d" % PUSH_MARK, "bl @fs", "cbz x0, 5f",
        "mov x0, x20", "mov x1, xzr", "bl @%#x" % ISBOSS, "tbnz w0, #0, 5f",
        "mov w0, #1", "b @0x108e0c4",
        "5: cbz x20, 6f", "b @0x108e058", "6: b @0x108e054",
    ])
    m.cave("cm2", [
        "cmp w8, #1", "b.ne 5f",
        "mov x0, x19", "mov w1, #%d" % PUSH_MARK, "bl @fs", "cbz x0, 4f",
        "mov x0, x22", "mov x1, xzr", "bl @%#x" % ISBOSS, "tbnz w0, #0, 4f",
        "b @0x108eea4",
        "4: b @0x108f130",
        "5: b @0x108ee6c",
    ])
    m.cave("equip", [
        "ldr w8, [x24, #0x84]", "mov w10, #4800", "sub w9, w8, w10", "cmp w9, #19", "b.ls 1f",
        "ldr w8, [x24, #0x58]", "b @0x1028170",
        "1: b @0x10280ec",
    ])
    # ================================================================ Whiskey
    # s0 = current value of the whiskey modifier of stat w1 (0 if none).  x0 = entity, w1 = hidden skill id
    m.cave("wval", [
        "stp x29, x30, [sp, #-32]!", "mov x29, sp", "str x19, [sp, #16]", "mov x19, x0",
        "bl @gst", "cbz x0, 8f", "mov x1, x0", "mov x0, x19", "bl @fm", "cbz x0, 8f", "ldr s0, [x0, #0x24]", "b 9f",
        "8: movi d0, #0",
        "9: ldr x19, [sp, #16]", "ldp x29, x30, [sp], #32", "ret",
    ])
    # x0 = entity: all four whiskey modifiers := 0 (the cup count restarts), then re-evaluate.  x1 = whiskey skill id
    m.cave("wreset", [
        "stp x29, x30, [sp, #-64]!", "mov x29, sp", "stp x19, x20, [sp, #16]", "stp x21, x22, [sp, #32]",
        "mov x19, x0", "mov w20, w1", "mov w21, wzr",
        "1: add w1, w20, w21", "add w1, w1, #1", "bl @gst", "cbz x0, 2f", "mov x1, x0", "mov x0, x19", "bl @fm", "cbz x0, 2f", "str wzr, [x0, #0x24]",
        "2: mov x0, x19", "add w21, w21, #1", "cmp w21, #4", "b.lt 1b",
        "ldr x0, [x19, #0x48]", "cbz x0, 9f", "mov w1, wzr", "mov x2, xzr", "mov w3, wzr", "bl @%#x" % EVALUATE,
        "9: ldp x21, x22, [sp, #32]", "ldp x19, x20, [sp, #16]", "ldp x29, x30, [sp], #64", "ret",
    ])
    # x0 = Gugba, w1 = whiskey skill id: one drink = +CUP % on a random stat that still has room (full stats are skipped)
    m.cave("drink", [
        "stp x29, x30, [sp, #-80]!", "mov x29, sp", "stp x19, x20, [sp, #16]", "stp x21, x22, [sp, #32]", "stp x23, x24, [sp, #48]",
        "mov x19, x0", "mov w20, w1", "mov w22, wzr", "mov w23, wzr",
        "1: mov x0, x19", "add w1, w20, w23", "add w1, w1, #1", "bl @wval",
    ] + movf("w8", "s1", CUP * MAX_CUPS - CUP / 2) + [
        "fcmp s0, s1", "b.ge 2f", "add w22, w22, #1",
        "2: add w23, w23, #1", "cmp w23, #4", "b.lt 1b",
        "cbz w22, 9f",
        "mov x0, xzr", "mov w1, wzr", "mov w2, w22", "mov x3, xzr", "bl @%#x" % RANDOM_RANGE_I, "mov w24, w0",
        "mov w23, wzr",
        "3: mov x0, x19", "add w1, w20, w23", "add w1, w1, #1", "bl @wval",
    ] + movf("w8", "s1", CUP * MAX_CUPS - CUP / 2) + [
        "fcmp s0, s1", "b.ge 4f", "cbz w24, 5f", "sub w24, w24, #1",
        "4: add w23, w23, #1", "cmp w23, #4", "b.lt 3b", "b 9f",
        "5: add w1, w20, w23", "add w1, w1, #1", "bl @gst", "cbz x0, 9f", "mov x21, x0",
        "mov x0, x19", "mov x1, x21", "bl @fm", "cbnz x0, 6f",
        "mov x0, x19", "mov x1, x21", "mov w2, #-1", "bl @am", "cbz x0, 9f", "str wzr, [x0, #0x24]",
        "6: ldr s0, [x0, #0x24]",
    ] + movf("w8", "s1", CUP) + [
        "fadd s0, s0, s1", "str s0, [x0, #0x24]",
        "ldr x0, [x19, #0x48]", "cbz x0, 9f", "mov w1, wzr", "mov x2, xzr", "mov w3, wzr", "bl @%#x" % EVALUATE,
        "9: ldp x23, x24, [sp, #48]", "ldp x21, x22, [sp, #32]", "ldp x19, x20, [sp, #16]", "ldp x29, x30, [sp], #80", "ret",
    ])
    # x0 = BattleManager: finds Gugba (first living entity with the whiskey mark) on the Entity[,] grid at bm+0x1e8 and gives him a drink
    m.cave("whiskey", [
        "stp x29, x30, [sp, #-64]!", "mov x29, sp", "stp x19, x20, [sp, #16]", "stp x21, x22, [sp, #32]", "stp x23, x24, [sp, #48]",
        "mov x19, x0",
        "ldr x22, [x19, #0x1e8]", "cbz x22, 9f",
        "ldr x8, [x22, #0x10]", "cbz x8, 9f",
        "ldr x9, [x8]", "ldr x23, [x8, #0x10]", "cbz x23, 9f", "mul x24, x9, x23",
        "mov x20, xzr",
        "1: cmp x20, x24", "b.hs 9f",
        "add x8, x22, x20, lsl #3", "ldr x21, [x8, #0x20]", "add x20, x20, #1",
        "cbz x21, 1b",
        "ldr x8, [x21, #0x38]", "cbz x8, 1b", "ldrb w9, [x8, #0x36]", "cbnz w9, 1b",
        "mov x0, x21", "mov w1, #%d" % WHISKEY_MARK, "mov w2, wzr", "bl @fr", "cbz x0, 1b",
        "mov x0, x21", "bl @drink",
        "9: ldp x23, x24, [sp, #48]", "ldp x21, x22, [sp, #32]", "ldp x19, x20, [sp, #16]", "ldp x29, x30, [sp], #64", "ret",
    ])
    # PreSkillEffect(evaluator x0, attacker x1, ...): whiskey roll (emitRatio + Skill Boost) for an attacking Gugba -> flag byte
    m.cave("hpre", [
        "stp x29, x30, [sp, #-64]!", "mov x29, sp", "stp x0, x1, [sp, #16]", "stp x2, x3, [sp, #32]",
        "cbz x1, 9f",
        "mov x0, x1", "mov w1, #%d" % WHISKEY_MARK, "mov w2, wzr", "bl @fr", "cbz x0, 9f",
        "str x0, [sp, #48]", "ldr x0, [sp, #24]", "mov x1, xzr", "bl @%#x" % EMITCORRECT,
        "ldr x8, [sp, #48]", "ldr w9, [x8, #0x6c]", "add w9, w9, w0", "str w9, [sp, #56]",
        "mov x0, xzr", "mov w1, wzr", "mov w2, #100", "mov x3, xzr", "bl @%#x" % RANDOM_RANGE_I,
        "ldr w9, [sp, #56]", "cmp w0, w9", "b.ge 9f",
        "adrp x9, @%#x" % FLAG_PAGE, "mov w10, #1", "strb w10, [x9, #%#x]" % FLAG_OFF,
        "9: ldp x2, x3, [sp, #32]", "ldp x0, x1, [sp, #16]", "ldp x29, x30, [sp], #64",
        "stp d9, d8, [sp, #-0x60]!", "b @%#x" % (SITE_PRE + 4),
    ])
    # epilogue of <Evaluate>c__Iterator19.MoveNext (x19 = iterator, [x19+0x88] = BattleEvaluator, [+0x28] = BattleManager): drink when the roll succeeded
    m.cave("hend", [
        "stp x29, x30, [sp, #-48]!", "mov x29, sp", "stp x20, x21, [sp, #16]",
        "ldr x20, [x19, #0x88]", "cbz x20, 9f", "ldr x20, [x20, #0x28]", "cbz x20, 9f",
        "adrp x9, @%#x" % FLAG_PAGE, "ldrb w10, [x9, #%#x]" % FLAG_OFF, "cbz w10, 9f",
        "strb wzr, [x9, #%#x]" % FLAG_OFF, "mov x0, x20", "bl @whiskey",
        "9: ldp x20, x21, [sp, #16]", "ldp x29, x30, [sp], #48",
        "ldr x20, [x19, #0x88]", "b @%#x" % (SITE_END + 4),
    ])

    # ================================================================ damage taken (SkillDamage entry): victim x0, damage w1
    m.cave("gdmg", [
        "stp x29, x30, [sp, #-112]!", "mov x29, sp",
        "stp x0, x1, [sp, #16]", "stp x2, x3, [sp, #32]", "stp x4, x5, [sp, #48]", "str d0, [sp, #64]",
        "stp x19, x20, [sp, #72]", "stp x21, x22, [sp, #88]", "str x8, [sp, #104]",
        "mov x19, x0", "cbz x19, 9f", "cmp w1, #1", "b.lt 9f",
        # whiskey: any damage empties the cups
        "mov x0, x19", "mov w1, #%d" % WHISKEY_MARK, "bl @fs", "cbz x0, 1f", "mov x0, x19", "bl @wreset",
        # 20th hit: say the line once
        "1: ldr w8, [x19, #0x32c]", "cmp w8, #%d" % (HITS_CAP - 1), "b.ne 9f",
        "mov x0, x19", "mov w1, #%d" % TAP_MARK, "bl @fs", "cbz x0, 9f",
        "add w1, w1, #4", "bl @gst", "cbz x0, 9f", "mov x21, x0",
        "mov x0, x19", "mov x1, x21", "bl @fm", "cbnz x0, 9f",
        "mov x0, x19", "mov x1, x21", "mov w2, #-1", "bl @am",
        "mov x0, x21", "bl @%#x" % GETNAME, "cbz x0, 9f", "mov x1, x0", "mov x0, x19", "mov w2, wzr", "bl @%#x" % SHOWMSG,
        "cbz x0, 9f", "mov x1, x0", "mov x0, x19", "mov x2, xzr", "bl @%#x" % STARTCO,
        "9: ldr x8, [sp, #104]", "ldp x21, x22, [sp, #88]", "ldp x19, x20, [sp, #72]", "ldr d0, [sp, #64]", "ldp x4, x5, [sp, #48]", "ldp x2, x3, [sp, #32]", "ldp x0, x1, [sp, #16]",
        "ldp x29, x30, [sp], #112",
        "adrp x28, @0x2a94000", "b @%#x" % (SITE_DMG + 4),
    ])

    # ================================================================ Rhythm Headbutt: use counter (replaces `bl List<int>.Add` in the SkillAttack list builder)
    # x19 on entry = the <SkillAttack> iterator (its +0x10 is the attacking Entity).  Every time the headbutt is put into the emitted list, the permanent
    # modifier of the hidden inert skill id+1 on the attacker grows by 1.0 (created at 0 when missing)
    m.cave("gadd", [
        "stp x29, x30, [sp, #-96]!", "mov x29, sp", "stp x19, x20, [sp, #16]", "stp x21, x22, [sp, #32]", "stp x23, x24, [sp, #48]", "stp x25, x26, [sp, #64]",
        "mov x25, x19", "mov x19, x0", "mov w20, w1", "mov x21, x2",
        "bl @%#x" % LIST_ADD,
        "cbz x19, 9f", "cbz w20, 9f", "cbz x25, 9f",
    ] + GET_SKILL_DB + [
        "cbz x0, 9f", "mov w1, w20", "mov x2, xzr", "bl @%#x" % GETTYPE, "cbz x0, 9f",
        "ldr w9, [x0, #0x84]", "mov w10, #%d" % HEAD_MARK, "cmp w9, w10", "b.ne 9f",
        "ldr x22, [x25, #0x10]", "cbz x22, 9f",
        "add w1, w20, #1", "bl @gst", "cbz x0, 9f", "mov x23, x0",
        "mov x0, x22", "mov x1, x23", "bl @fm", "cbnz x0, 6f",
        "mov x0, x22", "mov x1, x23", "mov w2, #-1", "bl @am", "cbz x0, 9f", "str wzr, [x0, #0x24]",
        "6: ldr s0, [x0, #0x24]", "fmov s1, #1.0", "fadd s0, s0, s1", "str s0, [x0, #0x24]",
        "9: ldp x25, x26, [sp, #64]", "ldp x23, x24, [sp, #48]", "ldp x21, x22, [sp, #32]", "ldp x19, x20, [sp, #16]", "ldp x29, x30, [sp], #96", "ret",
    ])

    # ================================================================ Grandma's Will
    # x0 = Gugba: every living enemy (kind 1) gets the 1-turn DEF -99 % modifier (tap id + 5).  x1 = tap skill id
    m.cave("debuff", [
        "stp x29, x30, [sp, #-96]!", "mov x29, sp", "stp x19, x20, [sp, #16]", "stp x21, x22, [sp, #32]", "stp x23, x24, [sp, #48]", "stp x25, x26, [sp, #64]",
        "mov x19, x0", "add w1, w1, #5", "bl @gst", "cbz x0, 9f", "mov x21, x0",
        "ldr x9, [x19, #0x268]", "cbz x9, 9f", "ldr x25, [x9, #0x1e8]", "cbz x25, 9f", "ldr x8, [x25, #0x10]", "cbz x8, 9f",
        "ldr w9, [x8]", "ldr x10, [x8, #0x10]", "mul x26, x9, x10", "mov x20, xzr",
        "1: cmp x20, x26", "b.hs 9f", "add x8, x25, x20, lsl #3", "ldr x22, [x8, #0x20]", "add x20, x20, #1", "cbz x22, 1b",
        "ldr x8, [x22, #0x38]", "cbz x8, 1b", "ldrb w9, [x8, #0x36]", "cbnz w9, 1b", "ldr w9, [x8, #0x2c]", "cmp w9, #1", "b.ne 1b",
        "mov x0, x22", "mov x1, x21", "bl @fm", "cbnz x0, 5f",
        "mov x0, x22", "mov x1, x21", "mov w2, #1", "bl @am", "b 1b",
        "5: mov w8, #1", "stp w8, w8, [x0, #0x18]", "b 1b",
        "9: ldp x25, x26, [sp, #64]", "ldp x23, x24, [sp, #48]", "ldp x21, x22, [sp, #32]", "ldp x19, x20, [sp, #16]", "ldp x29, x30, [sp], #96", "ret",
    ])
    # Entity.limitModifiedStatus(this, modified, base, limit) caps every enemy-side reduction at base x 0.3 (float at 0x204f1e4), which made DEF -100 % only about -25 %.
    # x21 = entity at 0x1078e68: an entity carrying a modifier of the DEF-break skill (mark 4810) skips the cap, nobody else is touched
    m.cave("hdef", [
        "ldr x8, [x21, #0x48]", "cbz x8, 5f", "ldr x8, [x8, #0x10]", "cbz x8, 5f",
        "ldr w9, [x8, #0x18]", "ldr x8, [x8, #0x10]", "cbz x8, 5f", "ldr w10, [x8, #0x18]", "cmp w9, w10", "csel w9, w9, w10, lo",
        "add x8, x8, #0x20", "mov w10, wzr",
        "1: cmp w10, w9", "b.hs 5f", "ldr x11, [x8, x10, lsl #3]", "add w10, w10, #1", "cbz x11, 1b",
        "ldr x12, [x11, #0x40]", "cbz x12, 1b", "ldr w12, [x12, #0x84]", "mov w13, #%d" % DEBUFF_MARK, "cmp w12, w13", "b.ne 1b",
        "b @0x1078eac",
        "5: ldr x23, [x21, #0x38]", "b @0x1078e6c",
    ])
    # x0 = entity: one-shot cyan flash + the gather (concentration) effect on the tapped piece only (270 gathering_02 is the chain-link icon: removed, Sam 2026-10-14)
    m.cave("tapfx", [
        "stp x29, x30, [sp, #-32]!", "mov x29, sp", "str x19, [sp, #16]", "mov x19, x0",
        "mov x0, x19", "mov w1, #%d" % FX_HOP_FLASH, "bl @fx",
        "mov x0, x19", "mov w1, #%d" % FX_HOP_GATHER, "bl @fx",
        "ldr x19, [sp, #16]", "ldp x29, x30, [sp], #32", "ret",
    ])
    # EmitHopBreak (x19 = entity): tapping a piece that owns the tap skill arms it, once per battle
    m.cave("hop", [
        "stp x29, x30, [sp, #-64]!", "mov x29, sp", "stp x19, x20, [sp, #16]", "stp x21, x22, [sp, #32]", "str x23, [sp, #48]",
        "mov x0, x19", "mov w1, #%d" % TAP_MARK, "bl @fs", "cbz x0, 9f", "mov x21, x0", "mov w23, w1",
        "mov x0, x19", "mov x1, x21", "bl @fm", "cbnz x0, 8f",
        "add w1, w23, #2", "mov x0, x19", "bl @gst", "cbz x0, 8f", "mov x1, x0", "mov x0, x19", "bl @fm", "cbnz x0, 8f",     # already used this battle
        "mov x0, x19", "mov x1, x21", "mov w2, #1", "bl @am",
        "mov x0, x19", "mov w1, w23", "bl @debuff",
        "mov x0, x19", "bl @tapfx",
        "8: ldr x23, [sp, #48]", "ldp x21, x22, [sp, #32]", "ldp x19, x20, [sp, #16]", "ldp x29, x30, [sp], #64", "b @0x1086828",
        "9: ldr x23, [sp, #48]", "ldp x21, x22, [sp, #32]", "ldp x19, x20, [sp, #16]", "ldp x29, x30, [sp], #64",
        "ldr x21, [x19, #0x268]", "b @%#x" % (SITE_HOP + 4),
    ])
    # ShowHopBreakIcons (x19 = entity, x20 = the icon array): the owner of the tap skill keeps only the glow
    m.cave("icons", [
        "stp x29, x30, [sp, #-32]!", "mov x29, sp", "stp x19, x20, [sp, #16]", "cbz x20, 9f",
        "mov x0, x19", "mov w1, #%d" % TAP_MARK, "bl @fs", "cbz x0, 9f",
        "stp xzr, xzr, [x20, #0x20]", "stp xzr, xzr, [x20, #0x30]", "stp xzr, xzr, [x20, #0x40]", "stp xzr, xzr, [x20, #0x50]",
        "9: ldp x19, x20, [sp, #16]", "ldp x29, x30, [sp], #32", "adrp x8, @0x2ad8000", "b @%#x" % (SITE_ICONS + 4),
    ])
    # EmitMultiSkill, before IsEmittable (x24 = SkillType, x22 = attacker, w23 = slot): the tap skill is emitted without a roll when its owner is the attack
    # root, was tapped (armed modifier present) and has not been used yet
    m.cave("tapemit", [
        "ldr w8, [x24, #0x84]", "mov w9, #%d" % TAP_MARK, "cmp w8, w9", "b.ne 1f",
        "stp x29, x30, [sp, #-32]!", "mov x29, sp", "str x19, [sp, #16]", "str xzr, [sp, #24]",
        "mov x0, x22", "mov x1, xzr", "bl @%#x" % ISROOT, "tbz w0, #0, 6f",
        "mov x0, x22", "mov x1, x24", "bl @fm", "cbz x0, 6f",
        "mov x0, x22", "mov w1, #%d" % TAP_MARK, "bl @fs", "cbz x0, 6f", "add w1, w1, #2", "bl @gst", "cbz x0, 6f",
        "mov x1, x0", "mov x0, x22", "bl @fm", "cbnz x0, 6f",
        "mov x8, #1", "str x8, [sp, #24]",
        "6: ldr x8, [sp, #24]", "ldr x19, [sp, #16]", "ldp x29, x30, [sp], #32",
        "cbz x8, 5f", "and w8, w23, #0x1f", "b @0x10bea10",
        "5: b @0x10be6c4",
        "1: mov x1, xzr", "mov x0, x24", "bl @0x1024a58", "b @0x10be780",
    ])
    # SkillAttack list builder: `bl ChrBaseParams.GetSkill(slot)` returns the skill id; for the tap skill the id+1 attack skill is run instead
    m.cave("pick", [
        "stp x29, x30, [sp, #-48]!", "mov x29, sp", "stp x19, x20, [sp, #16]",
        "bl @%#x" % GETSKILL, "mov w20, w0",
    ] + GET_SKILL_DB + [
        "cbz x0, 9f", "mov w1, w20", "mov x2, xzr", "bl @%#x" % GETTYPE, "cbz x0, 9f",
        "ldr w9, [x0, #0x84]", "mov w10, #%d" % TAP_MARK, "cmp w9, w10", "b.ne 9f", "add w20, w20, #1",
        "9: mov w0, w20", "ldp x19, x20, [sp, #16]", "ldp x29, x30, [sp], #48", "ret",
    ])
    # _damageAction attenuation (x19 attacker, x20 victim, x21 SkillType, x25 evaluator): factor of the fist = hits taken (nearest) / max(1, min(hits, 7 - distance))
    hits = ["ldr w10, [x19, #0x32c]", "cmp w10, #1", "mov w11, #1", "csel w10, w10, w11, ge", "cmp w10, #%d" % HITS_CAP, "mov w11, #%d" % HITS_CAP, "csel w10, w10, w11, le"]
    m.cave("fist", [
        "cbz x21, 8f", "ldr w8, [x21, #0x84]", "mov w9, #%d" % HEAD_MARK, "cmp w8, w9", "b.eq 10f",
        "mov w9, #%d" % FIST_MARK, "cmp w8, w9", "b.ne 8f",
        "cbz x19, 8f", "cbz x20, 8f",
        "ldr x8, [x19, #0x38]", "cbz x8, 8f", "ldr x9, [x20, #0x38]", "cbz x9, 8f",
        "ldr w10, [x8, #0x4c]", "ldr w11, [x9, #0x4c]", "subs w10, w10, w11", "cneg w10, w10, mi",
        "ldr w12, [x8, #0x50]", "ldr w13, [x9, #0x50]", "subs w12, w12, w13", "cneg w12, w12, mi",
        "add w10, w10, w12",
        # (a) the used marker on the attacker (once per battle) and the all-out cost: Gugba falls to 1 HP
        "sub sp, sp, #32", "stp x29, x30, [sp, #16]", "str x22, [sp, #8]", "str w10, [sp]",
        "mov x0, x19", "mov w1, #%d" % TAP_MARK, "bl @fs", "cbz x0, 4f",
        "add w1, w1, #2", "bl @gst", "cbz x0, 4f", "mov x22, x0",
        "mov x0, x19", "mov x1, x22", "bl @fm", "cbnz x0, 4f",
        "mov x0, x19", "mov x1, x22", "mov w2, #-1", "bl @am", "cbz x0, 4f", "fmov s1, #1.0", "str s1, [x0, #0x24]",
        "mov x0, x19", "mov w1, #1", "bl @%#x" % SETHP,
        "4: ldr w10, [sp]", "ldr x22, [sp, #8]", "ldp x29, x30, [sp, #16]", "add sp, sp, #32",
        # (b) every non-boss victim keeps the stun (tap id + 3)
        "sub sp, sp, #32", "stp x29, x30, [sp, #16]", "str w10, [sp]", "str x22, [sp, #8]",
        "mov x0, x20", "bl @%#x" % ISBOSS, "tbnz w0, #0, 7f",
        "mov x0, x19", "mov w1, #%d" % TAP_MARK, "bl @fs", "cbz x0, 7f", "add w1, w1, #3", "bl @gst", "cbz x0, 7f", "mov x22, x0",
        "mov x0, x20", "mov x1, x22", "bl @fm", "cbnz x0, 7f",
        "mov x0, x20", "mov x1, x22", "mov w2, #-1", "bl @am",
        "7: ldr w10, [sp]", "ldr x22, [sp, #8]", "ldp x29, x30, [sp, #16]", "add sp, sp, #32",
        "cmp w10, #1", "b.ne 3f",
        # (c) nearest victim: screen shake, a non-boss drops to 1 HP, shockwave, factor = hits
        "ldr x0, [x25, #0x20]", "cbz x0, 2f",
        "sub sp, sp, #16", "str x0, [sp, #8]",
    ] + movf("w9", "s0", SHAKE_AMOUNT) + [
        "mov x1, xzr", "bl @%#x" % SCREENSHAKE,
        "mov x1, x0", "ldr x0, [sp, #8]", "mov x2, xzr", "bl @%#x" % STARTCO,
        "add sp, sp, #16",
        "2: sub sp, sp, #32", "stp x29, x30, [sp, #16]",
        "mov x0, x20", "bl @%#x" % ISBOSS, "tbnz w0, #0, 6f",
        "mov x0, x20", "mov w1, #1", "bl @%#x" % SETHP,
        "6: mov x0, x20", "mov w1, #%d" % FX_SHOCK, "bl @fx",
        "ldp x29, x30, [sp, #16]", "add sp, sp, #32",
    ] + hits + [
        "b 5f",
        # (d) cells behind: max(1, min(hits, 7 - distance))
        "3: mov w14, w10", "mov w11, #%d" % FALLOFF, "sub w14, w11, w14",
    ] + ["ldr w10, [x19, #0x32c]", "cmp w10, #1", "mov w11, #1", "csel w10, w10, w11, ge", "cmp w10, #%d" % HITS_CAP, "mov w11, #%d" % HITS_CAP, "csel w10, w10, w11, le",
         "cmp w14, w10", "csel w10, w14, w10, lt", "mov w12, #1", "cmp w10, #1", "csel w10, w10, w12, gt",
         "5: scvtf s0, w10", "b @0xf0cc20",
         # Rhythm Headbutt: factor = the use counter (at least 1.0)
         "10: cbz x19, 8f",
         "sub sp, sp, #32", "stp x29, x30, [sp, #16]",
         "mov x0, x19", "mov w1, #%d" % HEAD_MARK, "bl @fs", "cbz x0, 11f",
         "add w1, w1, #1", "mov x0, x19", "bl @wval", "b 12f",
         "11: movi d0, #0",
         "12: ldp x29, x30, [sp, #16]", "add sp, sp, #32",
         "fmov s1, #1.0", "fcmp s0, s1", "fcsel s0, s0, s1, ge", "b @0xf0cc20",
         "8: bl @%#x" % GETATT, "b @0xf0cc20"])

    m.hook(SITE_CM1, "cbnz x20, @0x108e058", "cm1")
    m.site(SITE_CM2, "cmp w8, #1; b.eq @0x108f130", ["b @cm2", "nop"])
    m.hook(SITE_EQUIP, "ldr w8, [x24, #0x58]", "equip")
    m.hook(SITE_DMG, "adrp x28, @0x2a94000", "gdmg")
    m.hook(SITE_PRE, "stp d9, d8, [sp, #-0x60]!", "hpre")
    m.hook(SITE_END, "ldr x20, [x19, #0x88]", "hend")
    m.hook(SITE_HOP, "ldr x21, [x19, #0x268]", "hop")
    m.hook(SITE_ICONS, "adrp x8, @0x2ad8000", "icons")
    m.hook(SITE_TAPEMIT, "mov x1, xzr", "tapemit")
    m.hook(SITE_PICK, "bl @%#x" % GETSKILL, "pick", link=True)
    m.hook(SITE_ADD, "bl @%#x" % LIST_ADD, "gadd", link=True)
    m.hook(SITE_FIST, "bl @%#x" % GETATT, "fist")
    m.hook(SITE_LIMIT, "ldr x23, [x21, #0x38]", "hdef")
    return m
