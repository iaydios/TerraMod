# TerraModUpdate: Handoff Guide (English)

Purpose: let another Claude (claude.ai or Claude Code) pick up this work from this file plus the standalone files in `TerraModUpdate/`. Read this file first, then `Kit/BUILD.md`, then `work_log.md` (newest entries at the bottom).

Project: fan-made, non-profit Terra Battle mod. Four Λ characters (Ma'curi 1289, Kana 1290, Gugba 1291, Y'apkar? Λ 1292) plus one combined APK. Each character has an independent native patch of `libil2cpp.so`. Nothing is shared between characters.

## 0. Files you need

| Path | What it is |
|---|---|
| `Kit/BUILD.md` | Build manual, marks table, hook sites, verification list |
| `Kit/builders/make_<name>.py` | Generates `<Name>Update/mods/*.json`. Edit this, never the JSON by hand |
| `Kit/tools/natives/<name>_native.py` | Native code (caves and hooks) per character |
| `Kit/tools/tests/` | Emulator tests: `test_<name>.py`, `gen_live.py`, `check_caves.py`, `test_real_splice.py`, `test_independence.py`, `verify_apk.py` |
| `Kit/base/SkillData.json`, `ChrDatabase.json` | Original game data (0-based index; skill ID = index + 1) |
| `Kit/builders/shipped_extract.json` | Copies of original skill records used as templates |
| `Kit/scripts/run.sh`, `run_combo.sh` | Build one character / one combo APK |
| `<Name>Update/release/` | Split APK parts, `SHA256.txt`, `build.log`, `join_apk.bat` |
| `work_log.md` | Chronological change log with verification notes |
| `TROUBLESHOOTING_EN.md`, `TROUBLESHOOTING_EN_SHORT.md` | Symptom to action list |
| `analysis/methods.tsv` | Game method addresses (name to address table) |

The original `libil2cpp.so` is extracted from `Kit/input/` APK parts. Tests take its path as an argument.

## 1. Current state (2026-10-15)

| Package | SHA256 prefix | Status |
|---|---|---|
| Ma'curi | `f45729df` | Delivered to the user's PC |
| Kana | `19dbe9c4` | Delivered, tested perfect in game |
| Gugba | `602054cf` | Delivered, tested perfect in game |
| Y'apkar? Λ | `e2f88fa0` | Delivered to the PC (replaces `bee20cc6`) |
| Combo (all four) | `74b59775` | Delivered to the PC (replaces `9b7923ad`) |

Y'apkar's Madness and Awakening skills were just changed (see section 3 item 9). Real-game testing of Ma'curi's Mechanical Reflect and Y'apkar's new skills is still pending.

Every native patch is verified only in the emulator with the real game code. Nothing has been verified in the real game unless the table says "tested".

## 2. Hard rules (learned the hard way)

1. One build at a time. Builds share `/root/charwork`. Two parallel builds produce `cp: cannot create directory` errors or wrong output.
2. After editing a builder, rerun the builder, then check `mods/*.json`, then build, then read `out/dump/*.json`. Skipping the rerun once shipped an old value.
3. Use only the game's own things: its effects, skills, values. Do not clone particle effects. Effect IDs must be 1 to 450 (the game's effect pool has 451 slots). A cloned effect id 451 crashed Gugba's tap skill.
4. Every hook cave must return every callee-saved register (x19 to x30, d8 to d15, sp), and every caller-saved register the game reads afterwards. A cave that clobbered x8 in the damage hook crashed every skill.
5. Hidden helper skills must directly follow their visible skill (id+1, id+2, ...). The natives find skills by `SkillType.capacity` marks (+0x84), never by fixed IDs.
6. Skill IDs 3843 to 3852 are reserved by the client. The build pads past them.
7. Never reuse another character's marks, hook sites or state byte. `nativelib.check_modules` refuses overlaps; `test_independence.py` proves it on the real file.
8. Windows delivery: ASCII-only file and folder names, ASCII-only `.bat` content.
9. Deliver to the user's PC only after explicit approval. Other characters' release hashes must stay unchanged in a single-character build.
10. Yapkar job SkillAttrib 7 is intentional. Do not change it.

## 3. Problems met and how each was fixed

