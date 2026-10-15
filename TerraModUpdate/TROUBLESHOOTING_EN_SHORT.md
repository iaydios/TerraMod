# Quick Troubleshooting (short version)

Full version: `TROUBLESHOOTING_EN.md`. Nothing here is verified in the real game yet.

## Check first
- Re-run `join_apk.bat`, then install. Old joined APKs in the folder are outdated.
- Compare the APK SHA256 with `release/SHA256.txt` (Macuri f45729df, Kana 19dbe9c4, Gugba 602054cf, Yapkar e2f88fa0, Combo 74b59775).
- Note: which character, which skill, what you did, crash or no effect.

## Game crashes on a skill
- Find the hook in `Kit/tools/natives/<name>_native.py`.
- Effect id must be 1 to 450 (the game's effect pool has 451 slots). Never play cloned effects.
- A hook must give back every register and flag the game reads afterward.
- Test with the real game function in the emulator. Do not use a stub.

## Skill does nothing
- Check `mods/*.json` and `out/dump/ChrDatabase.json`.
- Check the marker values: `capacity` and `successRate` (4444 is only for Kana's buddy skill).
- Buddy skills sit at array index 8 and use BOOST 100.

## Wrong number or text
- Gugba max HP is 9000.
- After editing a builder: rerun builder, check `mods/*.json`, build, read the dump.

## Odd visuals
- Marker-only skills must use status 0 (53 is the red aura).

## Build errors
- `cp: cannot create directory '/root/charwork/tools'` means two builds ran together. Rebuild, one at a time.

## After any native change, run
- `test_<name>.py` for the character
- `gen_live.py`
- `check_caves.py` (must show 0 violations)
- `test_real_splice.py` (0 mismatch)
- `test_independence.py` (all 15 OK)
- `verify_apk.py` and signature check

## Rules
- Use the game's own things. Do not invent or clone.
- One build at a time.
- ASCII file names for Windows.
- Ask for approval before copying files to the PC.
- Log every change in `work_log.md`.

## Leave alone
- Yapkar job SkillAttrib 7 is intentional.

## Still open
- Real-game test of all four characters, especially Gugba's tap skill.
- Headbutt reset on wave 2 is unknown.
- Skill text drafts are not applied.
- Combo 74b59775 and Yapkar e2f88fa0 were delivered 2026-10-14.
