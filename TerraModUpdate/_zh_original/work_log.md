# TerraModUpdate 工作紀錄（原生獨立化）

規則（Sam）：技能與公式先確認再動手；每個角色原生獨立、不共用掛鉤；資料夾用「英文名+Update」；
各自產生獨立 APK，但可任意組合進同一個 APK；舊殘骸要標明去處、不要搞混；不動 Sam 的 TB 資料夾，除非他同意。

## 2026-10-13 設計確認（Sam 已逐項同意）
- Macuri(1289)：機械生命(裝備,六角盾,每回合第一下免疫)／槍塚(20%,1.0×3下)／威逼(裝備,對HP<33%敵人×1.5,萬槍除外,圖示=增加物理攻擊)／萬槍(5%,10000不變)；夥伴 機械手臂：渴血(星星,每次造成傷害回復0.5 ATK)
- Kana(1290)：心跳加速不變／病毒子彈(夾擊或連鎖共用判定,40%,中毒,回血)／反差萌(裝備,魔法傷害變0並反射粉毒,移除物理迴避)／女王蜂(10%,只對敵人)；夥伴 心動左輪：心動病毒把「魔防-50%」改成「敵人技能發動機率-50%」
- Gugba(1291)：別擋路不變／威士忌(30%,每杯+25%無時限,每項最多4杯共16杯,受傷歸零重算)／地震斬(30%橫三列3.0ATK+重力,不強制)／格古巴大地震(夾擊或連鎖5%,全敵1.0×5,隨機3異常,洗牌位置)；夥伴 月魂：奶奶的意志(點擊,一場一次,敵人防禦-100%,重拳倍率=整場被打次數上限20,滿20句「夠了…」,拿掉全能力-90%反噬)
- Yapkar(1292)：妄想不變／瘋狂與覺醒四屬性改夾擊或連鎖(共用判定,不再自身十字)；共生557 防禦魔防+100%、攻擊魔攻+100%；光環全場復活1次1/2血

## 架構決定
- 每角色一個原生模組 tools/natives/<名>_native.py，各自洞穴區、各自掛鉤位置、各自複製小程式；建置時 nativelib.check_modules 自動檢查撞位。
- 洞穴區分配：Yapkar=PKCS12.GetBytes 0xB3398C；Gugba=0x9FD118+0xAFB99C；Kana=0xB32B60+0x9FC314；Macuri=0xAFC890+0xB2FB9C。
- 內建可用：重力=束縛陰影(status 38)；敵人攻擊機率−=status 9；洗牌=Scatter(技能2058)；對話=Entity.ShowMessage。

## 進度日誌
- 01:36 建立開發樹 /home/user/work/upd（暫存），寫 nativelib.py（框架）。
- 01:50 亞普卡原生模組 natives/yapkar_native.py 完成並通過模擬器測試（tests/test_yapkar.py，共用測試框架 tests/emu.py）：
  共生557 防禦/魔防/攻擊/魔攻 +100%（輔助修飾值=100.0）、亞普卡死亡後歸零、第二回合不重複、全場復活 1/2 血（revive 傳入 0.5）、
  夾擊連鎖技能附加 3 個隱藏元素技（瘋狂：冰/暗/雷；覺醒：月/重力/光子）。⚠仍未在真實遊戲驗證。
  Sam 補充(01:49)：「所有原生都要詳盡完整，不要奇怪的省略」→ 每個角色的每項原生功能都完整重寫。
- 01:55 馬卡利模組 natives/macuri_native.py 完成並通過模擬測試（tests/test_macuri.py）：
  掛鉤 3 處（全部只屬馬卡利）：SkillDamage 0x10917CC（機械生命：每回合第一下傷害變0，標記=1回合修飾；渴血：攻擊者每次造成傷害回復0.5×ATK）、
  SkillAttack 清單 0xCC3EF8（槍塚出現在發動清單時再追加2次=共3下）、_damageAction 0xF0CE10（威逼：目標HP<33%（嚴格小於）傷害×1.5，萬槍標記5130除外）。
  ⚠限制：機械生命只把「傷害」變0，同一擊附帶的異常狀態不一定被擋（遊戲內傷害與狀態是兩條路）。
