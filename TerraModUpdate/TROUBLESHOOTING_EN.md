# TerraModUpdate: What To Do When Something Goes Wrong (English)

Companion to `CHANGE_RECORD_2026-10-13_14.md` (Traditional Chinese, full history). This file only covers how to handle problems.
Nothing below has been verified inside the real game yet. Native patches were only checked with an emulator and snippets of the real game code.

Folders (all under `TerraModUpdate/`): `MacuriUpdate`, `KanaUpdate`, `GugbaUpdate`, `YapkarUpdate`, `ComboUpdate`, `Kit`.
Each character has its own independent native patch of `libil2cpp.so`. Build kit docs: `Kit/BUILD.md`. Short log: `work_log.md`.

---

## 1. First checks (before touching any code)

1. Collect: which character, which skill, what action, crash or "no effect", any game log.
2. Make sure the installed APK is the newly joined one, not an old joined `TerraBattle-mod.apk` / `reTB-Host-mod.apk` left in the folder. Re-run `join_apk.bat` in that folder, then install.
3. Compare the APK SHA256 with `release/SHA256.txt`. Current single-package prefixes:
   - Macuri `f45729df`, Kana `19dbe9c4`, Gugba `602054cf`, Yapkar `e2f88fa0`, Combo `74b59775`.
4. Rule out a bad install: if a character with no native change misbehaves too, suspect the install or join step, not the patch.

---

## 2. Symptom -> likely cause -> action

### Crash when a skill or tap is used
- Look at the native cave used by that action: `Kit/tools/natives/<name>_native.py` (hook list at top of file).
- Known causes already found and fixed:
  - **Particle effect id above 450.** The game's effect pool holds 451 slots, valid ids are 1..450. Never play a cloned `particleEffectSet` entry from native code. Use an existing id (current tap effects: 372, 270, 271). `terra_mod.py` refuses a build with a cloned particle id above 450, and `test_gugba.py` asserts ids are in 1..450.
  - **A cave overwrote a register the game still reads** (example: x8 in the Gugba damage hook, which crashed every skill). Every cave must hand back every register and flag the original code reads after the hook.
- Typical other crash sources: fixed-size game arrays, internal field offsets, calls into game functions with wrong arguments.
- Do not stub out the game functions the cave calls. A stubbed effect call hid the pool-limit crash. Load the real function into the emulator instead (examples: `hop_real.py`, `icons_real.py`, `tests/test_real_splice.py`).

### Skill does nothing / wrong effect
- Check the skill data in `<Name>Update/mods/*.json` and the dump `out/dump/ChrDatabase.json` after a build.
- Check that the native mark is present: marks are carried in `SkillType.capacity` (+0x84). A changed `capacity` or `successRate` can break the hook that looks for it.
  - `successRate 4444` is a marker used only by Kana's buddy skill for the "line" hook. Anything else with 4444 is a bug (it once leaked into Gugba's hidden skill; now 100).
- Buddy (follower) skills sit at skill array index 8. Their trigger check uses the buddy BOOST value (we use 100 = always), not `SkillType.emitRatio`.

### Wrong stat, HP, or text in the game
- Gugba max-level HP is 9000 (set in `make_gugba.py` as `jobs[0]["HPmax"]`).
- After editing any builder: rerun the builder, check `mods/*.json`, build, then read `out/dump/ChrDatabase.json`. Skipping the rerun once produced an APK with the old value.

### Red aura / status icon on a marker skill
- Marker-only passive skills must use status 0. Status 53 = red attack-up aura, status 15 = auto-heal aura.

### Missing visual or sound
- Gugba's tap skill no longer plays the extra gravity sound (the cloned effect caused the crash). An existing candidate is effect 350 `final_heavy_01` (not yet seen in game). Add only after confirming the id is in 1..450.

### Build produced garbage or a copy error
- Error like `cp: cannot create directory '/root/charwork/tools'` means two builds ran at once. They share `/root/charwork`. Discard both outputs and rebuild, one at a time.

### Job SkillAttrib 7 on Yapkar
- Intentionally kept. No original job uses attribute 7, but the owner decided not to change it. Do not "fix" it.

---

## 3. After ANY native code change: required checks

Run from `Kit/` against the original `libil2cpp.so`:

1. `test_<name>.py` for the character (gugba, kana, macuri, yapkar), all must print OK.
2. `python3 -I tools/tests/gen_live.py <original so>` to regenerate `live_regs.json` (registers and flags the game reads after each hook site).
3. `python3 -I tools/tests/check_caves.py <original so>`, must end with `TOTAL violations: 0`. It statically proves, on every path, that x19-x30, d8-d15 and sp are restored and sp stays 16-byte aligned.
4. `test_real_splice.py` (real `SkillDamage` code, original vs patched), expect 0 MISMATCH.
5. `test_independence.py` (each module changes only its own bytes), expect all 15 subsets OK.
6. Build, then `verify_apk.py` (expect ALL OK) and apksigner v1/v2/v3 verification.

How to read the output:
- A **hard failure** in `emu.py` means a callee-saved register or a flag the game still reads was changed. Fix the cave.
- `REVIEW` lines mean a caller-saved register differs and liveness could not prove it dead. Check the real disassembly by hand. In the last audit all 24 REVIEW items were harmless (callee ignores the register, callee never returns, or wrong type assumption), but never assume that: look each time.
- The only intended register write is Kana's `force` cave setting bit 0 of w24 (declared via `m.intended_writes`).

---

## 4. Rules for making changes safely

- Reuse what the game already has (effects, skills, values). Do not clone effects or invent values. Every non-original value must have a stated reason.
- Never reuse another character's hook or marker value. Each character has independent natives; modules must not interfere (the independence test enforces this).
- Order for any change: edit builder -> rerun builder -> inspect `mods/*.json` -> build (one build at a time) -> read `out/dump` -> run all checks in section 3 -> split release.
- Release split: `split -b 25000000 -d -a 2`; update `release/SHA256.txt`; confirm the joined file's SHA256 equals the build output.
- Deliver to the user's PC only after their approval. Target folder: `TB\TerraMod\1013V1\pack_en\TerraModUpdate\<Name>Update\release`. Limits per commit call: 30MB per file, 100MB total. The user then runs `join_apk.bat` themselves.
- Use ASCII file names for anything delivered to Windows.
- Record every change (what, why, how verified, what is still unverified) in `work_log.md` and the change record.

---

## 5. Known open items

- Not yet tested in the real game: all four characters (especially the Gugba tap skill).
- Unknown: whether the Gugba rhythm headbutt resets to 1.0 at the start of battle wave 2.
- Skill text drafts (`skill_text_draft_*.md`) are written but not applied.
- ComboUpdate exists only in the project, not on the user's PC.