1. **Gugba tap skill froze the game.** Cause: a cloned particle effect with id 451. Fix: removed clones, use existing ids 372 and 271 only. Rule: section 2.3.
2. **Gugba tap showed a chain-link icon.** Cause: effect 270 `gathering_02` has a chain texture. Fix: do not use 270.
3. **Enemy DEF cut only about 25% instead of 99%.** Cause: the game's `Entity.limitModifiedStatus` (0x1078E40) caps every enemy-side reduction at 30% of base (float at 0x204F1E4). Fix: hook at 0x1078E68 skips the cap only when the entity has a modifier with mark 4810 (grandma's DEF break). Proven on the real function with `test_limit_real.py`.
4. **Every Gugba skill crashed.** Cause: the damage hook at 0x10917DC overwrote x8, which the game reads two instructions later. Fix: save and restore x8. Proof: `test_real_splice.py` and `gen_live.py`.
5. **A skill's ID looked off by one.** It was a wrong claim. Real rule: skill ID = list index + 1. Dump indices are 0-based. Check `out/dump/SkillData.json` with `id = index + 1`.
6. **Hidden buddy skill values were mixed up.** A buddy skill is found in skill slot 8, emitted with BOOST 100, not with `SkillType.emitRatio`. See `project memory: buddy-skill-mechanics`.
7. **Macuri's buddy regeneration was too strong.** Fix: replaced by Mechanical Reflect. It uses the game's own Counterattack record (template skill 47, icon 5, effect 54, range 3) with power 2.5. A lethal hit leaves Macuri at 1 HP (state byte 0x2B8C000+0xAF3, set on lock, cleared at each SkillAttack start, so the lock holds for all hits of one monster attack). A kill by the counter heals him to full and adds a stacking +25% damage per kill (permanent modifier on hidden skill id+1).
8. **Gugba rhythm skill hit five animations and froze.** Cause: the skill ID was repeated in the emitted list. Fix: never repeat an animated skill to fake extra hits; the game's own multi-hit effect (for example effect 41 earthquake) already hits several times in one animation.
9. **Y'apkar pincer skills only hit the column.** The owner asked for pincer + row + column + X. Fix: hidden skills id+3..id+5 (column), id+6..id+9 (row, using the game's own row records 302, 412, 467, 358, 3076, 3180, 2273, 2263), id+10..id+13 (X). The X skills use range 16. Range 16 is the game's pincer-plus-X routine centred on EACH pincered enemy (BattleManager.IterateList2 at 0xce5230, jump-table case 16 to 0xce44ec). No shipped skill uses it, so it is untested in game. Fallback if the X looks wrong: set `range=10` in `make_yapkar.py` (range 10 is centred on one origin cell only).
10. **Asset version confusion.** Y'apkar's portrait asset uses version 132 in `make_yapkar.py`. If an avatar does not change on screen, a client cache may be the cause. Changing the version needs an APK rebuild and confirmation first.
11. **Delivery failed while the device was disconnected.** The remote device bridge can drop. Retry once after a short wait. If it still fails, tell the user the files were NOT delivered and give the staged path. Never claim delivery that did not succeed.
12. **Release files over the device size limit.** Limits per commit call: 30 MB per file, 100 MB per call. Solution: `split -b 25000000 -d -a 2`, then deliver the parts.

## 4. How to handle the same kind of problem next time

- **Crash on a skill or tap:** find the hook in `Kit/tools/natives/<name>_native.py` (header lists the sites). Check effect ids (1 to 450). Check register preservation with `check_caves.py` (must show `TOTAL violations: 0`). Check `live_regs.json` after running `gen_live.py`. Do not stub the game function in tests; load the real function (`test_real_splice.py`, `test_limit_real.py`).
- **Skill does nothing:** check `mods/*.json` and `out/dump/SkillData.json`. Check that the mark (capacity) is present and unique. Check that hidden helpers directly follow their visible skill.
- **Wrong number or text:** rerun the builder, rebuild, read the dump. Texts live in the builder (`tx(zh, en, ja)`) and in `skills_and_texts.md`.
- **Skill looks wrong in game but works in data:** compare with the closest original skill in `base/SkillData.json` (search `rangePrefixString`, `kind`, `condition`, `effID`). Use the original's ranges and effects before inventing anything.
- **Build error on copy:** two builds ran together. Rebuild one at a time.
- **Verification after any native change, in this order:**
  1. `python3 -I Kit/tools/tests/test_<name>.py <so>` (must print OK)
  2. `python3 -I Kit/tools/tests/gen_live.py <original so>`
  3. `python3 -I Kit/tools/tests/check_caves.py <original so>` (0 violations)
  4. `python3 -I Kit/tools/tests/test_real_splice.py <original so> <patched so>` (0 mismatches)
  5. `python3 -I Kit/tools/tests/test_independence.py <original so>` (15 of 15 OK)
  6. Build, then `verify_apk.py <apk> <dump> <game.apk> <Update folders>` (ALL OK)
  7. Compare the other characters' SHA256 prefixes with section 1. They must not change.

## 5. Adding a new character WITHOUT any AI (step-by-step)

Work in a Windows or Linux shell. The Windows route uses `build.bat` (needs WSL, first run installs packages).

### 5.1 Plan the character
1. Choose the character ID (game chr id), its job ID, and the names.
2. Choose skill marks that are not used. Check: `grep -h "^MARKS\|capacity=" Kit/tools/natives/*.py Kit/builders/*.py` and list the numbers already used. Pick numbers in an unused range. Hidden helper skills use the number plus 1, 2, ...
3. Choose icon slots that nobody uses. See the memory note `terramod-icon-slots` and `TerraModUpdate/Kit/BUILD.md` (Icons paragraph). Used slots: 127 is free now, 128 Ma'curi, 129/130 Kana, 140/141 Gugba. Slots 142 and 143 are free. Do not reuse a used slot.
4. Write the skill texts (English, Japanese, Traditional Chinese). Keep the descriptions short and factual.