- 02:05 卡奈模組 natives/kana_native.py 完成並通過模擬測試（tests/test_kana.py）：
  6 處掛鉤：交換位置 0xCD30D8（心跳加速）、EmitMultiSkill 0x10BEA0C（女王蜂：只標記 kind==1 的敵人，修正「連物件都標記」）、
  SkillDamage 0x10917A8（反差萌：怪物打來的魔法傷害（SkillType.IsTypeOfMagic）變0並反射粉毒，物理不處理）、PoisonDamage 0x11668B8（毒吸血）、
  AddModifier 0x102C270（病毒子彈強制中毒）、SkillAttack 0xCC4048（心動病毒 直線夾擊 successRate 4444）。
  粉毒技能改成「反差萌的隱藏技 id+1」，所以女王蜂需要反差萌已解鎖（Lv50 < Lv90，實際不會缺）。
  舊功能去向：poison_stat_share(YSTAT/標記4602) 無任何技能使用，不帶入；star_range / random_power 隨 超級刺擊 / 機械狂暴 被取代而不帶入。
- 02:20 格古巴模組 natives/gugba_native.py 寫成（13 處掛鉤、25 個洞穴）：別擋路(3處+交換)、威士忌(杯數制、受傷歸零)、地震大招清單擴充(5下+3種隨機異常+洗牌)、
  奶奶的意志(點擊上膛、敵人防禦-100%、重拳倍率=被打次數(用遊戲自己的 Entity+0x32c 被打計數)、「夠了…」)。尚待模擬測試。
- 02:25 四模組已對真實 libil2cpp.so 組合驗證：24 個掛鉤位置原始位元組全部吻合；tests/test_independence.py 驗證 15 種組合，
  各模組互不共用任何被修改的位元組（兩兩交集 0，任意子集 = 各自差異的聯集）。

## 2026-10-13 建置階段（接續）
- 02:30 terra_mod.py 改用 nativelib.apply_natives（模組名單來自 mod JSON 的 native 欄位；特效 id 由 fx_clone.PES_IDS 帶入），移除舊 gugba_patch/native_patch 呼叫；
  新增 raw 紀錄支援（skills 的 raw、buddies 的 raw、characters 的 raw{info,jobs,rebirth}）。
- 02:40 四個角色的 mod JSON 由 Kit/builders/make_*.py 產生（資料來源 shipped_extract.json＝上一版釋出內容＋原版範本）；技能表見「skills_and_texts.md」。
  圖示：馬卡利 127（六角盾，自繪）、卡奈 140/141（沿用愛心）、格古巴 143（威士忌杯，自繪）；星星用遊戲自己的 112 號（唯讀，不算共用）。
- 02:50 建立 Kit/scripts（build.sh、run.sh、run_combo.sh、combine.py、make_folder_files.py）、四個 Update 資料夾與 ComboUpdate（combo.txt），各自的 build.bat／join_apk.bat／make_gdresources_tar.bat／README.txt。
- 02:55 建置測試：四個單獨 APK、四合一、馬+格、卡+亞、馬+卡+亞 全部建置成功；apksigner v2/v3 通過（遊戲 APK 另有 v1）。
  tests/verify_apk.py：APK 內 libil2cpp.so ＝ 原版＋剛好那些模組（逐位元組；格古巴只有點擊特效 id 的 2 個位元組由建置帶入），每個標記與隱藏技能位置都存在。
- 抓到並修掉的錯誤：技能 ID 3843–3852 是客戶端保留區（runtime tmpTypes＝null），舊作法是第二個技能才補洞，導致第一個技能(例如機械生命 3842)的隱藏輔助技能 id+1 被推到 3853，
  原生會找不到它而靜默失效。現在 terra_mod 在第一個 mod 技能之前先補到 3852，mod 技能從 3853 起，隱藏技能一定緊跟。verify_apk.py 也加了「隱藏技能必須是真技能、不是補洞佔位」的檢查。
