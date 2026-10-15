# TerraModUpdate Work Log (Native Standalone)

Rules (Sam): Confirm skills and formulas before making changes; each character's natives are standalone and do not share hooks; folders are named "English name + Update";
each produces its own standalone APK, but they can be combined freely into one APK; old leftovers must be labeled with where they went and not mixed up; do not touch Sam's TB folder unless he agrees.

## 2026-10-13 Design Confirmation (Sam approved each item)
- Macuri (1289): Mechanical Life (機械生命; equipment, hex shield, immune to the first hit each turn) / Spear Mound (槍塚; 20%, 1.0×3 hits) / Intimidate (威逼; equipment, ×1.5 vs enemies below 33% HP, excludes Ten Thousand Spears, icon = increases physical attack) / Ten Thousand Spears (萬槍; 5%, 10000 unchanged); buddy Mechanical Arm: Blood Thirst (渴血; star icon, each damage dealt restores 0.5 ATK)
- Kana (1290): Heart Racing (心跳加速) unchanged / Virus Bullet (病毒子彈; Pincer (夾擊) or Chain share one roll, 40%, poison, heals) / Contrast Cuteness (反差萌; equipment, magic damage becomes 0 and reflects pink poison, removes physical evasion) / Queen Bee (女王蜂; 10%, enemies only); buddy Heartthrob Revolver (心動左輪): Heartthrob Virus (心動病毒) changes "Magic DEF -50%" to "enemy skill activation chance -50%"
- Gugba (1291): Don't Get in the Way (別擋路) unchanged / Whiskey (威士忌; 30%, each cup +25% with no time limit, max 4 cups per stat, 16 cups total, reset and recalculated when damaged) / Earthquake Slash (地震斬; 30%, horizontal three rows at 3.0 ATK + gravity, not forced) / Gugba Great Earthquake (格古巴大地震; Pincer or Chain 5%, all enemies 1.0×5, 3 random ailments, shuffle positions); buddy Moon Soul (月魂): Grandma's Will (奶奶的意志; tap, once per battle, enemy DEF -100%, Heavy Punch multiplier = cap of 20 hits taken during the battle, at 20 says "Enough…", removes the -90% all-stats backlash)
- Yapkar (1292): Delusion (妄想) unchanged / Madness (瘋狂) and Awakening (覺醒) four elements changed to Pincer or Chain (shared roll, no longer a cross around itself); Symbiosis (共生) 557: DEF and Magic DEF +100%, ATK and Magic ATK +100%; Aura (光環): revive 1 time for the whole field at 1/2 HP

## Architecture Decisions
- One native module per character: tools/natives/<name>_native.py, each with its own cave region, its own hook sites, and its own copied helper routines; nativelib.check_modules automatically checks for site collisions at build time.
- Cave region allocation: Yapkar = PKCS12.GetBytes 0xB3398C; Gugba = 0x9FD118+0xAFB99C; Kana = 0xB32B60+0x9FC314; Macuri = 0xAFC890+0xB2FB9C.
- Built-in options available: gravity = Binding Shadow (束縛陰影; status 38); enemy attack chance reduction = status 9; shuffle = Scatter (skill 2058); dialogue = Entity.ShowMessage.

## Progress Log
- 01:36 Created development tree /home/user/work/upd (temporary) and wrote nativelib.py (framework).
- 01:50 Yapkar native module natives/yapkar_native.py completed and passed emulator tests (tests/test_yapkar.py, shared test framework tests/emu.py):
  Symbiosis 557 DEF/Magic DEF/ATK/Magic ATK +100% (auxiliary modifier value = 100.0), reset to zero after Yapkar dies, does not repeat on turn 2, full-field revive at 1/2 HP (revive given 0.5),
  Pincer/Chain skills attach 3 hidden elemental skills (Madness: ice/dark/thunder; Awakening: moon/gravity/photon). ⚠ Not yet verified in the real game.
  Sam added (01:49): "All natives must be detailed and complete, with no strange omissions." → Every native feature of every character was fully rewritten.
- 01:55 Macuri module natives/macuri_native.py completed and passed simulation tests (tests/test_macuri.py):
  3 hook sites (all belonging only to Macuri): SkillDamage 0x10917CC (Mechanical Life: first damage each turn set to 0, marker = 1-turn modifier; Blood Thirst: attacker restores 0.5×ATK for each damage dealt),
  SkillAttack list 0xCC3EF8 (when Spear Mound appears in the activation list, 2 more hits are appended = 3 hits total), _damageAction 0xF0CE10 (Intimidate: target HP below 33% (strictly less than) damage ×1.5, excluding Ten Thousand Spears marker 5130).
  ⚠ Limitation: Mechanical Life only sets the "damage" to 0; status ailments attached to the same hit are not necessarily blocked (in the game, damage and status are two separate paths).
