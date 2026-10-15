# TerraModUpdate 修改紀錄：2026-10-13 夜 ～ 2026-10-14（格古巴閃退、全角色檢查、掛鉤點稽核）

用途：Sam 之後遇到問題，先讀這份。它記錄「發生什麼、為什麼、怎麼改、怎麼驗證、哪些還沒驗證」。
更短的流水帳在 `work_log.md`；建置方法在 `Kit/BUILD.md`；技能內容在 `skills_and_texts.md`。
語言：Sam 用繁體中文；檔名一律英文（Windows 解壓問題，見 `NAMES_zh_to_en.txt`）。

---

## 0. 一眼看完（目前狀態）

| 角色 | 單包 SHA256（TerraBattle-mod.apk，開頭） | 本次有沒有改 | 已放進 Sam 電腦的 release 資料夾 |
|---|---|---|---|
| 瑪庫里 MacuriUpdate | 90c90130 | 沒改（稽核沒找到問題） | 是（2026-10-14 重放一次） |
| 卡奈 KanaUpdate | 19dbe9c4 | 女王蜂特效 480→原版 205 | 是 |
| 格古巴 GugbaUpdate | 9afd6245 | 見下，改最多 | 是 |
| 亞普卡 YapkarUpdate | 095bb423 | 沒改（Sam 說職業屬性 7 不要動） | 是（重放一次） |
| 合併包 ComboUpdate | 79b94fd4 | 隨上面重建 | 沒放，只在專案裡 |

**全部原生程式仍只有模擬器／真實遊戲程式碼片段驗證，沒有在真實遊戲裡跑過。** Sam 實測是唯一最終驗證。
Sam 必須在每個資料夾重新執行 `join_apk.bat` 再安裝；有些資料夾還留著舊的已合併 APK，不能用。

---

## 1. 時間順序：發生了什麼

### 1.1 格古巴「每個技能都閃退」（2026-10-13 稍早，已修，已交付）
- 原因：格古巴「受到傷害」掛鉤（Entity.SkillDamage，0x10917DC）的洞穴把 **x8** 弄壞了，而遊戲在兩行之後還會用 x8。任何傷害 ≥1 就當機。
- 用真實遊戲程式碼（把遊戲的 SkillDamage 原樣放進模擬器、接上補丁後的洞穴）重現，修法是洞穴先存 x8 再還原。
- 教訓寫進記憶 `feedback-hook-registers`：洞穴必須把「掛鉤點之後遊戲還會讀的每個暫存器」原樣還回去。

### 1.2 小跟班技能紅色光暈（已修）
- 只當標記用的被動技能不該有 status 53（紅色攻擊力提升光環）；改成 status 0。status 15 = 自動回復光環。
- Sam 其實在說「技能出錯」，不是「發光」；我一開始誤會，他糾正後才去稽核小跟班技能本身（見 1.3）。

### 1.3 小跟班（buddy）技能稽核（沒找到問題）
- 查了遊戲怎麼掛小跟班技能：Status.EvaluateBuddy 把它放在技能陣列第 9 格（index 8）；EmitCheck 第 8 格用小跟班的 BOOST（我們是 100＝一定發動）而不是 SkillType.emitRatio。詳見記憶 `buddy-skill-mechanics`。
- 用真實 SkillDamage 加上所有標記技能測試，三個角色的暫存器與原版一致。
- 結論：資料與原生都沒有缺陷；當時 Sam 的具體症狀不明，後來他指出是格古巴點擊技能閃退（1.4）。

### 1.4 格古巴「奶奶的意志」按下去閃退（本次主因，已修）
- 症狀（Sam）：「格古巴的技能按下去閃退」→「奶奶的意志」。
- 一開始用真實遊戲程式碼模擬 EmitHopBreak、ShowHopBreakIcons，暫存器、堆疊、callee-saved 都乾淨，**沒重現**；因為模擬時把「播放特效」這個呼叫換成假的，所以漏掉真正的原因。
- **真正原因**（讀真實 libil2cpp.so 找到）：
  - 點擊時 `tapfx` 洞穴會播放 3 個特效，其中第 3 個是我自己用 `se_clone` 複製出來的 particleEffectSet 條目（聚集特效 271 + 重力音效），編號 **451**。
  - 遊戲的 EffectManager 實例池 `[mgr+0x70]` 是固定長度陣列：`mov w1,#0x1c3`（0x10D7DF0）＝ **451 格**；函式 0x10D80A8 檢查「長度 > 編號」，451 不通過，丟 IndexOutOfRange，遊戲閃退。
  - 原版 particleEffectSet 只有 450 筆，所以合法編號是 1～450。