- 03:05 舊殘骸歸檔（只搬不刪，對照表 _archive_old/where_things_went.md、專案根目錄 00_新舊檔案去處.md）：gugba/patch、gugba/build、gugba/release、gugba/release_yapkar、gugba/gdnew、CharToolFollow、舊技能/流程文件。
  gugba/ 內留下四角色介紹、故事、翻譯、analysis、save。記憶檔已更新（terramod-update-architecture.md；舊記憶標為已被取代）。
- 03:10 各資料夾 release/ 放切片 APK（25MB 一片）＋SHA256＋join_apk.bat（四個單獨包＋ComboUpdate 四合一）。
- 尚未做／未驗證：真實遊戲內測試（全部原生只有模擬器驗證）；Windows/WSL 上實跑 bat（只在 Linux 實跑 build.sh）；馬卡利／卡奈的圖片 bin 不在專案內（Sam 電腦已安裝），所以這兩個資料夾的 gdresources_new 是空的。

## 2026-10-13 Sam 第二輪回饋（04:12）
- Sam：1 缺失檔案從別處補；2 大地震不要凍結、其餘隨機；3 重力 75% 可以；4 工作儘量詳細；5 技能說明不要個人特色台詞、可依故事寫，但先給他看；6 亞普卡 DNA recode 頭像偏右要置中。
- 2（大地震）：異常池由 7 種改為 6 種（毒、睡眠、麻痺、混亂、戰意喪失、重力），去掉凍結；其餘 3 種仍由原生從池中隨機不重複抽取，洗牌技能緊跟在池後（id+7）。
  改動：natives/gugba_native.py QUAKE_POOL 7→6、builders/make_gugba.py 拿掉 icebind、tests/test_gugba.py（跑 200 次確認 6 種都會出現、每次 3 種不重複、洗牌 id=+7）、verify_apk.py 隱藏技能配置 4820:+1..+7。test_independence 15 種組合仍通過。
- 3（地震斬）：維持重力成功率 75%、2 回合，可被抵抗（已是現況）。
- 6（亞普卡頭像）：原 piece 圖的透明區在左邊 17px，內容重心 x=65（中心 53），所以偏右。改由 yapkar_illust.png 重新裁切（以臉中心 x≈420、邊長 190、頂端 y=6），臉中心落在 x≈53。
  舊圖留在 /tmp 以外沒有備份需要；重新產生 Pieces/Illust/Profile bin（Kit/scripts/make_images_yapkar.py）→ YapkarUpdate/gdresources_new；asset_db 的 Pieces 3007 版本號 131→132，讓遊戲重新下載（否則可能還看到舊快取）。
- 5（技能說明）：草稿在「skill_text_draft_story_style.md」（左現在、右草稿），尚未套用到 mod JSON；等 Sam 確認後再改三語並重新打包。
- 圖示更正：格古巴 143 原本我自己畫了一個威士忌杯；後來在舊檔案找到 Sam 原本的 skill_icon_143.png（31×37），已換回原圖。卡奈 140/141 本來就是原圖。馬卡利 127（六角盾）仍是我自繪，等 Sam 看過。
- 1（缺失檔案）：專案內缺的是馬卡利／卡奈的圖片原檔與 bin（art、gdresources）以及馬卡利夥伴機械手臂的 mod JSON 原檔，只存在 Sam 電腦 TB\TerraMod。已再次發出連接電腦的請求卡，等 Sam 允許後只讀取這些檔案補進 MacuriUpdate／KanaUpdate（不修改他的任何檔案）。
- 重新建置：四個單獨包、四合一全部通過 verify_apk.py；release/ 分片與 SHA256 已更新。