- 02:05 Kana module natives/kana_native.py completed and passed simulation tests (tests/test_kana.py):
  6 hook sites: position swap 0xCD30D8 (Heart Racing); EmitMultiSkill 0x10BEA0C (Queen Bee: marks only enemies with kind==1, fixing an issue where objects were also marked);
  SkillDamage 0x10917A8 (Contrast Cuteness: magic damage from monsters (SkillType.IsTypeOfMagic) becomes 0 and reflects pink poison; physical is not handled); PoisonDamage 0x11668B8 (poison lifesteal);
  AddModifier 0x102C270 (Virus Bullet forces poison); SkillAttack 0xCC4048 (Heartthrob Virus straight-line pincer, successRate 4444).
  The pink poison skill was changed to "Contrast Cuteness hidden skill id+1", so Queen Bee requires Contrast Cuteness to be unlocked (Lv50 < Lv90, so it is never actually missing).
  Where old features went: poison_stat_share (YSTAT / marker 4602) is not used by any skill, so it was not carried over; star_range / random_power were dropped along with the replaced Super Spike (超級刺擊) and Mechanical Rage (機械狂暴).
- 02:20 Gugba module natives/gugba_native.py written (13 hook sites, 25 caves): Don't Get in the Way (3 sites + swap), Whiskey (cup-count system, reset on damage), Earthquake big-move list expansion (5 hits + 3 random ailments + shuffle),
  Grandma's Will (tap to charge, enemy DEF -100%, Heavy Punch multiplier = hits taken (using the game's own Entity+0x32c hit counter), "Enough…"). Pending simulation tests.
- 02:25 All four modules combined and verified against the real libil2cpp.so: the original bytes at all 24 hook sites matched; tests/test_independence.py verified 15 combinations,
  modules share no modified bytes with each other (pairwise intersection 0; any subset = the union of their individual changes).

## 2026-10-13 Build Phase (continued)
- 02:30 terra_mod.py now uses nativelib.apply_natives (the module list comes from the native field of the mod JSON; effect IDs are supplied by fx_clone.PES_IDS); removed the old gugba_patch / native_patch calls;
  Added raw record support (raw for skills, raw for buddies, raw{info,jobs,rebirth} for characters).
- 02:40 The mod JSON for the four characters was generated by Kit/builders/make_*.py (data source shipped_extract.json = previous released content + original template); skill table in "skills_and_texts.md".
  Icons: Macuri 127 (hex shield, self-drawn), Kana 140/141 (reusing heart), Gugba 143 (whiskey cup, self-drawn); the star uses the game's own icon 112 (read-only, not counted as shared).
- 02:50 Created Kit/scripts (build.sh, run.sh, run_combo.sh, combine.py, make_folder_files.py), the four Update folders and ComboUpdate (combo.txt), each with its own build.bat / join_apk.bat / make_gdresources_tar.bat / README.txt.
- 02:55 Build tests: four single APKs, the four-in-one, Macuri+Gugba, Kana+Yapkar, Macuri+Kana+Yapkar all built successfully; apksigner v2/v3 passed (the game APK also has v1).
  tests/verify_apk.py: libil2cpp.so inside the APK = original + exactly those modules (byte by byte; for Gugba, only the 2 bytes of the tap effect ID are supplied by the build), and every marker and hidden skill position is present.
  Bug found and fixed: skill IDs 3843–3852 are a client-reserved range (runtime tmpTypes = null). The old approach only filled the gap before the second skill, so the hidden auxiliary skill id+1 of the first skill (e.g. Mechanical Life 3842) was pushed to 3853,
  where the native code could not find it and failed silently. Now terra_mod fills up to 3852 before the first mod skill, so mod skills start at 3853 and hidden skills always follow immediately. verify_apk.py also gained a check that a hidden skill must be a real skill, not a gap-filler placeholder.
- 03:05 Old leftovers archived (moved, not deleted; reference tables _archive_old/where_things_went.md and project root 00_新舊檔案去處.md): gugba/patch, gugba/build, gugba/release, gugba/release_yapkar, gugba/gdnew, CharToolFollow, old skill/process documents.
  gugba/ keeps the four character introductions, stories, translations, analysis, and save. Memory file updated (terramod-update-architecture.md; old memory marked as superseded).