- 修法：不再複製特效，`tapfx` 改播遊戲原有的 372（閃光）、270（聚集圈）、271（聚集光）。少了複製出來的重力音效（唯一外觀差異）。
  - `Kit/builders/make_gugba.py`：移除 `"effects"` 條目。
  - `Kit/tools/natives/gugba_native.py`：`FX_HOP_GATHER = 271`，註解寫明「池只有 1..450」。
  - `Kit/tools/terra_mod.py`：任何複製出來的 particle id > 450 傳進原生碼時直接拒絕建置。
  - `Kit/tools/tests/test_gugba.py`：斷言所有 fx id 在 1..450。
- 沒有證據顯示舊版（槽 4 版本）的點擊曾經在遊戲裡成功過，所以這個路徑從來沒被真實驗證過。

### 1.5 Sam 的要求：「全部角色重新檢查，有本來的就用本來的」
做了全角色資料稽核（2026-10-14）：把四個角色所有 mod 技能、職業、角色資訊的每個數值與原版資料庫比對。
- 不是原版的數值只剩這些（都有理由，已向 Sam 說明）：
  - 圖示槽 127–130、140、141：Sam 自己的圖，替換遊戲 8 個未使用的槽。
  - `capacity` 標記（原生程式用來找技能）。
  - 卡奈小跟班技能 successRate 4444（卡奈「直線夾擊」掛鉤用的標記）。
  - 卡奈隱藏技「愛心粉毒」life −1（永久修飾）。
  - 亞普卡職業 SkillAttrib 7（技能屬性 7 存在，但沒有原版職業用；Sam 決定**不要改**）。
- 改掉的：
  1. **卡奈女王蜂**特效 `@fx_queen`（我合成的 effectSet 條目 480 = 愛心追蹤 + 毒）→ 原版 **205**（愛心追蹤，跟魅惑子彈同一個）。`make_kana.py` 的 `effects` 移除。EffectSet 數量回到原版 479 / 450。
  2. **格古巴「毀滅一擊」**（隱藏技）successRate 4444 → **100**。原因：4444 是卡奈 `line` 掛鉤的標記；合併包裡卡奈的程式會把格古巴這招的 sx/sy 改掉。
  3. **格古巴滿級血量** HPmax 10287 → **9000**（Sam 先說 8000 後改 9000）。`make_gugba.py` 對該職業設 `HPmax = 9000`；職業雜湊由建置自動重算。
  4. 刪掉我自己留下的暫存資料夾 `TestGugbaNoNative`。
- 沒改：瑪庫里、亞普卡（稽核沒有問題）。

### 1.6 Sam 的要求：「節點暫存點的，都給我檢查仔細」＝ 掛鉤點的暫存器／旗標
Sam 要我把所有掛鉤點（hook site）周圍的暫存器檢查清楚。做了 4 件事：

**(a) `gen_live.py` 重寫**（產生 `Kit/tools/tests/live_regs.json`）
- 舊版只往後看 60 行、遇到無條件跳躍就停、不看分支目標、不看旗標，等於可能漏掉遊戲稍後才讀的暫存器。
- 新版：對被掛鉤的整個函式做反向存活分析（函式範圍取自 `Kit/analysis/methods.tsv`）；追蹤兩個分支目標；追蹤 NZCV 旗標；`bl` 讀取的參數暫存器依被呼叫函式的參數個數（methods.tsv 第 4 欄）推算；丟例外的輔助函式（0xBEF9E8、0xBEF8CC、0xBF06F4）視為不會返回；`ret`／尾呼叫要求所有 callee-saved；`br`（跳表）代表全部存活；多指令掛鉤點（只有格古巴 0x108EE64 這個 2 指令的）也正確處理；被取代指令本身寫入的暫存器不要求不變。
- 修正了 capstone 把 x29/x30 叫 fp/lr 造成的漏判。

**(b) 模擬器檢查加強**（`Kit/tools/tests/emu.py`）
- 檢查前把 x0–x28、d0–d31 都填「哨兵值」，NZCV 也填固定值。
- callee-saved（x19–x30、d8–d15）如果被改且遊戲還會用 → **直接失敗**。
- 旗標若遊戲還會讀且被改 → 失敗。
- 其他 caller-saved 暫存器被洞穴改了、而分析又不能證明已死亡 → 印出 `REVIEW` 行（需要人工確認）。
- 每個模組測試都顯示「ran on N of N hook caves」：四個模組目前都是 100% 覆蓋（格古巴 12/12、卡奈 6/6、瑪庫里 4/4、亞普卡 2/2）。