## 補缺失檔案（2026-10-13，Sam 要求 #1）
- 來源：Sam 電腦 C:\Users\User\Desktop\TB\TerraMod（唯讀暫存，未改動 Sam 的任何檔案）。
- MacuriUpdate/art：macuri_lambda、illust、piece、profile、profile_m、bimg_521、buddy_521a/b；gdresources_new 補入 7 個 bin（Illust/Pieces/Profile×2/BuddyImages×2/BuddyThumbs，3001＋521）。
- KanaUpdate/art：kana_illust、kana_piece、kana_profile、kana_profile_m、bimg_522、buddy_522a/b；gdresources_new 補入 7 個 bin（3002＋522）。
- MacuriUpdate/ref_sam_pc_originals/：舊 mods 10、11 JSON 與空白的 character_settings_table.txt（僅供參考，不參與建置）。
- self_drawn_icons（六角盾127、威士忌杯143）存於 _archive_old/self_drawn_icons/。
- 待辦：圖示編號連號規劃；補檔後 release 尚未重建（bin 已預建，是否納入 build.sh 待驗證）。

## 圖示整理（2026-10-13，Sam：連號、自繪圖用我畫的、渴血用血滴、奶奶的意志用奶奶頭）
- 查證：遊戲以名稱載入 SkillIcons/skill_icon_N；每張圖在資源清單（globalgamemanagers 的 ResourceManager）登記兩筆（Texture2D 與 Sprite）。現有 147 張，沒被任何技能使用的只有 127–130、140–143。
- 新編號：馬卡利 127 六角盾、128 血滴（渴血）；卡奈 129、130 愛心；格古巴 140 威士忌杯（自繪）、141 奶奶頭（奶奶的意志，含「夠了…」）；142、143 保留空著。
- 重要發現：每個槽的 Sprite 保留原圖尺寸（例如 127 是 41×34）。icon_patch 現在會把圖貼到該槽原尺寸的透明畫布（太大才等比縮小、置中），避免被拉伸或裁切。
- 備份：Sam 原 143 圖與卡奈舊 140/141 圖放在 _archive_old/old_icon_numbers/；自繪預覽在 _archive_old/self_drawn_icons/。
- 已重建 Macuri/Kana/Gugba/Yapkar 單包與四合一，verify_apk 全部 ALL OK；四個資料夾 release/ 已更新，分割檔合併後 SHA 與 SHA256.txt 相符。
- 擴充 148 以上：尚未做。除了新增 Texture2D，還要新增 Sprite（四頂點矩形，需依尺寸改頂點與 rect）與兩筆資源清單，並重排 SerializedFile 物件表；無法在真實遊戲驗證。

## 馬卡利「機械再生」機制改動（2026-10-13，Sam 選定方案 1）
- 原：每回合第一次傷害無效。新：受到所有來源傷害 +33%，每回合開始回滿血。
- 草稿 v4 第 14 行已更新，名稱「機械生命」改為「機械再生」（遊戲內名稱尚未改）。
- 尚未改程式。可行性初判：+33% 可在傷害入口（Entity.SkillDamage，現有 macuri 的 dmg 鉤子）改 w1；但需確認普攻是否走同一入口。每回合回滿血需要新的回合開始鉤點，不能與 Yapkar 的 0xCD9AC4 共用（獨立模組規則），需另找位置分析。

## 套用「執行」：馬卡利機制、技能名稱與文字（2026-10-13）
- 馬卡利：渴血（5140）改為角色第一個技能，機械再生（5101）改為夥伴機械手臂（498）的技能；移除隱藏技能 5102 與「第一次傷害無效」。
- macuri_native：dmg 鉤子（0x10917CC）對有機械再生的受擊者傷害 ×133/100；新增回合開始鉤點 0xCD9AC0（PreEvaluateStatusManager，與 Yapkar 的 0xCD9AC4 錯開一行指令），對每個存活且有標記的單位補滿血。test_macuri 重寫並通過，test_independence 15 種組合全通過。
- 名稱：機械生命→機械再生、病毒子彈→魅惑子彈、格古巴大地震→星球地裂（含各子技能名）、重拳→毀滅一擊。
- 文字：四角色依草稿 v4.2 改為繁中/英/日三語；卡奈用原說明（心跳加速、女王蜂採 Sam 修改版）；萬槍說明為「凝神」；別擋路效果未改（Sam 尚未給新效果）。
- 重建：四個單獨包與四合一包，verify_apk 全部 ALL OK；各 release/ 已更新並核對 SHA。
- 限制：+33% 只攔 SkillDamage，毒等非技能來源可能不受影響；全部原生碼仍只在模擬器驗證，未在真實遊戲跑過。