### 5.2 Create the folder
1. Copy `YapkarUpdate` (has a native module) or `KanaUpdate` (no native) to `<NewName>Update`. Use ASCII only.
2. Delete the copied `release/`, `out/` and `out_check/` folders inside the new folder. Keep `build.bat`, `join_apk.bat`, `make_gdresources_tar.bat`, `update.json`, `art/`, `gdresources_new/`, `server_buddies.json`, `README.txt`.
3. Copy `Kit/builders/make_yapkar.py` to `Kit/builders/make_<newname>.py` and edit:
   - `character(<chr_id>, <job_id>, [<skill keys in job order>])`. The number of keys must equal the job's skill slot count (assert).
   - Each skill: start from `base(<index>)` (original skill, 0-based index) or `shipped(<id>)`, then change the fields with `S.add(key, record, name, desc, **fields)`. Only fields that exist in the record can be set.
   - Marks: `capacity=<unique mark>`.
   - `mod = {...}` at the bottom: `skills`, `characters`, `asset_db`, `native` (empty list if no native).
   - `write_mod(out, "15_<name>.json", mod, [], {...})`. Use a number that does not collide with the existing `10_`..`15_` files.
4. Run: `cd Kit/builders && python3 make_<newname>.py ../../<NewName>Update`.
5. Check `<NewName>Update/mods/*.json` by eye: skill count, marks, icon numbers, texts.

### 5.3 Native code (only if the skill needs a new behaviour)
1. Copy `Kit/tools/natives/yapkar_native.py` to `<newname>_native.py`. Replace:
   - `REGIONS`: pick never-executed Mono.Security methods. Use `analysis/methods.tsv` and check that the method is never called (other characters use 0xAFC890, 0xB2FB9C, 0x9FD118, 0xAFB99C, 0xB32B60, 0x9FC314, 0xB3398C, and 0xB3398C is Y'apkar's). Choose a region that no module uses.
   - `SITE_*` hook addresses: must be unique (no other module uses them; see the module table in `Kit/BUILD.md`).
   - `MARKS`: the new marks.
   - The state byte, if any, in `flags=[(page, offset)]`. Use an offset no other module uses (Gugba 0x2B8C000+0xAF0, Macuri 0x2B8C000+0xAF3).
2. Write `Kit/tools/tests/test_<newname>.py` modelled on `test_yapkar.py` (emulator with mocked game structures). Test every behaviour, including what happens to other characters (must be no-op).
3. Add the module to `Kit/tools/tests/test_independence.py` and to the table in `Kit/BUILD.md`.
4. Run the verification list in section 4 (all seven steps).

### 5.4 Build
1. One build at a time: `bash Kit/scripts/run.sh <OUT dir> <NewName>Update`. Windows: double-click `<NewName>Update\build.bat`.
2. Read the build log for `re-read verification OK` and the SHA256 lines.
3. Run `verify_apk.py` (expect ALL OK).
4. Check `<OUT>/dump/SkillData.json` for the new skills (`id = index + 1`, marks present).

### 5.5 Release
1. Create `<NewName>Update/release/`.
2. `cd <OUT>` then `split -b 25000000 -d -a 2 TerraBattle-mod.apk <release>/TerraBattle-mod.apk.part` (same for `reTB-Host-mod.apk`).
3. Write `release/SHA256.txt` (`sha256sum TerraBattle-mod.apk reTB-Host-mod.apk`) and copy `build.log`.
4. Check the join: `cat release/TerraBattle-mod.apk.part* | sha256sum` must equal the APK's hash.

### 5.6 Combo
1. Add `<NewName>Update` on its own line in `ComboUpdate/combo.txt`.
2. Run `bash Kit/scripts/run_combo.sh <absolute path to combo.txt> <OUT>` (absolute path is required).
3. `verify_apk.py` with every folder listed. Release split as in 5.5.

### 5.7 Deliver to the user's PC (only after the user approves)
1. Copy each release file to `TB\TerraMod\1013V1\pack_en\TerraModUpdate\<NewName>Update\release\`.
2. Limits per call: 30 MB per file, 100 MB per call.
3. Tell the user: run `join_apk.bat` inside the folder, then compare the SHA256 with `SHA256.txt`.

### 5.8 After the user tests
Record the result in `work_log.md` and in the project memory. If the user reports a problem, use section 4.

## 6. Open items

- Real-game tests pending: Ma'curi Mechanical Reflect (power 2.5), Y'apkar new pincer/row/X skills (X uses range 16), Combo.
- Y'apkar avatar version (see section 3.10) if the portrait does not change.
- Skill text drafts (`skill_text_draft_*.md`) are not yet applied to everything.
- Headbutt reset on wave 2 is unknown (Gugba).