**(c) 人工核對全部 REVIEW 項目（共 24 個暫存器項）**
對照真實遊戲反組譯逐條看：全部是「檢查工具過度保守」的誤報，沒有任何一個是真問題。典型原因：
- 後面只有丟例外輔助函式（不會返回，參數不重要）。
- 被呼叫的函式其實不吃那個暫存器（例如 `bl 0xBFD180` 只吃 x0；`0x1ECE404` 讀 x0、x1、x8；ResetAroundBonus 的 x1 在被呼叫端被覆寫）。
- 函式回傳型別是 Vector2 / bool，不是檢查工具保守假設的 x0。
- 浮點參數 v1 在 SkillDamage 根本不是參數。

**(d) 新增 `check_caves.py`：靜態證明**
- 對每個模組的每個洞穴的每一條路徑（不是只跑測試走到的）追蹤：離開時 x19–x30、d8–d15 是否恢復入口值、sp 是否回到原位、sp 是否 16 位元組對齊。
- 以「遊戲之後不再讀的暫存器」和「被取代指令本身寫入的暫存器」作為允許差異。
- 唯一刻意的例外：卡奈 `force` 洞穴會把 w24 的 bit0 設成 1（AddModifier 的旗標），已在 `kana_native.py` 以 `m.intended_writes` 宣告。
- 用故意弄壞 `tapfx`（拿掉還原 x19）驗證它抓得到。現況 `TOTAL violations: 0`。

**(e) 其他靜態稽核**
- 所有掛鉤點旗標：**沒有任何一個掛鉤點的旗標在之後還會被讀**。
- 唯一的 2 指令取代（格古巴 0x108EE64 `cmp w8,#1; b.eq`）：全遊戲程式碼沒有任何分支跳進它的第二個指令。
- 洞穴區（七個「從沒執行的 Mono.Security 方法」）：每個區域的起點只被方法指標表引用一次；直接呼叫者全在 Mono.Security 內，往上追只到 `X509Certificate.CreateFromSignedFile`、`X509Certificate2.Import/ImportPkcs12`，它們本身沒有直接呼叫者（只能經虛擬／反射），遊戲不會呼叫憑證匯入。
- 格古巴用的 Entity+0x32c「被打次數」是遊戲自己在 SkillDamage 裡累加的欄位（不是我們自創）。

---

## 2. 我犯的錯（誠實紀錄）
1. 把「小跟班技能沒有改」誤解成發光（Sam 糾正）。
2. 模擬點擊流程時把播放特效的呼叫換成假的，因此漏掉特效池上限。**教訓：測試不要替身掉真實被呼叫者，要讀真實函式。**
3. 同時開兩個 build.sh 會互相覆蓋 `/root/charwork`（錯誤訊息 `cp: cannot create directory '/root/charwork/tools'`），那兩個產物作廢，改成序列建置。**一次只跑一個 build。**
4. 改了 `make_gugba.py`（HPmax 9000）卻沒先重跑 builder 就打包，第一次打出來還是 8000；後來用傾印的 ChrDatabase 發現並重打。**教訓：改 builder 後先重跑 `python3 make_x.py ../../XUpdate`，並檢查 `mods/*.json`，再 build，最後讀 `out/dump/ChrDatabase.json` 確認數值。**
5. 我曾在 Sam 要求「不要改成 0」之前準備改亞普卡 SkillAttrib；被他中斷後確認 builder 與 mods 檔都沒有被改動（仍是 7）。

---

## 3. 驗證怎麼做、結果如何（2026-10-14 最後一輪）
全部針對最終產物（格古巴 G9、卡奈 K8、合併包 C9）：
- `verify_apk.py`：APK 內的 `libil2cpp.so` ＝ 原版 + 剛好那些模組；標記與隱藏技能位置都存在 → ALL OK。
- 簽章：apksigner v1／v2／v3 驗證通過。
- `test_real_splice.py`：真實 SkillDamage 程式碼放進模擬器，原版與補丁版逐筆比對（含「所有標記都在受害者和攻擊者身上」）→ 0 MISMATCH。
- `test_independence.py`：15 種子集合，各模組只改自己的位元組 → ALL 15 SUBSETS OK。
- 四個模組單元測試：GUGBA OK / KANA OK / MACURI OK / YAPKAR OK。
- `check_caves.py`：0 violations。
- 傾印資料庫確認：EffectSet 479 / 450、格古巴 HPmax 9000、沒有 effID > 479、successRate 4444 只剩卡奈小跟班那一個。
- release 切片（每片 25,000,000 位元組）接回後的 SHA256 與建置輸出一致；電腦端逐檔比對檔名與大小，四個資料夾全部相符。

**沒有做、因此未驗證：** 真實遊戲內執行；Windows 上實跑 join_apk.bat；電腦端合併後的 SHA256（電腦端 Linux 環境沒啟動，無法在那邊算）。

---