- 03:10 Each folder's release/ holds split APKs (25 MB per part) + SHA256 + join_apk.bat (four single packs + ComboUpdate four-in-one).
- Not done / not verified: in-game testing on the real game (all natives verified only in the emulator); running the .bat files on Windows/WSL (build.sh was only run on Linux); Macuri / Kana image bins are not in the project (installed on Sam's PC), so gdresources_new in these two folders is empty.

## 2026-10-13 Sam's Second Round of Feedback (04:12)
- Sam: 1. fill in missing files from elsewhere; 2. the big earthquake should not freeze, the rest random; 3. gravity at 75% is fine; 4. make the work as detailed as possible; 5. skill descriptions should not use personal-flavor lines, may follow the story, but show them to him first; 6. Yapkar DNA recode portrait is off to the right and needs to be centered.
- 2 (big earthquake): the ailment pool changed from 7 kinds to 6 (poison, sleep, paralysis, confusion, loss of fighting spirit, gravity), freeze removed; the other 3 are still drawn at random without repetition from the pool by the native code, and the shuffle skill follows right after the pool (id+7).
  Changes: natives/gugba_native.py QUAKE_POOL 7→6; builders/make_gugba.py removed icebind; tests/test_gugba.py (ran 200 times to confirm all 6 kinds appear, 3 distinct kinds each time, shuffle id=+7); verify_apk.py hidden skill layout 4820:+1..+7. test_independence 15 combinations still pass.
- 3 (Earthquake Slash): keep gravity success rate at 75%, 2 turns, can be resisted (already the current state).
- 6 (Yapkar portrait): in the original piece image, the transparent area is 17 px on the left and the content center is at x=65 (center 53), so it sat to the right. Re-cropped from yapkar_illust.png (face center x≈420, side length 190, top y=6); the face center now lands at x≈53.
  The old image was left outside /tmp; no backup needed. Regenerated Pieces/Illust/Profile bins (Kit/scripts/make_images_yapkar.py) → YapkarUpdate/gdresources_new; asset_db's Pieces 3007 version 131→132 so the game re-downloads (otherwise it may still show the old cache).
- 5 (skill descriptions): draft in "skill_text_draft_story_style.md" (left = current, right = draft); not yet applied to the mod JSON; the three-language texts will be changed and repacked after Sam confirms.
- Icon correction: Gugba 143 was originally a whiskey cup I had drawn myself; later I found Sam's original skill_icon_143.png (31×37) in the old files and switched back to the original image. Kana 140/141 were already original images. Macuri 127 (hex shield) is still my own drawing, pending Sam's review.
- 1 (missing files): what was missing from the project were the Macuri / Kana original image files and bins (art, gdresources), and the original mod JSON for the Macuri buddy Mechanical Arm; these exist only on Sam's computer at TB\TerraMod. A new request to connect to the computer was sent; once Sam allows it, these files will be read only and added to MacuriUpdate / KanaUpdate (none of his files will be modified).
- Rebuilt: the four single packs and the four-in-one all passed verify_apk.py; release/ parts and SHA256 updated.

## Filling in Missing Files (2026-10-13, Sam's request #1)
- Source: Sam's computer C:\Users\User\Desktop\TB\TerraMod (read-only staging; none of Sam's files were modified).
- MacuriUpdate/art: macuri_lambda, illust, piece, profile, profile_m, bimg_521, buddy_521a/b; gdresources_new gained 7 bins (Illust/Pieces/Profile×2/BuddyImages×2/BuddyThumbs, 3001 + 521).
- KanaUpdate/art: kana_illust, kana_piece, kana_profile, kana_profile_m, bimg_522, buddy_522a/b; gdresources_new gained 7 bins (3002 + 522).
- MacuriUpdate/ref_sam_pc_originals/: old mods 10 and 11 JSON and a blank character_settings_table.txt (reference only, not used in the build).
- self_drawn_icons (hex shield 127, whiskey cup 143) stored in _archive_old/self_drawn_icons/.
- To do: plan consecutive icon numbering; release not yet rebuilt after the file fill-in (bins already prebuilt; whether to include them in build.sh still to be verified).

