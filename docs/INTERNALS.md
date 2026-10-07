# Internals (Terra Battle 5.5.7 / reTB, Unity 2017.4, IL2CPP metadata v24, arm64)

## Pitfalls — each of these broke the game once

1. **Skill IDs 3843–3852 are reserved.**
   - `SkillData.GetType(id)` returns `types[id-1]`, except IDs 3843..3852. Those come from a runtime `tmpTypes = new SkillType[10]` array whose entries are null.
   - A job pointing at one of those IDs freezes the character page.
   - `terra_mod.apply_skill` pads those slots and never hands them out.
2. **Skill ID = list index + 1.** `template` in a spec is the list index (ID − 1).
3. **Bundle object tables must be sorted by PathID.**
   - When rebuilding a bundle under a new name, the new PathIDs keep each object's sign, and `assets_inplace.build` asserts the table is sorted.
   - An unsorted table loads silently but shows a blank piece or illustration, even though the server returns 200.
4. **The asset cache key includes the version.** After re-shipping an image, raise `ver` in `asset_db`.
5. **reTBHost `patchData` `chrInfos` are applied BY INDEX** onto `ChrDatabase.infos`, which is sorted by ID.
   - Entry *i* must describe `infos[i]`, or it overwrites another character. `host_mod` checks this.
   - The `jobs` and `skills` keys are not applied from patchData.
6. **Signatures.** Modded APKs are signed with your own key. Users must uninstall the originals, which wipes reTBHost data, so they must export first.
7. **arm64 only.** Native patches touch `lib/arm64-v8a/libil2cpp.so`, and `armeabi-v7a` is removed from the APK.

## Data encoding

- `data.unity3d` (UnityFS, LZ4) → `resources.assets`. MonoBehaviours have no type trees.
- `mbcodec.py` learns the field layout from the original object plus the JSON dump, then re-encodes. The build aborts unless the original encodes back byte-for-byte.
- Strings in these MonoBehaviours are obfuscated with a 256-byte substitution table, stored inside `global-metadata.dat` (`mbcodec.load_tables`). The text is stored reversed.
- PathIDs: ChrDatabase 12688, SkillData 12700, EffectSet 12692, BuddyDatabase 13474. The AssetVersions TextAsset is found by name.
- Integrity hashes: job / buddy `hash` = sum of the four little-endian int32 words of `MD5(payload + "mist_guardians_keycode")`. See `jobhash.py` and `buddyhash.py`.

## Downloadable images (gdresources)

- URL / file name: `md5(name + "tbguardmistkeycodehiso") + name + ".bin"`. Folders:
  - `android/Pieces` (`img_`)
  - `android/Illust` (`illust_`)
  - `android/BuddyImages` (`buddy_<id>a/b`)
  - `android/BuddyThumbs` (`bimg_`)
  - `Profile` (JPEG, `profile_<id>` and `profile_<id>_m`, same prefix)
- `ENCA` container: a byte substitution through the same table, a nibble swap and xor 0xFF, and a position shuffle. See `assets.py`.
- Bundles are rebuilt in place from a same-length-name original: names, CAB id and pixels are replaced, and the layout stays identical. Texture formats supported: RGBA32, RGB24, ETC2_RGBA8.

## Stats / EXP

- `stat(L) = min + (max-min) * ((L-1)/98) ** coeff`.
- EXP to reach L uses the same curve with `EXP`/`EXPmax`/`EXPcoeff`.
- Saved `jobLevels` value = `(exp << 12) | level`.

## SkillType field offsets (IL2CPP object)

```
blowOff 0x10  attenuation 0x14  category 0x18  condition 0x1c  effEmitCondition 0x20
counterFilter 0x24  kind 0x28  status 0x2c  iconNo 0x30  name/desc/range strings 0x38/0x40/0x48
weap 0x50  attrib 0x54  range 0x58  filter 0x5c  targetDir 0x60  sx 0x64  sy 0x68
emitRatio 0x6c  power 0x70  spower 0x74  successRate 0x78  effID 0x7c  life 0x80  capacity 0x84
```

## Native patches (`native_patch.py`)

- Code caves live in `Mono.Security.Authenticode.AuthenticodeDeformatter::VerifyCounterSignature` (0xAFC890, about 2.8 KB). The game never calls it.
- Every patched site is checked against the expected original bytes before writing.
- **random_power** at `SkillEvaluator::_damageAction` 0xF0CE10 (`fmul s9, s10, s9`):
  - The instruction is replaced with a `bl` to a cave that runs only if `successRate == 4242`.
  - The cave draws `GameRandom.Range(0, 1)` (0xD350CC). Using the game's synced RNG keeps battles deterministic.
  - It walks a cumulative probability table and multiplies `s9` by `BASE + STEP*k`.
  - Only callee-saved registers are live after the site.
- **star_range** at `BattleManager::IterateX` 0xCE4604: makes range 10 with `sx >= 7` also cover the full row and column.

Addresses are for this exact `libil2cpp.so`. Use `tools/analysis/build_maps.py` to regenerate the symbol maps for another build.

## Analysis helpers (`tools/analysis`)

Set `TERRAMOD_WORK` to a folder containing `libil2cpp.so`, `global-metadata.dat`, and the outputs below.

| script | does |
|---|---|
| `build_maps.py` | `symmap.json` (addr→method), `fullmap.json` (method→addrs), `full.s` |
| `strlit.py` | `got2str.json`: string literals referenced through the metadataUsages GOT |
| `disasm.py A B` | annotated disassembly of a range (call targets and string literals) |
| `fn.py Name::Method` | disassemble a method by name |
| `callers.py Name::Method` | who calls it |
| `cg.py Name::Method depth` | call graph |
| `trace_pe.py effID kind [pc]` | emulates the `PlayEffect` dispatch for a given effect / skill kind (reads `pe.s` = `fn.py` output for that method) |
| `texdump.py outdir files…` | decrypt and export textures from gdresources `.bin` files (needs `pip install texture2ddecoder`) |

## reTBHost (server)

- The server is FastAPI running inside Chaquopy: `assets/chaquopy/app.imy`, a zip containing `tb_server/`.
- `host_mod.py` edits JSON data and `.py` sources, recompiles `.pyc` with the same magic, updates `build.json`'s sha1, then aligns and signs.
- Buddy draws: truth kinds are 1/21/30; fellowship (coin) kinds are 0/20.
- The buddy lock flag is bit 2.