## 4. 檔案地圖（改了哪些）
- `Kit/builders/make_gugba.py`：移除 effects 條目；HPmax 9000；毀滅一擊 successRate=100。
- `Kit/builders/make_kana.py`：女王蜂 effID=205；移除 effects 條目。
- `Kit/tools/natives/gugba_native.py`：FX_HOP_GATHER=271（取代 `{FX_fx_tap_gather}`）。
- `Kit/tools/natives/kana_native.py`：加 `m.intended_writes = {"force": ["x24"]}`（行為不變）。
- `Kit/tools/terra_mod.py`：複製的 particle id > 450 → 拒絕建置。
- `Kit/tools/tests/`：`gen_live.py`（重寫）、`emu.py`（加強）、`check_caves.py`（新）、`live_regs.json`（重新產生）、`test_gugba.py`（fx id 斷言）、`test_real_splice.py`（含標記全開情境）。
- `Kit/BUILD.md`：驗證步驟加第 4 項「掛鉤安全」；特效池上限警語。
- 各 `*Update/mods/*.json`、`release/`：已重新產生／重新切片。
- 記憶（專案共享）：`feedback-effect-pool-limit`、`feedback-original-first`、`buddy-skill-mechanics`、`feedback-hook-registers`。

---

## 5. 日後出問題怎麼查（流程）
1. 問 Sam：哪個角色、哪個技能、做了什麼動作、閃退還是沒效果、有沒有遊戲 log。
2. 先確認他安裝的是新合併的 APK（SHA256 開頭見第 0 節），不是舊的已合併檔。
3. 閃退 → 找該動作用到的原生洞穴（`Kit/tools/natives/<名>_native.py` 檔頭有掛鉤點清單）。
   - 先看有沒有播特效／用到固定大小陣列／遊戲內部欄位偏移。
   - 用 `Kit/analysis/methods.tsv` 查地址對應方法；用 `capstone` 反組譯原版 `Kit/input` 重建的 libil2cpp.so。
   - **不要替身掉被呼叫的遊戲函式**；寫一個把真實函式放進 unicorn 的小測試（範例：`hop_real.py`、`icons_real.py`、`tests/test_real_splice.py`）。
4. 修改原生程式後必跑：`test_<名>.py`、`gen_live.py <原版so>`、`check_caves.py <原版so>`、`test_real_splice.py`、`test_independence.py`，再建置並跑 `verify_apk.py`。
5. 改 builder → 重跑 builder → 檢查 mods JSON → 一次只跑一個 build → 讀 `out/dump` 驗證數值 → 重新切片（`split -b 25000000 -d -a 2`）→ 更新 `release/SHA256.txt` → 向 Sam 報告並等他同意再放進電腦（路徑 `TB\TerraMod\1013V1\pack_en\TerraModUpdate\<名>Update\release`，單次提交 ≤100MB，單檔 ≤30MB）。

## 6. 規則提醒（Sam）
- 回覆用繁體中文；檔名英文；做任何決定前先問他；放進他電腦要他同意（他說「放進去」才放）。
- 有遊戲原本的東西就用原本的，不要自創複製；不要敷衍、不要便宜行事；每項改動要有紀錄與驗證。
- 專案沒有 GitHub 倉庫；所有檔案放 `/mnt/project-files/TerraModUpdate`。

## 7. 還開著的事項
- Sam 實測四個角色（特別是格古巴點擊「奶奶的意志」）並回報。
- 格古巴點擊少了複製出來的重力音效；如果 Sam 想要音效，可改播現有的 350「final_heavy_01」（音效 gravity_final，畫面較大，沒實際看過）。需 Sam 決定。
- 節奏頭槌「一場戰鬥」在第二波是否重新從 1.0 開始：遊戲內未驗證。
- 技能說明文字草稿（`skill_text_draft_*.md`）尚未套用，需 Sam 確認。
- 亞普卡職業 SkillAttrib 7 維持原狀（Sam 決定）。

---
## 8. Addendum 2026-10-14 (after Sam's in-game test of Gugba): tap skill fixes
See work_log.md "night 7". Summary: (a) removed particle 270 (chain-link icon) from the tap animation; (b) enemy DEF -100% was capped to about -30% by the game's Entity.limitModifiedStatus (cap constant 0.3 at 0x204F1E4); new hook 0x1078E68 skips the cap for entities carrying the DEF-break modifier (mark 4810) and the modifier is now -99%; (c) new real-code test `Kit/tools/tests/test_limit_real.py`. Gugba APK 602054cf, Combo 1c53acd7; other three characters unchanged. Not yet on Sam's PC.
Debug tip: if DEF still looks capped, check the hook at 0x1078E68 is present (verify_apk) and the skill with mark 4810 has spower -99 in out/dump/SkillData.json.
