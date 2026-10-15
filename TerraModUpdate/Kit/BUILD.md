# TerraModUpdate Kit: build manual (EN; the folder README files are zh-TW / EN / FR)

## Layout
```
TerraModUpdate/
  Kit/            shared tools: tools/ (terra_mod.py, host_mod.py, nativelib.py, natives/*.py, tests/), base/ (original DB json), input/ (original APK parts + SHA256.txt),
                  scripts/ (build.sh, run.sh, run_combo.sh, setup.sh, combine.py, make_folder_files.py), builders/ (the scripts that generated every mods/*.json),
                  templates/ (image-bin templates), analysis/ (method address table etc.)
  MacuriUpdate/ KanaUpdate/ GugbaUpdate/ YapkarUpdate/    one folder per character: mods/*.json, art/, gdresources_new/, update.json, server_buddies.json,
                  build.bat, join_apk.bat, make_gdresources_tar.bat, README.txt, release/ (prebuilt split APKs)
  ComboUpdate/    combo.txt (list of Update folder names) + build.bat -> ONE APK with every listed character
  _archive_old/    everything of the old (shared-hook) design, kept for reference only, with where_things_went.md
  work_log.md     work log
```
Keep the TerraModUpdate folder in one piece: the per-character bat files call `..\Kit\scripts`.