## 別擋路效果改為只推動敵人方塊（2026-10-13，Sam）
- 移除「被推動的敵人物理防禦力降低10%」：刪除 gugba_native 的 push 洞穴與 0xCD30E4 鉤點（現在 gugba 少一個鉤點），技能 spower 改 0；方塊推動本身（4801 的 canMove 判斷）不變。
- 說明改為「橫衝直撞，擋路的全被撞開。可推動所有方塊（Boss除外）。」；test_gugba 移除 push 測試並通過；Gugba 單包與四合一重建、verify_apk ALL OK、15 種組合獨立性通過；release 已更新。

## 發送到 Sam 電腦（2026-10-13）
- 目的地：C:\Users\User\Desktop\TB\TerraMod\1013V1\（Sam 指定，之後全部放這裡）。
- 方式：device 端 Linux 工作區無法啟動，故以 tar.gz 分割（25MB × 35 + 補充包 1）傳到 1013V1\_parts，並附 解壓TerraModUpdate.bat（合併、顯示 SHA256、解壓）與 README.txt。
- 主包 SHA256 d42d92ab…2075；補充包（5 個 out_check + 6 個 __pycache__，Sam 要求「全部都要」）SHA256 6a661faf…f135。

## 檔名全部改英文並重傳（2026-10-13，Sam：「是不是用繁體中文當檔名？先改英語」）
- 解壓失敗疑為中文檔名／bat 內中文在 Windows 出問題。48 個中文檔名與資料夾名全部改成英文（對照表 NAMES_zh_to_en.txt），文字檔內的引用同步更新；所有 .bat 去掉中文，只留英文（原有的中文／法文 rem 行刪除）。
- 重新打包（含 out_check、__pycache__）傳到 TB\TerraMod\1013V1\pack_en\（parts\ 35 個分割檔 + extract_TerraModUpdate.bat + README.txt），主包 SHA256 99fe3757…c77a。舊的 1013V1\_parts 與中文檔名的 bat／txt 請 Sam 刪除。

