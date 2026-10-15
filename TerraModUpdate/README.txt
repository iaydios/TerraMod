================ 繁體中文 ================
TerraModUpdate：四個 Λ 角色（馬卡利 1289／卡奈 1290／格古巴 1291／亞普卡? 1292）的原生補丁已全部重寫，每個角色的原生完全獨立。

資料夾
  MacuriUpdate / KanaUpdate / GugbaUpdate / YapkarUpdate   每個角色一個資料夾，可各自打包成自己的 APK
  ComboUpdate    編輯 combo.txt（每行一個 Update 資料夾名稱，任意組合），雙擊 build.bat → 同一個 APK 裝進所選的所有角色
  Kit            共用的打包工具（tools、base、input 原版 APK 分割檔、scripts、builders、tests）；說明在 Kit\BUILD.md
  _archive_old    舊設計（共用掛鉤）留下的東西，只供參考，去處見 _archive_old\where_things_went.md
  work_log.md    整個過程的紀錄
每個角色資料夾內：mods\（技能/角色資料）、art\、gdresources_new\、build.bat、join_apk.bat、make_gdresources_tar.bat、release\（已打包好的分割 APK）、README.txt。
請保持 TerraModUpdate 整個資料夾完整（各資料夾的 bat 會呼叫 Kit）。
安裝順序：先裝 Host（reTB-Host-mod.apk），再裝遊戲（TerraBattle-mod.apk，簽名與以前相同，可直接覆蓋）。
重要：所有原生補丁只在模擬器驗證過，尚未在遊戲內實測。

================ English ================
TerraModUpdate: the native patches of the four Lambda characters (Ma'curi 1289 / Kana 1290 / Gugba 1291 / Y'apkar? 1292) were rewritten; every character's native code is fully independent.
  MacuriUpdate / KanaUpdate / GugbaUpdate / YapkarUpdate   one folder per character, each builds its own APK
  ComboUpdate    edit combo.txt (one Update folder name per line, any subset), double-click build.bat -> ONE APK with all selected characters
  Kit            shared build tools (tools, base, input = original APK parts, scripts, builders, tests); see Kit\BUILD.md
  _archive_old    leftovers of the old shared-hook design, reference only; see _archive_old\where_things_went.md
  work_log.md    log of the whole process
Keep the whole TerraModUpdate folder together (the bat files call Kit).  Install order: Host APK first, then the game APK (same signing key as before).
Important: all native patches are emulator-verified only, not tested in the game yet.

================ Français ================
TerraModUpdate : les patchs natifs des quatre personnages Lambda ont été réécrits, chacun est totalement indépendant.
Un dossier par personnage (APK autonome) ; ComboUpdate\combo.txt pour combiner n'importe quels personnages dans un seul APK ; Kit = outils ; _archive_old = anciens restes (référence seulement).
Garder tout le dossier ensemble. Installer d'abord le Host, puis le jeu. Les patchs natifs ne sont vérifiés que par émulateur.