## Icon Cleanup (2026-10-13, Sam: consecutive numbers; self-drawn icons use the ones I drew; Blood Thirst uses a blood drop; Grandma's Will uses the grandma head)
- Verified: the game loads SkillIcons/skill_icon_N by name; each image is registered twice in the resource list (ResourceManager in globalgamemanagers): Texture2D and Sprite. There are 147 existing images; the only ones not used by any skill are 127–130 and 140–143.
- New numbering: Macuri 127 hex shield, 128 blood drop (Blood Thirst); Kana 129, 130 heart; Gugba 140 whiskey cup (self-drawn), 141 grandma head (Grandma's Will, including "Enough…"); 142 and 143 left empty.
- Important finding: each slot's Sprite keeps its original image size (e.g. 127 is 41×34). icon_patch now pastes the image onto a transparent canvas at the slot's original size (scaled down proportionally and centered only if too large), to avoid stretching or cropping.
- Backups: Sam's original 143 image and Kana's old 140/141 images are in _archive_old/old_icon_numbers/; self-drawn previews are in _archive_old/self_drawn_icons/.
- Rebuilt the Macuri/Kana/Gugba/Yapkar single packs and the four-in-one; verify_apk ALL OK; release/ updated in all four folders; after merging the split files the SHA matches SHA256.txt.
- Extending to 148 and above: not done. Besides adding a Texture2D, it would also require a Sprite (four-vertex rectangle, with vertices and rect adjusted to size), two resource list entries, and reordering the SerializedFile object table; cannot be verified in the real game.

## Macuri "Mechanical Regeneration" Mechanic Change (2026-10-13, Sam chose option 1)
- Before: the first damage each turn was nullified. New: takes +33% damage from all sources, and fully healed at the start of each turn.
- Draft v4 line 14 updated; name changed from "Mechanical Life" to "Mechanical Regeneration" (in-game name not yet changed).
- Code not yet changed. Initial feasibility assessment: the +33% can be changed at the damage entry point (Entity.SkillDamage, the existing macuri dmg hook) by changing w1; but need to confirm whether basic attacks go through the same entry point. Full heal each turn needs a new turn-start hook point, which cannot be shared with Yapkar's 0xCD9AC4 (independent-module rule); another location needs to be found and analyzed.

## Apply Step: Macuri Mechanic, Skill Names and Texts (2026-10-13)
- Macuri: Blood Thirst (5140) changed to the character's first skill; Mechanical Regeneration (5101) changed to a skill of the buddy Mechanical Arm (498); hidden skill 5102 and "first damage nullified" removed.
- macuri_native: dmg hook (0x10917CC) multiplies damage to targets with Mechanical Regeneration by 133/100; added turn-start hook 0xCD9AC0 (PreEvaluateStatusManager, offset by one instruction from Yapkar's 0xCD9AC4), fully heals every living marked unit. test_macuri rewritten and passing; all 15 test_independence combinations pass.
- Names: Mechanical Life → Mechanical Regeneration; Virus Bullet → Charm Bullet; Gugba Great Earthquake → Planet Rift (including each sub-skill name); Heavy Punch → Doom Strike.
- Texts: the four characters' texts changed to Traditional Chinese / English / Japanese per draft v4.2; Kana uses the original descriptions (Heart Racing; Queen Bee uses Sam's revised version); the Ten Thousand Spears description is "Concentration (凝神)"; Don't Get in the Way's effect unchanged (Sam has not yet given a new effect).
- Rebuilt: the four single packs and the four-in-one pack, all passing verify_apk ALL OK; each release/ updated and SHA verified.
- Limitation: the +33% only hooks SkillDamage, so non-skill sources such as poison may not be affected; all native code is still verified only in the emulator and has not run in the real game.

## Don't Get in the Way Effect Changed to Only Pushing Enemy Blocks (2026-10-13, Sam)
- Removed "pushed enemies have their physical DEF reduced by 10%": deleted gugba_native's push cave and hook site 0xCD30E4 (Gugba now has one fewer hook site), skill spower changed to 0; the block-push itself (4801's canMove check) unchanged.
  The description changed to "Charges straight ahead; anything in the way gets knocked aside. Can push all blocks (except bosses)." test_gugba push test removed and passing; Gugba single pack and four-in-one rebuilt, verify_apk ALL OK, 15-combination independence passing; release updated.

## Sent to Sam's Computer (2026-10-13)
- Destination: C:\Users\User\Desktop\TB\TerraMod\1013V1\ (specified by Sam; everything goes here from now on).
- Method: the Linux workspace on the device could not be started, so the files were split into tar.gz (35 × 25 MB + 1 supplementary pack), sent to 1013V1\_parts, with 解壓TerraModUpdate.bat (merges, shows SHA256, extracts) and README.txt attached.
- Main pack SHA256 d42d92ab…2075; supplementary pack (5 out_check + 6 __pycache__, Sam requested "all of them") SHA256 6a661faf…f135.

## All Filenames Changed to English and Re-sent (2026-10-13, Sam: "Are you using Traditional Chinese as filenames? Change to English first")
- Extraction failure suspected to be caused by Chinese filenames / Chinese text in the .bat files on Windows. All 48 Chinese filenames and folder names renamed to English (mapping table NAMES_zh_to_en.txt); references within text files updated accordingly; all .bat files stripped of Chinese, keeping English only (existing Chinese / French rem lines deleted).
- Repacked (including out_check, __pycache__) and sent to TB\TerraMod\1013V1\pack_en\ (parts\ 35 split files + extract_TerraModUpdate.bat + README.txt); main pack SHA256 99fe3757…c77a. Sam is asked to delete the old 1013V1\_parts and the .bat/.txt files with Chinese names.