## 2026-10-13 (late) Gugba Planet Rift fix
- Sam: the game's own earthquake plays its animation ONCE and deals 5 hits; our Planet Rift cast the whole skill 5 times (5 animations) and froze the game.
- gugba_native.py: removed the 4 extra copies of the quake from the emitted list (QUAKE_HITS gone).  The quake is now cast once (skill data = the game's own Forced Tremor, id 275, with power 1.0 / emit 5 % / mark 4820); the 3 random status skills + the shuffle are still appended.
- tests/test_gugba.py updated (list = quake x1 + 3 statuses + shuffle); all emulator tests, test_independence (15 subsets) and verify_apk (single + combo) pass.
- Rebuilt GugbaUpdate/release and ComboUpdate/release (game APK only; both Host APKs are byte-identical to before).  Not yet delivered to Sam's PC (waiting for his OK).
- Not yet found: the cause of "skills freeze" is NOT proven to be this; unmodded vs single builds still to be tested by Sam.

## 2026-10-13 (night) Gugba skill 4: Planet Rift -> Rhythm Headbutt
- Sam: the quake is replaced by 節奏頭槌 (icon 34, non-elemental physical 1.0x ATK, +1.0x ATK per use, no cap within the wave, resets next wave, pincer only).
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
- Fix (data only, no native change): status 53 -> 0 on the 7 mark-only skills: Macuri 渴血 / 威逼 / 機械再生, Kana 心跳加速 / 反差萌, Gugba 奶奶的意志（已發動） / 夠了….  Status 0 on a kind-5 skill is inert (same as the game's own skill 1960/1961).  Kept status 53 on Kana's hidden 心跳加速（強化）: it is the real 1-turn x1.1 buff for the ally, so it still glows only while it works.
- Not touched: Kana 女王蜂 (kind 3, status 53, success 100) may still put the aura on enemies it hits; Sam's complaint was about the party portraits.

## 2026-10-13 (night 4) Buddy (小跟班) skills audit
- Sam: "小跟班技能沒有改阿 / 我是說技能出錯，不是說發光" (symptom not described).
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
- Sam: skills should be 夾擊+橫列+縱列 (all three, not only the column), then also add X "so the field looks full".
- Before: visible skill = game range "夾擊＋縱列" (fire 299 / sun 3075) + hidden column versions only. Game has twins "夾擊＋橫列" (fire 302, ice 412, dark 467, thunder 358, sun 3076, moon 3180, gravity 2273, photon 2263) and "X型" skills (range 10, 5x5: 日輪擊 3345, 月輪擊 3311).
- Now: hidden id+6..+9 = row twins (marks 4944-4947 / 4954-4957), id+10..+13 = X (marks 4961-4964 / 4971-4974). Awakening sun X and moon X are the game's own skills; the other six X skills use the 日輪擊 record with the element's own attrib/effID (fire 1/136, ice 2/137, dark 4/139, thunder 3/138, gravity 18/335, photon 17/329) - values the game already uses, but the combination X-range + these effects is new and untested. Power unchanged (0.5 / 1.0).
- Native: ELEM_COUNT 3 -> 11 (SkillAttack hook appends id+3..id+13), MARKS extended. One emit roll still decides everything (12 element hits + visible per Madness/Awakening, pincered enemies are hit by column and row copies).
- Verified: test_yapkar, gen_live, check_caves 0, independence 15 OK, verify_apk ALL OK, dump layout checked. Builds: Yapkar bee20cc6, Combo 9b7923ad; Macuri f45729df, Kana 19dbe9c4, Gugba 602054cf unchanged. NOT delivered (PC has Yapkar 095bb423 and Combo 509d6e45).
- Risks: many animations in one attack (game froze when Planet Rift repeated one skill 5x, here every skill is different); X-range with cloned-attrib effects untested.
- 2026-10-14: Yapkar bee20cc6 + Combo 9b7923ad delivered to Sam's PC.

## 2026-10-14 night 11: Yapkar X now radiates from every struck enemy (Sam: "是打到的位置上放射出X")
- Cause: the game's X型 range 10 (BattleManager 0xce44ec) is an X around ONE origin cell given by the caller, not around each pincered enemy. Reading BattleManager.IterateList2 (0xce5230) showed the game already implements ranges 13-17 = 'pincer + shape around EVERY pincered enemy'; range 16 calls the X routine (0xce44ec) centred on each pincered entity (jump table index 3), but no game skill uses range 16 in its data.
- Change: the 8 X skills (hidden id+10..+13 of Madness / Awakening) now use range 16 (sx,sy 5,5 as the game's own X skills). Data only, no native change.
- Verified: test_yapkar, verify_apk ALL OK, dump shows range 16. Builds: Yapkar e2f88fa0, Combo 74b59775 (others unchanged). NOT delivered (PC has the night-10 build bee20cc6 / 9b7923ad).
- Unverified in real game: range 16 has never been used by a shipped skill; if the X looks wrong or crashes, fall back to range 10.

## 2026-10-15: Delivery pending (not on the user's PC)
- Yapkar e2f88fa0 (range 16 X skills) and Combo 74b59775 are built and split in the project release folders. Not delivered: the device bridge was disconnected on every attempt (00:21 to 00:25 UTC). The user will approve the delivery when they are at home.
- The user's PC still has Yapkar bee20cc6 and Combo 9b7923ad, plus Macuri f45729df, Kana 19dbe9c4, Gugba 602054cf.
- Handoff guide for other Claude sessions: HANDOFF_EN.md (English, no personal names).
- 2026-10-15 09:28 UTC: Yapkar e2f88fa0 and Combo 74b59775 delivered to the user's PC (both 7 files written).