## Building
- One character: double-click `<Name>Update\build.bat` (WSL needed; the first run installs packages). Result in `<Name>Update\out\`.
- Several characters in one APK: edit `ComboUpdate\combo.txt` (one folder name per line, any subset, any order), double-click `ComboUpdate\build.bat`.
- By hand (Linux): `bash Kit/scripts/build.sh <out dir> MacuriUpdate KanaUpdate ...`
- build.sh: joins and SHA-checks the original APKs, copies tools/base, merges every selected folder's mods/*.json (+art/), runs `terra_mod.py build` (round-trip check, mods, natives, icons, asset db,
  zipalign, apksigner v1+v2+v3, always the same key `terramod.keystore`), then `host_mod.py` with `--new-chr` of the selected characters and a merged server_buddies.json
  (names synced from the built BuddyDatabase), verifies the signatures and writes `out/` (+ `out/dump/*.json` = the built databases).
- Skill IDs are assigned in file order (10_macuri, 12_kana, 14_gugba, 15_yapkar), so they differ between combinations. The natives never use fixed IDs: they find skills by
  `SkillType.capacity` marks and reach hidden helper skills as id+1, id+2, ... of the marked skill.  IDs 3843..3852 are reserved by the client (runtime tmpTypes), terra_mod pads past them
  before the first mod skill, so mod skills start at 3853 and a hidden skill can never fall into the reserved block.

## Mod JSON (mods/*.json)
Keys: `skills` (list; `raw` = complete SkillType record, or `template` (0-based index in base SkillData) + `set`; `set` may hold `"effID": "@fx_key"`), `buddies`, `characters`
(`raw` = {info, jobs[], rebirth}; job `skills` are `"@key"` references), `effects` (fx_clone specs), `icons` ({icon_no, file}), `asset_db`, `native` (module names in tools/natives/).
A hidden helper skill must directly follow its visible skill.  Float fields must be float32-exact.  The builders in Kit/builders regenerate these files:
`python3 make_macuri.py <MacuriUpdate folder>` etc. (they read builders/shipped_extract.json = records of the previous release plus base templates).

## Independence rules (Sam, 2026-10-13)
Each native module owns: its own dead-code regions (caves), its own hook sites, its own copies of every helper, its own marks, its own state byte (Gugba).  Nothing is shared.
`nativelib.check_modules` refuses to build when two modules overlap (regions, sites, state bytes, marks); `tests/test_independence.py <libil2cpp.so>` proves on the real file that all 15 subsets
(Gugba also: `tests/test_limit_real.py <original so> <patched so>` runs the real Entity.limitModifiedStatus with the DEF-break hook.)
patch disjoint bytes.  Icons (consecutive, no overlaps; these are the game's 8 unused skill_icon slots, replaced in place): Macuri 128 blood drop (127 no longer used), Kana 129/130 hearts, Gugba 140 whiskey + 141 grandma; 142/143 stay free (slot 112 = the game's own star icon, only read). Art is fitted onto the slot's original pixel size (the game's Sprite keeps that size).  `combine.py check` rejects duplicate characters / icon slots.

| Module | Regions (never executed Mono.Security code) | Hook sites |
|---|---|---|
| macuri_native | 0xAFC890 (2800), 0xB2FB9C (2744) | 0x10917CC SkillDamage, 0xCC3EF8 SkillAttack list, 0xF0CE10 _damageAction |
| kana_native | 0xB32B60 (3500), 0x9FC314 (3460) | 0xCD30D8 swap, 0x10BEA0C EmitMultiSkill, 0x10917A8 SkillDamage, 0x11668B8 PoisonDamage, 0x102C270 AddModifier, 0xCC4048 SkillAttack |
| gugba_native | 0x9FD118 (8268), 0xAFB99C (3420), flag byte 0x2B8C000+0xAF0 (Gugba), Macuri flag 0x2B8C000+0xAF3 | 12 sites (see the module header) |
| yapkar_native | 0xB3398C (8352) | 0xCD9AC4 turn tick, 0xCC3EEC SkillAttack list |

## Marks (SkillType.capacity)
Macuri 5101 Mechanical Reflect (buddy 498: game Counterattack x3.0 ATK, HP lock at 1, kill = full heal + 25% damage stacking; +1 hidden kill counter), 5110 Spear Tomb, 5120 Coercion, 5130 Ten Thousand Spears, 5140 Bloodthirst (character skill 1).
Kana 4611 Heartbeat (+1 buff), 4601 Virus Bullet, 4612 Contrast (+1 = 4614 hidden Pink Heart Poison), 4613 Queen Bee; buddy skill: successRate 4444 pincer line, status 9.
Gugba 4801 Out of the Way, 4802 Whiskey (+1..+4), 4830 Rhythm Headbutt (+1 hidden counter skill, its modifier value = uses so far this battle), 4806 Grandma's Will (+1 4805 fist, +2 4807, +3 4808, +4 4809, +5 4810).
Yapkar 4901, 4902 (+1 4911, +2 4912, +3..+5 ice/dark/thunder column 4941..4943, +6..+9 fire/ice/dark/thunder row 4944..4947, +10..+13 X 4961..4964), 4903 (+1 4913, +2 4914, +3..+5 moon/gravity/photon column 4951..4953, +6..+9 sun/moon/gravity/photon row 4954..4957, +10..+13 X 4971..4974), 4904.

## Verification (do all of it before shipping)
1. `java -jar apksigner.jar verify -v out/TerraBattle-mod.apk` (v1+v2+v3 true for the game APK); the build prints `re-read verification OK`.
2. `python3 -I Kit/tools/tests/verify_apk.py out/TerraBattle-mod.apk out/dump <original game.apk> <Update folders>`: libil2cpp.so == original + exactly those modules; every mark and hidden-skill layout is present.
3. `python3 -I Kit/tools/tests/test_<name>.py` (unicorn emulator with mocked game structures) for each module and `test_independence.py <original libil2cpp.so>`.
(Gugba also: `tests/test_limit_real.py <original so> <patched so>` runs the real Entity.limitModifiedStatus with the DEF-break hook.)
4. Hook safety (added 2026-10-13): `python3 -I Kit/tools/tests/gen_live.py <original libil2cpp.so>` regenerates live_regs.json (whole-function liveness incl. condition flags, per hook site); `python3 -I Kit/tools/tests/check_caves.py <original libil2cpp.so>` proves on EVERY path of EVERY cave that x19-x30/d8-d15 and sp come back unchanged (except what the displaced game instruction writes or what the game no longer reads); the module tests print `REVIEW` lines = caller-saved registers a cave changes that the analysis could not prove dead (review them by hand; all current ones were checked against the real code and are false alarms).  Effects: native code may only play particleEffectSet ids 1..450 (the game's EffectManager pool is a fixed array of 451); never clone particle entries.  Values in mod data should be ones the original game data already uses (icon slots with Sam's art excepted).
5. NOTHING is verified inside the real game: all native code is emulator-verified only.  Test in the game and report.

## Adding a character
Copy an Update folder, write its builder (builders/make_x.py), write a new module in tools/natives/ (pick unused dead-code regions and hook sites, run test_independence), add its marks to verify_apk.py,
list it in update.json (`chr_ids`, `native`, `icons`) and run the build.  Prefer the game's built-in skills over custom natives: custom bomb/missile patches once froze battles.