## 2026-10-13 (late) Gugba Planet Rift fix
- Sam: the game's own earthquake plays its animation ONCE and deals 5 hits; our Planet Rift cast the whole skill 5 times (5 animations) and froze the game.
- gugba_native.py: removed the 4 extra copies of the quake from the emitted list (QUAKE_HITS gone).  The quake is now cast once (skill data = the game's own Forced Tremor, id 275, with power 1.0 / emit 5 % / mark 4820); the 3 random status skills + the shuffle are still appended.
- tests/test_gugba.py updated (list = quake x1 + 3 statuses + shuffle); all emulator tests, test_independence (15 subsets) and verify_apk (single + combo) pass.
- Rebuilt GugbaUpdate/release and ComboUpdate/release (game APK only; both Host APKs are byte-identical to before).  Not yet delivered to Sam's PC (waiting for his OK).
- Not yet found: the cause of "skills freeze" is NOT proven to be this; unmodded vs single builds still to be tested by Sam.

## 2026-10-13 (night) Gugba skill 4: Planet Rift -> Rhythm Headbutt
- Sam: the quake is replaced by Rhythm Headbutt (節奏頭槌) (icon 34, non-elemental physical 1.0x ATK, +1.0x ATK per use, no cap within the wave, resets next wave, pincer only).
- Native (gugba_native.py): mark 4830. "gadd" (List.Add hook) increments the attacker's counter modifier (hidden skill id+1, value = uses so far) once per cast; the "fist" cave (_damageAction attenuation hook) returns max(counter, 1.0) as the factor for this skill. Quake code (repeat, random statuses, scatter) removed completely.
- Data (make_gugba.py): base template 1677 (single-target physical, effID 99), condition=1 (pincer only), emitRatio 30 (my default, Sam did not specify), hidden id+1 = base 1960 (inert kind-5 skill; NOT status 53, which would multiply all stats).
- "Wave" = one battle: the counter lives on the entity (modifier life -1) and entities are rebuilt per battle. UNVERIFIED in game: check that wave 2 starts at 1.0 again.
- tests/test_gugba.py rewritten (counter 1..100 no cap, per character, other skills untouched, one count per cast); verify_apk.py layout 4830:+1.

## 2026-10-13 (night 2) ROOT CAUSE of "every skill freezes/crashes": Gugba damage hook clobbered x8
- Sam: every skill that was cast froze/crashed the game; the old pack (shared-hook natives) had worked.
- Compared the old working libil2cpp.so with the new ones byte by byte: the new Gugba module added a hook inside Entity.SkillDamage (0x10917DC, "damage taken": whiskey reset + hit counter) that the old build never had.
- At 0x10917DC the game has just loaded x8 (`ldr x8,[x8,#0x640]`) and uses it two instructions later (`ldr w24,[x8]`).  The cave "gdmg" overwrote x8 (it saved x0-x5/d0/x19-x22 only), so the very first damage >= 1 dealt to anyone made the game read from address 0 -> crash.  Reproduced with the REAL game code in the emulator (tests/test_real_splice.py: build 1c79fb39… -> invalid read at 0x10917E8, x8 = 0).
- Fix: gdmg saves/restores x8.  Fixed builds: Gugba APK f4507c3c…, Combo APK 00372cc3….
- Why the old tests missed it: they checked the cave's own results, never that the registers the game still needs come back unchanged.
- New checks: tests/gen_live.py + live_regs.json (registers the original code reads after each hook site, from the original libil2cpp.so) and Emu.call() verifies every hook cave hands them back unchanged (all 24 caves of the 4 modules are covered; intentional changes are whitelisted in the test: damage w1 in Kana/Macuri, AddModifier flags w24 in Kana).  tests/test_real_splice.py runs the real patched Entity.SkillDamage (all three hooks chained) against the original.
- Also verified: every native region has no outside caller except the neighbouring dead Mono.Security methods; verify_apk + test_independence (15 subsets) pass.

## 2026-10-13 (night 3) Red glow on the portraits in battle removed
- Sam: portraits of some characters glow red during battle even when nothing is happening (screenshot: two of the four party members).
- Cause (game code): StatusModifier.InitEffect (0x11696A8) looks at the status kind of every modifier: kind 53 -> Entity.SetPowerupMode(true) (effect 0x8F, the "power-up" aura), kind 15 -> SetAutoHealMode.  Our mark-only passives were built from a template with status 53 (all stats x1.0); InitEquipSkills turns every kind-5 skill into a permanent modifier, so the aura was on for the whole battle.
- Fix (data only, no native change): status 53 -> 0 on the 7 mark-only skills: Macuri Blood Thirst / Intimidate / Mechanical Regeneration, Kana Heart Racing / Contrast Cuteness, Gugba Grandma's Will (activated) / "Enough…".  Status 0 on a kind-5 skill is inert (same as the game's own skill 1960/1961).  Kept status 53 on Kana's hidden Heart Racing (enhanced): it is the real 1-turn x1.1 buff for the ally, so it still glows only while it works.
- Not touched: Kana Queen Bee (kind 3, status 53, success 100) may still put the aura on enemies it hits; Sam's report was about the party portraits.

