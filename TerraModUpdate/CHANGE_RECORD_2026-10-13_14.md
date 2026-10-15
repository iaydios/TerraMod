# TerraModUpdate Change Record: 2026-10-13 Night to 2026-10-14 (Gugba (格古巴) Crash, All-Character Check, Hook-Site Audit)

Purpose: If Sam runs into a problem later, read this first. It records what happened, why, how it was changed, how it was verified, and what is not yet verified.
A shorter running log is in `work_log.md`; the build method is in `Kit/BUILD.md`; skill content is in `skills_and_texts.md`.
Language: Sam uses Traditional Chinese; file names are always in English (Windows extraction issue, see `NAMES_zh_to_en.txt`).

---

## 0. At a glance (current status)

| Character | Single-pack SHA256 (TerraBattle-mod.apk, prefix) | Changed in this round? | Copied to Sam's PC release folder |
|---|---|---|---|
| Macuri (瑪庫里) MacuriUpdate | 90c90130 | No change (audit found no issue) | Yes (re-copied 2026-10-14) |
| Kana (卡奈) KanaUpdate | 19dbe9c4 | Queen bee (女王蜂) effect 480 → original 205 | Yes |
| Gugba GugbaUpdate | 9afd6245 | See below; most changes | Yes |
| Yapkar (亞普卡) YapkarUpdate | 095bb423 | No change (Sam said job attribute 7 should not be touched) | Yes (re-copied once) |
| Combo package (合併包) ComboUpdate | 79b94fd4 | Rebuilt along with the above | Not copied; only in the project |

**All native code is still verified only with emulator / real-game code snippets; it has not been run in the actual game.** Sam's in-game test is the only final verification.
Sam must re-run `join_apk.bat` in each folder before installing; some folders still contain old already-merged APKs, which must not be used.

---

## 1. Timeline: what happened

