# TerraMod

TerraMod is a toolchain for adding **new content** to Terra Battle when it runs against the reTB private server (reTBHost). Supported content: characters, DNA recodes, skills, companions (buddies) and images. The game is Unity 2017.4, IL2CPP, arm64.

You describe the content in JSON specs, and the tools do the rest:

- re-encode the game databases inside `data.unity3d`, byte for byte;
- register new images in the client's asset index;
- optionally apply small, opt-in native patches to `libil2cpp.so`;
- patch the reTBHost server (Chaquopy / FastAPI) to match;
- align and sign both APKs.

Every step checks its own work. The originals must round-trip exactly before anything changes, every output is read back, and native patch sites are matched against the expected original bytes before they are written.

> This repository contains **no** game files, APKs, game data or artwork. You must supply your own legally obtained copies.

## Features

| Feature | Details |
|---|---|
| New characters / jobs | Clone an existing character, then change names, stats, skills, image ID and profile story (6 languages) |
| DNA recodes | Source character, coin cost, 3 item types and 2 material characters |
| New skills | Clone an existing skill and change any `SkillType` field |
| New companions | Exclusive character, rarity, stats, skill and images |
| Server rules | Unique and locked companions (cannot be sold or used as material); a companion guaranteed on the next coin draw after the player owns a given character |
| Images | Pieces, illustrations, profiles, and companion art and thumbnails, generated as downloadable gdresources files |
| Native patches (optional) | `random_power` multiplies damage by a weighted random factor; `star_range` gives an 8-way star area |
| Save tool | Set a character's level in a reTBHost account export |

The repo ships with two example mods:

- `mods/10_macuri_lambda.json`: the character Ma'curi Λ, with a DNA recode and four skills.
- `mods/11_macuri_mech_arm.json`: the companion Ma'curi's Mech Arm, with a random-damage pincer skill.

## Requirements

- Linux or WSL.
- Python **3.13**. It must match the Chaquopy Python bundled in reTBHost, because server `.pyc` files are recompiled.
- `pip install -r requirements.txt`
- Java (`keytool`), plus Android build-tools `zipalign` and `apksigner.jar` in `build-tools/`. You can point to another folder with `TERRAMOD_BT`.
- `llvm-mc` and `llvm-objcopy`, only if you use the native patches.
- The native helpers: run `sh native/build_native.sh` to build `tools/libetc2.so` (ETC2 encoder, wraps etcpak) and `tools/liblz4.so`.

## Inputs (put them in `input/`)

| Path | Source |
|---|---|
| `TerraBattle.apk` | The original reTB game APK (arm64) |
| `reTB-Host.apk` | The original reTBHost APK |
| `game_data/` | reTBHost's extracted game data (`extracted-gamedata/game_data/`). The build needs `ChrDatabase.json`, `SkillData.json`, `EffectSet.json` and `BuddyDatabase.json`, and stops unless these re-encode byte-exactly to the data in your APK. |
| `gdresources/` | Your original gdresources folder, used as image templates |
| `art/` | Your new PNG / JPEG images, as listed in `images.json` |

## Build

```sh
sh native/build_native.sh   # once
sh build_all.sh             # -> out/TerraBattle-mod.apk, out/reTB-Host-mod.apk, out/gdresources/
```

`build_all.sh` runs three steps, which you can also run on their own:

1. **Game APK** (`tools/terra_mod.py build`)
   - Applies `mods/*.json` in file-name order: skills first, then companions, then characters.
   - Recomputes the integrity hashes and registers the new images in the built-in AssetVersions index.
   - Applies any native patches a spec lists, then aligns and signs the APK.
   - `--dump` writes the modded databases, which step 2 needs.
