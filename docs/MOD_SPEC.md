# Mod spec format

Each file in `mods/*.json` is applied in file-name order. A file may contain `skills`, `buddies`, `characters`, `asset_db`, `asset_versions` and `native`. Inside a file, skills are applied first so characters and buddies can reference them as `"@key"`. Text fields take either a string (English) or `{"en","ja","fr","de","es","zh_tw"}`. Missing languages fall back to English.

## skills[]

```json
{"key": "mech_frenzy", "template": 3029,
 "set": {"condition": 1, "range": 3, "power": 1.0, "emitRatio": 100, "effID": 99},
 "name": {...}, "desc": {...}, "range": {...}}
```

- `template`: **list index** of an existing `SkillData.types` entry (skill ID − 1).
- `set`: any `SkillType` field. Useful ones:

| field | meaning |
|---|---|
| `kind` | skill kind (attack, heal, status, …) |
| `condition` | 0 = attack, 1 = pincer, 4 = counter, … |
| `emitRatio` | activation % |
| `power` / `spower` | damage / status power |
| `attrib` / `weap` | element / weapon type |
| `range`, `sx`, `sy`, `filter`, `targetDir` | area shape |
| `status`, `successRate`, `life` | status effect, success %, turns |
| `effID` | visual effect, from `EffectSet` |
| `blowOff` | knock-back |

  For offsets and semantics see `INTERNALS.md`.
- The new skill gets the next free ID. IDs 3843–3852 are skipped automatically.

## buddies[]

```json
{"id": 498, "template": 490, "name": {...}, "desc": {...},
 "exclusiveChrID": 10, "rarity": 8, "type": 9, "MaxLevel": 1,
 "ATKmin": 10, "ATKmax": 10, ..., "image_id": 521, "skill": "@mech_frenzy"}
```

- Any key from `BUDDY_FIELDS_DIRECT` in `terra_mod.py` can be set.
- `exclusiveChrID` also matches characters whose `ancestorChrID` is that ID, so DNA recodes qualify.
- Images: `buddy_<image_id>a` / `buddy_<image_id>b` (large) and `bimg_<image_id>` (thumb).

## characters[]

```json
{"id": 1289, "template_character": 923, "name": {...}, "rarity": 6, "generation": 2,
 "jobs": [{"id": 5166, "template_job": 5022, "image_id": 3001,
           "fields": {"Species": 2, "Attrib": 2, "EXPmax": 9000000, ...},
           "stats": {"HP": [505, 4800], "ATK": [63, 510], ...},
           "skills": ["@a", "@b", 123, "@d"], "skill_levels": [1, 30, 50, 80],
           "profile": {...}}],
 "recode": {"from": 10, "coins": 20000,
            "items": [[132, 5], [97, 1], [10, 15]],
            "mons": [[69, 50], [176, 50]]}}
```

- `stats`: `[min, max]` per stat. The value at level L is `min + (max-min) * ((L-1)/98) ** coeff`, where `coeff` comes from `fields.HPcoeff` etc.
- `fields`: any existing job field. Unknown keys are rejected.
- `recode.items`: `[item_code, count]`. Exactly 3 items and 2 mons are required.
- `image_id` selects `img_<id>` (piece), `illust_<id>` and `profile_<id>[_m]`.
- After building, pass every new character ID to `host_mod.py --new-chr`.

## asset_db / asset_versions

Every new image must be listed, or the client never requests it.

```json
"asset_db": {"Pieces": [{"id": 3001, "w": 106, "h": 106, "ver": 131}],
             "Illusts": [{"id": 3001, "w": 878, "h": 1024, "ver": 131}],
             "BuddyImages": [{"id": 0, "name": "buddy_521a", "w": 367, "h": 605, "ver": 131}],
             "BuddyThumbs": [{"id": 521, "w": 106, "h": 106, "ver": 131}]}
```

`ver` is part of the client cache path. **Raise it every time you re-ship an image**, or players keep the old cached copy.

## native

`["random_power"]` and/or `["star_range"]`. See `native_patch.py`. Both are opt-in per skill:

- `random_power`: active only when `SkillType.successRate == 4242`. Its table (`MULT_BASE`, `MULT_STEP`, `MULT_PROBS`) is at the top of `native_patch.py`.
- `star_range`: active only when `range == 10` and `sx >= 7`.

## server/buddies.json (host_mod)

```json
[{"id": 498, "rarity_letter": "Z", "unique": true, "pool": null, "after_chr": 1289,
  "name": {...}, "max_level": 1, "exp_max": 0, "base_exp": 1, "base_coin": 1,
  "exp_coeff": 2.1, "evolve_id": 0, "coins_to_evolve": 0, "same_bonus_bias": 1}]
```

| field | effect |
|---|---|
| `unique` | at most one copy; delivered locked; cannot be sold or used as material |
| `pool` | `"truth"` / `"fellowship"` adds it to that draw pool; `null` keeps it out of both |
| `after_chr` | once the player owns this character, the next coin (fellowship) draw guarantees this buddy, once |

## images.json (make_images)

See the docstring in `tools/make_images.py`.

- The template must be an original file whose name has the **same length** as the new one.
- The image is resized to the template's texture size, so use a template with the size you want.