### 1.1 Gugba (格古巴) "every skill crashes" (earlier on 2026-10-13, fixed, delivered)
- Cause: The Gugba "took damage" hook (Entity.SkillDamage, 0x10917DC) cave corrupted **x8**, and the game reads x8 two instructions later. Any damage ≥1 crashed the game.
- Reproduced with real game code (the game's SkillDamage placed unchanged in the emulator, with the patched cave attached). The fix: the cave saves x8 first and restores it.
- Lesson recorded in memory `feedback-hook-registers`: a cave must return, unchanged, every register the game still reads after the hook point.

### 1.2 Buddy (小跟班) skill red glow (fixed)
- A passive skill used only as a marker should not have status 53 (red ATK-boost aura); changed to status 0. Status 15 = auto-regen aura.
- Sam was actually describing a "skill error," not "glowing." I first misunderstood; after his correction I audited the buddy skills themselves (see 1.3).

### 1.3 Buddy skill audit (no issue found)
- Checked how the game attaches buddy skills: Status.EvaluateBuddy places it in skill array slot 9 (index 8); EmitCheck for slot 8 uses the buddy's BOOST (ours is 100 = always triggers) instead of SkillType.emitRatio. See memory `buddy-skill-mechanics` for details.
- Tested with the real SkillDamage plus all marker skills; the registers of the three characters matched the original.
- Conclusion: neither the data nor the native code had a defect. At the time Sam's specific symptom was unclear; later he identified it as Gugba's tap-skill crash (1.4).

### 1.4 Gugba "Grandma's Will (奶奶的意志)" crashes on press (main cause this time, fixed)
- Symptom (Sam): "Gugba's skill crashes when pressed" → "Grandma's Will (奶奶的意志)."
- Initially I simulated EmitHopBreak and ShowHopBreakIcons with real game code. Registers, stack, and callee-saved registers were clean, **so the crash did not reproduce**. The reason: during simulation I replaced the "play effect" call with a stub, which hid the real cause.
- **Real cause** (found by reading the real libil2cpp.so):
  - On tap, the `tapfx` cave plays 3 effects. The third was a particleEffectSet entry I created myself by copying with `se_clone` (gather effect 271 + gravity sound), with ID **451**.
  - The game's EffectManager instance pool `[mgr+0x70]` is a fixed-length array: `mov w1,#0x1c3` (0x10D7DF0) = **451 slots**. Function 0x10D80A8 checks "length > ID"; 451 fails, it throws IndexOutOfRange, and the game crashes.
  - The original particleEffectSet has only 450 entries, so valid IDs are 1–450.
- Fix: stop copying effects. `tapfx` now plays the game's existing 372 (flash), 270 (gather ring), and 271 (gather light). The copied gravity sound is gone (the only difference in appearance).
  - `Kit/builders/make_gugba.py`: removed the `"effects"` entry.
  - `Kit/tools/natives/gugba_native.py`: `FX_HOP_GATHER = 271`; the comment states that the pool only has 1..450.
  - `Kit/tools/terra_mod.py`: any copied particle ID > 450 passed to native code is rejected at build time.
  - `Kit/tools/tests/test_gugba.py`: asserts that all fx IDs are in 1..450.
- There is no evidence that the tap in the old version (slot 4 version) ever worked in the game, so this path was never verified in the real game.

### 1.5 Sam's request: "Re-check all characters; use the original wherever one exists"
Completed a full data audit of all characters (2026-10-14): compared every value of all mod skills, jobs, and character info for the four characters against the original database.
- The only values that differ from the original (each with a reason, already explained to Sam):
  - Icon slots 127–130, 140, 141: Sam's own icons, replacing 8 unused game slots.
  - `capacity` markers (used by native code to find skills).
  - Kana buddy skill successRate 4444 (marker used by Kana's "straight-line pincer" (直線夾擊) hook).
  - Kana hidden skill "Love Powder Poison" (愛心粉毒) life −1 (permanent modifier).
  - Yapkar job SkillAttrib 7 (skill attribute 7 exists, but no original job uses it; Sam decided **not to change** it).
- Changed:
  1. **Kana's queen bee** effect `@fx_queen` (my synthesized effectSet entry 480 = heart tracking (愛心追蹤) + poison) → original **205** (heart tracking, same as the charm bullet). Removed `effects` from `make_kana.py`. EffectSet count is back to the original 479 / 450.
  2. **Gugba's "Destruction Strike" (毀滅一擊)** (hidden skill) successRate 4444 → **100**. Reason: 4444 is Kana's `line` hook marker; in the combo package, Kana's code overwrites the sx/sy of Gugba's skill.
  3. **Gugba max-level HP** HPmax 10287 → **9000** (Sam first said 8000, then changed it to 9000). `make_gugba.py` sets `HPmax = 9000` for that job; the job hash is recalculated automatically by the build.
  4. Deleted the temporary folder `TestGugbaNoNative` that I had left behind.
- Not changed: Macuri, Yapkar (audit found no issues).

### 1.6 Sam's request: "Check the hook points carefully" = registers / flags at hook sites
Sam asked me to check thoroughly the registers around all hook sites. Four things were done:

**(a) `gen_live.py` rewrite** (produces `Kit/tools/tests/live_regs.json`)
- The old version only looked 60 lines ahead, stopped at unconditional jumps, did not follow branch targets, and did not track flags. It could therefore miss registers the game reads later.
- New version: runs a backward liveness analysis over the whole hooked function (function range from `Kit/analysis/methods.tsv`); follows both branch targets; tracks NZCV flags; for argument registers read by `bl`, infers the argument count from the called function (column 4 of methods.tsv); treats the exception-throwing helpers (0xBEF9E8, 0xBEF8CC, 0xBF06F4) as never returning; `ret` / tail calls require all callee-saved registers; `br` (jump table) means all registers are live; correctly handles the multi-instruction hook site (only Gugba's 2-instruction one at 0x108EE64); registers written by the replaced instruction itself are not required to remain unchanged.
- Fixed a miss caused by capstone naming x29/x30 as fp/lr.

**(b) Stronger emulator checks** (`Kit/tools/tests/emu.py`)
- Before each check, x0–x28 and d0–d31 are filled with sentinel values; NZCV is set to fixed values.
- If callee-saved registers (x19–x30, d8–d15) are changed and the game still reads them → **immediate failure**.
- If a flag is changed while the game still reads it → failure.
- If other caller-saved registers are changed by the cave and the analysis cannot prove they are dead → print a `REVIEW` line (needs manual confirmation).
- Each module test shows "ran on N of N hook caves." All four modules currently have 100% coverage (Gugba 12/12, Kana 6/6, Macuri 4/4, Yapkar 2/2).

**(c) Manual review of all REVIEW items (24 register items in total)**
Checked each one line by line against the real game disassembly. All are false positives from an overly conservative checker; none is a real problem. Typical reasons:
- Followed only by exception-throwing helpers (they never return, so the arguments do not matter).
- The called function does not actually use that register (e.g., `bl 0xBFD180` only uses x0; `0x1ECE404` reads x0, x1, x8; ResetAroundBonus's x1 is overwritten by the caller).
- The function returns Vector2 / bool, not the x0 the checker assumed.
- The floating-point parameter v1 is not a parameter at all in SkillDamage.

**(d) New `check_caves.py`: static proof**
- For every cave in each module, traces every path (not only the paths the tests happen to reach): on exit, whether x19–x30 and d8–d15 are restored to their entry values, whether sp returns to its original position, and whether sp is 16-byte aligned.
- Allowed differences: registers the game no longer reads after the hook, and registers written by the replaced instruction itself.
- The only intentional exception: Kana's `force` cave sets bit0 of w24 to 1 (the AddModifier flag). This is declared in `kana_native.py` via `m.intended_writes`.
- Validated by deliberately breaking `tapfx` (removing the restore of x19) and confirming that it is caught. Current result: `TOTAL violations: 0`.

**(e) Other static audits**
- Flags at all hook sites: **none of the hook sites has a flag that is read later**.
- The only 2-instruction replacement (Gugba 0x108EE64 `cmp w8,#1; b.eq`): no branch anywhere in the game code jumps into its second instruction.
- Cave regions (seven "never-executed Mono.Security methods"): each region's entry is referenced only once, by the method pointer table. Direct callers are all inside Mono.Security; tracing upward reaches only `X509Certificate.CreateFromSignedFile` and `X509Certificate2.Import/ImportPkcs12`, which have no direct callers of their own (they are reachable only via virtual calls / reflection). The game does not call certificate import.
- The Entity+0x32c "times hit" field that Gugba uses is a field the game itself increments in SkillDamage (not something we created).

---

## 2. Mistakes I made (honest record)
1. Misread "the buddy skill was not changed" as a glow issue (corrected by Sam).
2. While simulating the tap flow, I replaced the effect-playing call with a stub, which hid the effect-pool limit. **Lesson: tests should not stub out the real callee; read the real function.**
3. Running two build.sh at the same time overwrote `/root/charwork` (error `cp: cannot create directory '/root/charwork/tools'`). Those outputs were discarded, and builds were switched to sequential. **Run only one build at a time.**
4. I changed `make_gugba.py` (HPmax 9000) but packed without re-running the builder first, so the first build still had 8000. I found it by dumping ChrDatabase and rebuilt. **Lesson: after changing a builder, re-run `python3 make_x.py ../../XUpdate`, check `mods/*.json`, then build, and finally read `out/dump/ChrDatabase.json` to confirm the values.**
5. I had prepared to change Yapkar's SkillAttrib before Sam told me not to set it to 0. After he stopped me, I confirmed that neither the builder nor the mods file had been changed (still 7).

---

## 3. Verification and results (final round, 2026-10-14)
All against the final artifacts (Gugba G9, Kana K8, Combo C9):
- `verify_apk.py`: the `libil2cpp.so` inside the APK = original + exactly those mods; marks and hidden-skill positions exist → ALL OK.
- Signature: apksigner v1 / v2 / v3 verification passed.
- `test_real_splice.py`: the real SkillDamage code placed in the emulator; original and patched versions compared record by record (including "all markers are present on both victim and attacker") → 0 MISMATCH.
- `test_independence.py`: 15 seed combinations; each module modifies only its own bytes → ALL 15 SUBSETS OK.
- Unit tests for the four modules: GUGBA OK / KANA OK / MACURI OK / YAPKAR OK.
- `check_caves.py`: 0 violations.
- Database dump confirmed: EffectSet 479 / 450, Gugba HPmax 9000, no effID > 479, successRate 4444 only on Kana's buddy skill.
- Release slices (25,000,000 bytes each) concatenated back: SHA256 matches the build output. On Sam's PC, file names and sizes were compared file by file; all four folders match.

**Not done, therefore not verified:** running in the real game; running join_apk.bat on Windows; the SHA256 of the merged file on Sam's PC (the Linux environment on the PC side was not running, so it could not be computed there).

---

## 4. File map (what was changed)
- `Kit/builders/make_gugba.py`: removed the effects entry; HPmax 9000; Destruction Strike successRate=100.
- `Kit/builders/make_kana.py`: queen bee effID=205; removed the effects entry.
- `Kit/tools/natives/gugba_native.py`: FX_HOP_GATHER=271 (replaces `{FX_fx_tap_gather}`).
- `Kit/tools/natives/kana_native.py`: added `m.intended_writes = {"force": ["x24"]}` (behavior unchanged).
- `Kit/tools/terra_mod.py`: copied particle IDs > 450 → build rejected.
- `Kit/tools/tests/`: `gen_live.py` (rewritten), `emu.py` (strengthened), `check_caves.py` (new), `live_regs.json` (regenerated), `test_gugba.py` (fx ID assertion), `test_real_splice.py` (includes the all-markers-on scenario).
- `Kit/BUILD.md`: added item 4, "hook safety," to the verification steps; added the effect-pool limit warning.
- Each `*Update/mods/*.json` and `release/`: regenerated / re-sliced.
- Memory (project-shared): `feedback-effect-pool-limit`, `feedback-original-first`, `buddy-skill-mechanics`, `feedback-hook-registers`.

---

## 5. How to investigate future problems (procedure)
1. Ask Sam: which character, which skill, what action was taken, crash or no effect, and whether there is a game log.
2. First confirm he installed the newly merged APK (SHA256 prefix in section 0), not an old merged file.
3. Crash → find the native cave used by that action (the header of `Kit/tools/natives/<name>_native.py` lists the hook sites).
   - First check whether it plays effects, uses fixed-size arrays, or uses game-internal field offsets.
   - Use `Kit/analysis/methods.tsv` to map addresses to methods; use `capstone` to disassemble the original libil2cpp.so rebuilt from `Kit/input`.
   - **Do not stub out called game functions.** Write a small test that loads the real function into unicorn (examples: `hop_real.py`, `icons_real.py`, `tests/test_real_splice.py`).
4. After any change to native code, always run: `test_<name>.py`, `gen_live.py <original so>`, `check_caves.py <original so>`, `test_real_splice.py`, `test_independence.py`; then build and run `verify_apk.py`.
5. Change a builder → re-run the builder → check the mods JSON → run only one build at a time → read `out/dump` to verify values → re-slice (`split -b 25000000 -d -a 2`) → update `release/SHA256.txt` → report to Sam and wait for his consent before copying to his PC (path `TB\TerraMod\1013V1\pack_en\TerraModUpdate\<name>Update\release`; single commit ≤100MB, single file ≤30MB).

## 6. Rules (from Sam)
- Reply in Traditional Chinese; file names in English; ask him before making any decision; get his consent before copying to his PC (copy only when he says to).
- Use the game's original items where they exist; do not create copies on your own; do not be perfunctory or take shortcuts; every change needs a record and verification.
- The project has no GitHub repository; all files are kept in `/mnt/project-files/TerraModUpdate`.

## 7. Open items
- Sam to test all four characters in-game (especially Gugba's tap, "Grandma's Will") and report back.
- Gugba's tap no longer includes the copied gravity sound. If Sam wants the sound, the existing 350 "final_heavy_01" (sound gravity_final, larger visual, not yet viewed in practice) could be played instead. Needs Sam's decision.
- Whether the Rhythm Headbutt (節奏頭槌) "one battle" counter restarts from 1.0 in wave two: not verified in-game.
- Skill description text drafts (`skill_text_draft_*.md`) are not yet applied; needs Sam's confirmation.
- Yapkar job SkillAttrib 7 stays as is (Sam's decision).

---
## 8. Addendum 2026-10-14 (after Sam's in-game test of Gugba): tap skill fixes
See work_log.md "night 7". Summary: (a) removed particle 270 (chain-link icon) from the tap animation; (b) enemy DEF -100% was capped to about -30% by the game's Entity.limitModifiedStatus (cap constant 0.3 at 0x204F1E4); new hook 0x1078E68 skips the cap for entities carrying the DEF-break modifier (mark 4810) and the modifier is now -99%; (c) new real-code test `Kit/tools/tests/test_limit_real.py`. Gugba APK 602054cf, Combo 1c53acd7; other three characters unchanged. Not yet on Sam's PC.
Debug tip: if DEF still looks capped, check the hook at 0x1078E68 is present (verify_apk) and the skill with mark 4810 has spower -99 in out/dump/SkillData.json.
