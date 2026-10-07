# TerraMod

**English summary:** A toolchain for adding *new content* (characters, DNA recodes, skills, companions/buddies, images) to Terra Battle (Unity 2017.4, IL2CPP, arm64) running against the reTB private server (reTBHost). Content is written as JSON specs. The tools re-encode the game databases inside `data.unity3d` byte-exactly, add the images to the asset index, optionally apply small opt-in native patches to `libil2cpp.so`, patch the reTBHost server (Chaquopy/FastAPI) to match, and sign both APKs. Every step verifies itself: it round-trips the originals, re-reads its output, and checks the expected bytes before patching.

> 本專案**不含**任何遊戲本體、APK、遊戲資料或美術素材。使用者必須自備合法取得的檔案。

---

## 能做什麼

| 功能 | 說明 |
|---|---|
| 新角色 / 新職業 | 從現有角色複製後修改名稱、數值、技能、立繪 ID、個人故事（6 語系） |
| DNA Recode | 指定來源角色、金幣、3 種素材、2 隻素材角色 |
| 新技能 | 從現有技能複製，修改 `SkillType` 任意欄位 |
| 新小跟班 (Buddy) | 專屬角色、稀有度、數值、技能、圖片 |
| 伺服器規則 | 唯一 / 上鎖（不能賣、不能當素材）、擁有某角色後下一次金幣抽獎保底 |
| 圖片 | 棋子 / 立繪 / 個人檔案 / 小跟班大圖與縮圖，產生可下載的 gdresources 檔 |
| 原生補丁（選用） | `random_power`：加權隨機傷害倍率；`star_range`：米字形範圍 |
| 存檔工具 | 直接設定 reTBHost 匯出存檔中角色的等級 |

範例 mod：`mods/10_macuri_lambda.json`（馬卡利・Λ）和 `mods/11_macuri_mech_arm.json`（馬卡利的機械手臂）。

## 需求

- Linux 或 WSL；Python **3.13**（必須與 reTBHost 內建的 Chaquopy Python 相同，因為要重新編譯 `.pyc`）
- `pip install -r requirements.txt`
- Java（`keytool`、`apksigner`），以及 Android build-tools 的 `zipalign` 與 `apksigner.jar`，放在 `build-tools/`（或用環境變數 `TERRAMOD_BT` 指定）
- 只有用到原生補丁時才需要 `llvm-mc` 和 `llvm-objcopy`
- 原生小工具：`sh native/build_native.sh`（編譯 `tools/libetc2.so`、`tools/liblz4.so`）

## 自備檔案（放在 `input/`）

| 檔案 | 從哪裡來 |
|---|---|
| `TerraBattle.apk` | 原始 reTB 遊戲 APK（arm64） |
| `reTB-Host.apk` | 原始 reTBHost APK |
| `game_data/` | reTBHost 解出的遊戲資料 `extracted-gamedata/game_data/`（需要 `ChrDatabase.json`、`SkillData.json`、`EffectSet.json`、`BuddyDatabase.json`）。建置時會先驗證這些 JSON 能逐位元組重建原 APK 內的資料，對不上就停止 |
| `gdresources/` | 自己裝置上的 gdresources（拿來當圖片模板） |
| `art/` | 新圖片 PNG / JPG（見 `images.json`） |

## 流程

```sh
sh native/build_native.sh   # 第一次
sh build_all.sh             # 產出 out/TerraBattle-mod.apk、out/reTB-Host-mod.apk、out/gdresources/
```

`build_all.sh` 依序執行三個步驟，也可以分開跑：

1. **遊戲 APK**：`tools/terra_mod.py build`
   - 讀取 `mods/*.json`，依檔名順序套用：技能 → 小跟班 → 角色
   - 重算 job / buddy hash，把新圖片加進內建的 AssetVersions 索引
   - 套用 spec 中 `"native"` 列出的補丁，最後對齊並簽名
   - `--dump` 會輸出修改後的資料庫，下一步要用
2. **伺服器 APK**：`tools/host_mod.py`
   - 寫入新角色、Recode、EXP 上限和 patchData，再依 `server/buddies.json` 加上小跟班規則
   - 重新編譯 `.pyc` 後簽名
3. **圖片**：`tools/make_images.py`
   - 依 `images.json` 用同名長度的原始檔當模板，產生加密的 `.bin`
   - 產出的資料夾合併進玩家的 gdresources，打包成 tar 後在 reTBHost 匯入

可選：`tools/edit_save.py` 修改 reTBHost 匯出存檔的角色等級。

> 兩個 APK 的簽名與官方不同，玩家必須先在 reTBHost **匯出帳號**，再移除原版、安裝模組版，最後匯入 tar 和存檔。

## 新增內容

撰寫規格見 [`docs/MOD_SPEC.md`](docs/MOD_SPEC.md)。開始前務必讀 [`docs/INTERNALS.md`](docs/INTERNALS.md) 的「陷阱」一節，裡面每一條都曾造成卡死或圖片空白。

## 目錄

```
tools/            建置工具（terra_mod / host_mod / make_images / edit_save 與函式庫）
tools/analysis/   逆向分析輔助（符號表、反組譯、呼叫圖、字串常量、貼圖匯出）
native/           libetc2 / liblz4 編譯腳本
mods/             mod 規格 JSON（每個檔案一組內容）
images.json       圖片產生清單（make_images 用）
art/              你的圖片（不納入 repo）
server/           伺服器端小跟班規則
docs/             規格與內部機制文件
```

## 授權

程式碼以 MIT 授權釋出（見 `LICENSE`）。Terra Battle 及其素材的權利屬於原權利人；本專案僅供私人伺服器的同好研究使用，請勿散布遊戲本體或素材。