2. **Server APK** (`tools/host_mod.py`; for a server on a PC see [below](#playing-with-a-pc-server-retbpc--retb-folder))
   - Adds the new characters, recodes, EXP caps and patchData.
   - Adds the companion rules from `server/buddies.json` and recompiles the changed `.pyc` files.
   - Signs the APK.
3. **Images** (`tools/make_images.py`)
   - Builds the encrypted `.bin` files listed in `images.json`. Each one uses an original file whose name has the same length as a template.
   - Merge the output into the player's gdresources, pack it as a tar, and import it in reTBHost.

Optional: `tools/edit_save.py` sets a character's level in a reTBHost account export.

> Both APKs are signed with your own key, so they cannot be installed over the official builds. Players must **export their account** in reTBHost first, uninstall the originals, install the modded APKs, then import the gdresources tar and the account.

## Playing with a PC server (reTBpc / reTB folder)

If the server runs on a PC instead of on the phone, you do not need the reTB Host APK. Patch the reTB folder directly:

```sh
python3 tools/host_mod.py --retb-folder /path/to/reTB --chrdb out/dump/ChrDatabase.json \
    --new-chr 1289 --buddies server/buddies.json
```

- `--chrdb` is the modded database that `terra_mod.py build --dump out/dump` writes.
- The command makes the same server edits as the APK mode, but in place: no signing, no `.pyc` compile.
- It finds every `tb_server` package under the folder, including the copy that **reTBpc installs into `reTB/.venv/.../site-packages`**. That installed copy is the one the server actually runs, so it is patched too.
- Each original file is kept next to it as `*.terramod-orig`. Re-running always starts from those originals, so it is safe to run again after changing your specs.
- Restart the server afterwards.
- **A server update in reTBpc replaces the patched files.** Run the command again after updating.

The phones still need the modded **game** APK, since the new characters and skills live in the client. They do not need the modded reTB Host APK. The images go into the gdresources folder that the PC server serves: copy the `.bin` files from `out/gdresources/` into it. No tar is needed.

## Making your own content

- [`docs/MOD_SPEC.md`](docs/MOD_SPEC.md) describes every spec field.
- [`docs/INTERNALS.md`](docs/INTERNALS.md) documents how the game works under the hood. **Read its "Pitfalls" section first.** Each item in it once froze the game or left an image blank.
- `tools/analysis/` holds the reverse-engineering helpers: symbol maps, annotated disassembly, call graphs, string literals and texture export.

## Layout

```
tools/            build tools (terra_mod, host_mod, make_images, edit_save) and libraries
tools/analysis/   reverse-engineering helpers
native/           build script for libetc2 / liblz4
mods/             mod specs, one set of content per file
images.json       image recipe for make_images
server/           server-side companion rules
docs/             spec format and internals
art/, input/      your own files (not tracked)
```

## A note from the author

Thanks to **Yami_nK** and **Guigeek** ([Terra-Tools](https://github.com/Guigeekun/Terra-Tools)) for their help. Thanks as well to Claude, and to Terra Battle itself.

Terra Battle was my favorite game. I played it right up to the day it shut down, but I never got the chance to see my Ma'curi receive a DNA Recode. That seed stayed with me all this time. Now, after a lot of effort, I've managed to create what I always dreamed of, at least half-successfully (?).

I hope everyone who truly loves Terra Battle, and everyone who is about to, will join in and create the characters they've always imagined.

Once again, my sincere thanks to both of you for your help.

## A Note from the Author

Thanks to **Yami_nK** and **Guigeek** ([Terra-Tools](https://github.com/Guigeekun/Terra-Tools)) for their help. And of course to Claude, and to Terra Battle itself.

Terra Battle was my favorite game, and I kept playing it until the day it shut down. But I never got the chance to see my Ma'curi receive a DNA Recode. That seed stayed in my heart all these years. Today, after a lot of effort, I have, at least half-successfully (?), brought that long-held dream to life.

I hope everyone who truly loves Terra Battle, and everyone who is about to fall in love with it, will join in and create the characters they have always imagined.

That's all. My sincere thanks to both of you for your help.

## License

The code is released under the MIT License (see `LICENSE`). Terra Battle and all of its assets belong to their respective owners. This project is a fan-made tool for private-server use. Do not redistribute game files or assets.