## 2026-10-13 (night 4) Buddy (小跟班) skills audit
- Sam: "The buddy skills were not changed. / I meant the skills are malfunctioning, not the glow." (symptom not described).
- Read the game code: Status.EvaluateBuddy puts the buddy skill at slot 8 of the skill array; EmitCheck slot 8 uses the buddy's BOOST value (ours 100); getHopBreakSkills / EmitMultiSkill / InitEquipSkills loop the whole array, so Macuri 5101, Kana virus (line 4444) and Gugba tap 4806 are found like character skills.  Status 0 on a kind-5 skill also exists in the shipped game (1961, 2507, 2970).
- tests/test_real_splice.py extended: real patched Entity.SkillDamage with ALL marks of the module (buddy marks included) on victim and attacker, for Macuri, Kana and Gugba separately: registers identical to the original (all OK).  Emulator tests of the four modules re-run: all pass, 4+6+12+2 caves covered.
- No defect found; nothing rebuilt or delivered.  Waiting for Sam to say which buddy does what wrong in game.

## 2026-10-13 (night 5) Gugba tap skill "Grandma's Will" crash: root cause + fix
- Symptom (Sam): pressing/tapping the buddy skill crashes the game.
- Root cause (read from real libil2cpp.so): EffectManager's instance pool [mgr+0x70] is a fixed array of 451 (`mov w1,#0x1c3` at 0x10d7df0) and 0x10d80a8 bounds-checks `len > id`. Our tap effect used a CLONED particleEffectSet entry (se_clone of 271 with sound gravity_final) = id 451 -> IndexOutOfRangeException the moment the tap played effects.
- Fix: no cloned effect any more: tapfx plays existing ids 372, 270 and 271 (gather, silent). make_gugba.py no longer has an "effects" entry; terra_mod.py now refuses to build when a cloned particle id > 450 reaches native code; test_gugba.py asserts every fx id in 1..450.
- Rebuilt GugbaUpdate (sha 09c14fef...) and ComboUpdate (2f3eb169...); verify_apk, test_gugba, test_real_splice, test_independence OK. Real ShowHopBreakIcons / EmitHopBreak emulation OK with id 271.
- NOT delivered to Sam's PC yet (waiting for his OK). Kana fx_queen is an effectSet (not particle) entry; no fixed 480 array found, left as is.

