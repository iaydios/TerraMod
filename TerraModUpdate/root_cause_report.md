# All Skills Crash on Use: Root Cause and Test Report (2026-10-13)

## One sentence
The Gugba (格古巴) "took damage" hook that was **newly added** this time (0x10917DC in the game function Entity.SkillDamage) corrupted register x8, which the game uses next. Whenever anyone takes 1 or more damage (any skill hitting anyone), the game reads address 0 and crashes immediately. The old version (the one you said worked) did not have this hook, so it was fine.

## How it was found (all measured, not guessed)
1. Compared, byte by byte, the libil2cpp.so of the "old APK that worked (SHA 2c8989df…)" and the "current APK," and listed every changed location.
   - New hooks (not in the old version): Gugba 0xCC3DF4, 0x10917DC; Macuri (馬卡利) 0xCD9AC0, 0x10917CC, 0xCC3EF8; Yapkar (亞普卡) 0xCD9AC4, 0xCC3EEC.
   - New storage locations in the program: Gugba 0x9FD118, Kana (卡奈) 0xB32B60, Yapkar 0xB3398C.
2. For each new hook, disassembled the original game code after that location to find the "registers the game still reads next."
   - Original game code at 0x10917DC:
     - 0x10917D8  ldr x8, [x8, #0x640]        ← x8 is set here
     - 0x10917DC  adrp x28, ...                 ← my hook is placed here
     - 0x10917E8  ldr w24, [x8]                 ← x8 is used only after this
   - My hook program (gdmg) saved only x0–x5, d0, x19–x22. It did not save x8, and it first reads the "hit count" using w8, so x8 was overwritten with values such as 0.
3. Reproduced using **the real game code**: loaded the patched libil2cpp.so into the emulator and ran from the start of Entity.SkillDamage (tests/test_real_splice.py).
   - The version you have installed now (SHA 1c79fb39…): when damage is 1, it reads address 0 at 0x10917E8 → crash (x8 = 0). When damage is 0, there is no crash. This also explains why not every action failed.
   - Fixed version: for damage 0, 1, and 50, the resulting registers exactly match the original game.
   - The damage hooks of the three characters Gugba, Kana, and Macuri, chained together (combined four-in-one build), also match.
4. Why my earlier tests missed it: the tests only checked whether "my program computes correctly." They did not check whether "the registers the game itself still needs were returned unchanged."

## New checks added (similar errors will now be blocked directly)
- tests/gen_live.py: computes, from **the original game**, the registers the game still uses after each hook (saved as live_regs.json).
- Each time the emulator runs a hook program, it checks that these registers are returned unchanged. The 24 hook programs across the four characters are all covered. Intentional changes (damage value w1, AddModifier flag w24) are listed as exceptions.
- Removing the fix and running again: the test immediately reports "0x10917dc changed register x8 that the game still uses," which proves the check works.
- tests/test_real_splice.py: runs the damage function with real game code and compares it before and after patching.

## Other check results
- Hooks of the other three characters: register checks all passed (Kana 6, Macuri 4, Yapkar 2).
- Storage locations: all seven regions (Gugba 2, Kana 2, Macuri 2, Yapkar 1) were checked one by one. From outside each region there is only one direct call each, from neighboring Mono.Security certificate functions that also never run. There are no calls from the game itself.
- Four characters not overlapping (15 combinations) passed. APK verification (Gugba alone, and the four-in-one build) passed.

## New builds
- Gugba-only APK: SHA256 f4507c3ca2055b89ec00678c908770e18e8c7195fe7fc305a66233c9638bbb59
- Four-in-one APK: SHA256 00372cc37cd798fd98e8fbd7ceca6526555e0e9d87c06f4ccf6e2680a1e725fa

## Things that still cannot be guaranteed
- I can only run the real game code in the emulator; I cannot run the entire game for you. What has been proven: this crash was found, reproduced, and fixed. Whether there are other problems requires your in-game testing.
- Whether the second wave of Rhythm Headbutt (節奏頭槌) restarts from 1.0 still needs in-game confirmation.