## 2026-10-14 (night 6) Full re-check of all characters (Sam: use the game's own things, check hook points carefully)
- Data audit of every mod skill/job/info against the original databases: only deviations left are Sam's icon slots (127-130, 140, 141), native marks (capacity), Kana buddy successRate 4444 (Kana line hook), Kana hidden Pink Heart Poison life -1, Yapkar job SkillAttrib 7 (a valid skill attrib value but no original job uses it; kept, asked Sam).
- Fixed: Kana Queen Bee used a CLONED combo effect (effectSet 480) -> now original effect 205 (heart homing, same as Charm Bullet); Gugba Doom Strike hidden skill carried successRate 4444 (Kana's line mark; in a combo Kana's line hook would have rewritten it) -> 100; no particle/effect clones remain (EffectSet 479/450 = original counts).
- Gugba max-level HP (HPmax) 10287 -> 9000 at Sam's request (first 8000, then 9000). Job hash recomputed by the build.
- Hook points: gen_live.py rewritten (whole-function CFG liveness incl. NZCV, callee param counts from methods.tsv, noreturn helpers); emu.py check now also gives sentinels to d regs/NZCV, hard-fails on callee-saved changes, prints REVIEW lines for live caller-saved changes; all 24 REVIEW items checked by hand against the real code = false alarms (arg-register over-approximation / return type). New check_caves.py: static proof per cave/path of x19-x30, d8-d15, sp balance + 16-byte alignment (mutation-tested). Sites: no live flags, the only 2-instruction site (0x108ee64) has no branch into its second instruction, each module region is a never-called Mono.Security method (only table pointers + Mono.Security/X509Certificate-import callers), 0x32c hit counter is the game's own field.
- Builds: Gugba 9afd6245..., Kana 19dbe9c4..., Combo 79b94fd4... (project release updated, NOT delivered to Sam's PC yet).

## 2026-10-14 night 7: Gugba tap skill, DEF cut 25% -> 99%, no chain-link animation (Sam's in-game test)
- Sam's report: (1) the tap animation shows a lock/chain, he wants only the concentration effect; (2) enemy DEF dropped only ~25%, wants 99%.
- Cause 1: tapfx played particleEffectSet 270 `gathering_02`, whose texture (gathering02, extracted from resources.assets) is a chain-link icon. Removed; tap now plays 372 skill_hop (flash) + 271 gather (circle) only. test_gugba asserts [372, 271].
- Cause 2: the game's own Entity.limitModifiedStatus (0x1078E40) caps every enemy-side reduction at base x 0.3 (float 0.3 at 0x204F1E4), so a -100% modifier became about -30%. Proven on the REAL function in the emulator (tests/test_limit_real.py): enemy, modified 4 / base 400 -> original 280, patched 4.
- Fix: new hook cave `hdef` at 0x1078E68 (displaced `ldr x23,[x21,#0x38]`): if the entity carries a modifier whose SkillType mark is 4810 (the DEF-break skill) skip the cap, everybody else unchanged. Only caller-saved x8-x13 used (not live there per gen_live). Side effect: while the 1-turn DEF-break lasts, other stat reductions on that enemy are also uncapped.
- Data: grandma_defdown spower -100 -> -99 (builders/make_gugba.py), README texts updated.
- Verified: test_gugba/kana/macuri/yapkar OK, gen_live (13 sites in gugba), check_caves 0 violations, test_independence 15 subsets OK, test_real_splice OK, test_limit_real OK, verify_apk ALL OK (single and combo), dump: skill mark 4810 spower -99.
- Builds: Gugba 602054cf (host unchanged 9f97d553), Combo 1c53acd7 (host cde6c44a). Macuri 90c90130, Kana 19dbe9c4, Yapkar 095bb423 rebuilt and unchanged. Release folders of Gugba and Combo re-split in the project; NOT yet copied to Sam's PC (waiting for his OK).
- Earlier slip in this thread: I first claimed buddy 500 pointed one skill too far; wrong, skill ID = list index + 1, buddy 500 -> tap skill is correct.
- 2026-10-14: Sam reports Gugba (602054cf) in-game test perfect after the DEF cap fix.

## 2026-10-14 night 8: Macuri buddy skill Mechanical Regeneration -> Mechanical Reflect (Sam's request after Macuri in-game test "perfect")
- Sam's spec: icon = the game's green counter fist; when pincered the buddy counters 3.0 ATK, non-elemental physical; Macuri's HP is locked at 1 (lethal damage leaves 1 HP, and the lock holds for EVERY hit of that same monster attack); if the counter kills the enemy -> full heal and +25% damage, stacking without limit for the rest of the battle; if it does not kill, the NEXT monster attack kills him.
- Design: the game's own Counterattack (skill 47 template: kind 2, condition 4, effEmit 1, range 3, icon 5, effID 54) with power 3.0, attrib 0, mark capacity 5101, emitRatio 100; hidden skill id+1 (template 1960, inert) carries the kill counter as a permanent modifier. The game fires the counter itself right after the monster attack (EmitCounterSkill loops the buddy slot with BOOST 100). Icon 127 is no longer used (only 128 drop).
- Natives (macuri_native.py): removed the per-turn tick hook 0xCD9AC0 and Regeneration. SkillDamage hook (0x10917CC): victim with mark 5101: if damage would leave <=0 HP, damage = HP-1 and state byte 0x2B8C000+0xAF3 = 1; at 1 HP with the byte set damage -> 0 (all hits of the same attack); byte clear -> damage goes through (dies). Counter hit (skill mark 5101) lethal for the victim -> kill counter +1, attacker healed to full. SkillAttack start hook (0xCC3EF8, runs for monster attacks and for the counter) clears the byte, so a surviving 1-HP Macuri dies to the next attack. _damageAction hook (0xF0CE10): every damage hit of the owner x (1 + 0.25 x kills) (interpreted as a damage multiplier, same effect as +25% ATK).
- Verified: test_macuri (rewritten: lock, same-attack multi-hit, release, kill credit, stacking), gugba/kana/yapkar tests, gen_live, check_caves 0 violations, independence 15 subsets OK, verify_apk ALL OK. Builds: Macuri 2eeb1681, Combo 664d2653; Kana 19dbe9c4, Gugba 602054cf, Yapkar 095bb423 unchanged. Release folders of Macuri and Combo re-split; NOT delivered to Sam's PC (waiting for OK).
- Unverified in the real game: that the native range-3 counter hits the attacker as intended, kill detection (damage >= current HP), the heal inside the SkillDamage hook, lock release timing.
- 2026-10-14: Macuri 2eeb1681 + Combo 664d2653 release delivered to Sam's PC (Macuri/Combo release folders); Sam must rerun join_apk.bat.

## 2026-10-14 night 9: Mechanical Reflect power 3.0 -> 2.5 (Sam)
- Sam: counter every enemy that attacks Ma'curi with ATK x2.5; "lock HP once, crippled twice in a row = dead" (= existing lock behaviour, kept; kill heal + 25% stack kept because he did not remove them).
- Data only: make_macuri.py power 2.5 + texts (zh/en/ja). Range stays 3 (the game's most common counter range; assumed to hit all pincering enemies, unverified; the game's own 'Mighty Counter' 2474 uses range 1/2.5). Trigger stays condition 4 (any pincer); the game has no counter condition for plain single attacks (only pincer 2/3/4 and magic 6).
- Builds: Macuri f45729df, Combo 509d6e45; Kana/Gugba/Yapkar unchanged. NOT delivered (the 2eeb1681/664d2653 versions are on Sam's PC).
- 2026-10-14: Macuri f45729df + Combo 509d6e45 delivered to Sam's PC.

## 2026-10-14 night 10: Yapkar Madness / Awakening now hit pincer + row + column + X (Sam)
- Sam: skills should be Pincer+row+column (all three, not only the column), then also add X "so the field looks full".
- Before: visible skill = game range "Pincer + column" (fire 299 / sun 3075) + hidden column versions only. Game has twins "Pincer + row" (fire 302, ice 412, dark 467, thunder 358, sun 3076, moon 3180, gravity 2273, photon 2263) and "X-shape" skills (range 10, 5x5: Sun Ring Strike (日輪擊) 3345, Moon Ring Strike (月輪擊) 3311).
- Now: hidden id+6..+9 = row twins (marks 4944-4947 / 4954-4957), id+10..+13 = X (marks 4961-4964 / 4971-4974). Awakening sun X and moon X are the game's own skills; the other six X skills use the Sun Ring Strike record with the element's own attrib/effID (fire 1/136, ice 2/137, dark 4/139, thunder 3/138, gravity 18/335, photon 17/329) - values the game already uses, but the combination X-range + these effects is new and untested. Power unchanged (0.5 / 1.0).
- Native: ELEM_COUNT 3 -> 11 (SkillAttack hook appends id+3..id+13), MARKS extended. One emit roll still decides everything (12 element hits + visible per Madness/Awakening, pincered enemies are hit by column and row copies).
- Verified: test_yapkar, gen_live, check_caves 0, independence 15 OK, verify_apk ALL OK, dump layout checked. Builds: Yapkar bee20cc6, Combo 9b7923ad; Macuri f45729df, Kana 19dbe9c4, Gugba 602054cf unchanged. NOT delivered (PC has Yapkar 095bb423 and Combo 509d6e45).
- Risks: many animations in one attack (game froze when Planet Rift repeated one skill 5x, here every skill is different); X-range with cloned-attrib effects untested.
- 2026-10-14: Yapkar bee20cc6 + Combo 9b7923ad delivered to Sam's PC.

## 2026-10-14 night 11: Yapkar X now radiates from every struck enemy (Sam: the X should radiate out from each position that gets hit)
- Cause: the game's X型 range 10 (BattleManager 0xce44ec) is an X around ONE origin cell given by the caller, not around each pincered enemy. Reading BattleManager.IterateList2 (0xce5230) showed the game already implements ranges 13-17 = 'pincer + shape around EVERY pincered enemy'; range 16 calls the X routine (0xce44ec) centred on each pincered entity (jump table index 3), but no game skill uses range 16 in its data.
- Change: the 8 X skills (hidden id+10..+13 of Madness / Awakening) now use range 16 (sx,sy 5,5 as the game's own X skills). Data only, no native change.
- Verified: test_yapkar, verify_apk ALL OK, dump shows range 16. Builds: Yapkar e2f88fa0, Combo 74b59775 (others unchanged). NOT delivered (PC has the night-10 build bee20cc6 / 9b7923ad).
- Unverified in real game: range 16 has never been used by a shipped skill; if the X looks wrong or crashes, fall back to range 10.

## 2026-10-15: Delivery pending (not on the user's PC)
- Yapkar e2f88fa0 (range 16 X skills) and Combo 74b59775 are built and split in the project release folders. Not delivered: the device bridge was disconnected on every attempt (00:21 to 00:25 UTC). The user will approve the delivery when they are at home.
- The user's PC still has Yapkar bee20cc6 and Combo 9b7923ad, plus Macuri f45729df, Kana 19dbe9c4, Gugba 602054cf.
- Handoff guide for other Claude sessions: HANDOFF_EN.md (English, no personal names).
- 2026-10-15 09:28 UTC: Yapkar e2f88fa0 and Combo 74b59775 delivered to the user's PC (both 7 files written).
