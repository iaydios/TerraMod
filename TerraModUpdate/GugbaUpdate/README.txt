================ 繁體中文 ================
GugbaUpdate：格古巴・Λ (1291) + 夥伴 月魂 (500)
這個資料夾只包含這一個角色的所有東西（技能資料、原生補丁、圖示、圖片），可單獨打包成自己的 APK，也可以和別的 Update 資料夾組合進同一個 APK（見上層 組合說明）。

技能：
別擋路：不變
威士忌：夾擊 30%，每杯隨機一項能力+25%（每項最多4杯，共16杯），受到任何傷害全部歸零重算
地震斬：夾擊 30%，橫3列，攻擊力×3.0＋重力（可被抵抗）
格古巴大地震：夾擊或連鎖 5%，全體敵人×1.0 連5下，隨機3種異常，洗牌位置
夥伴 月魂「奶奶的意志」：點擊，每場一次；敵人防禦−99%，下一次夾擊變重拳（倍率=被打次數，上限20）；被打滿20次說「夠了…」

自己打包：先看上層 Kit\BUILD 說明；基本上只要雙擊「build.bat」（需要 WSL；請保持 TerraModUpdate 整個資料夾完整，不要只複製這一個資料夾）。
成品：out\TerraBattle-mod.apk、out\reTB-Host-mod.apk、out\SHA256.txt（遊戲 APK 簽名與以前相同，可直接覆蓋安裝；先裝 Host 再裝遊戲）。
release\：已經打包好的分割檔，雙擊 join_apk.bat 合併並顯示 SHA256。
圖片：make_gdresources_tar.bat 只把 gdresources_new 的新圖打成 gdresources_new.tar（不碰你的原檔）；沒有新圖的角色表示你已安裝的圖片仍然有效。
注意：原生補丁只有模擬器驗證，尚未在遊戲內實測。

================ English ================
GugbaUpdate: Gugba Λ (1291) + buddy Moon Soul (500)
This folder holds everything of this one character (skill data, native patch, icons, images). It builds its own standalone APK, and can also be combined with other Update folders into one APK (see the combo notes one level up).

Skills:
Out of the Way: unchanged
Whiskey: pincer 30%, each drink +25% to a random stat (4 per stat, 16 in all); any damage taken resets everything
Quake Slash: pincer 30%, 3 rows, 3.0x ATK + gravity (resistible)
Rhythm Headbutt: pincer only 30%, single target, non-elemental physical 1.0x ATK; every use adds +1.0x ATK, no limit within the battle (counter per character, restarts at 1.0 next battle)
Buddy Moon Soul 'Grandma's Will': tap, once per battle; foes' DEF -99%, the next pincer becomes a fist (multiplier = times hit, max 20); says 'Enough...' at 20 hits

Build it yourself: double-click "build.bat" (needs WSL; keep the whole TerraModUpdate folder together, do not copy only this folder).
Results: out\TerraBattle-mod.apk, out\reTB-Host-mod.apk, out\SHA256.txt (same signing key as before, installs over the old one; install the Host first, then the game).
release\: the prebuilt split files; double-click join_apk.bat to join them and show the SHA256.
Images: make_gdresources_tar.bat packs only the new images of gdresources_new into gdresources_new.tar (your own files are untouched); a character without new images keeps the images you already installed.
Note: the native patches are emulator-verified only and have not been tested in the game yet.

================ Français ================
GugbaUpdate : Gugba Λ (1291) + compagnon Moon Soul (500)
Ce dossier contient tout ce qui concerne ce personnage (données de compétences, patch natif, icônes, images). Il produit son propre APK autonome et peut aussi être combiné avec d'autres dossiers Update dans un seul APK.
Compiler : double-cliquer sur « build.bat » (WSL requis ; garder tout le dossier TerraModUpdate ensemble). Résultats dans out\. join_apk.bat assemble les parties de release\. make_gdresources_tar.bat emballe uniquement les nouvelles images.
Remarque : les patchs natifs ne sont vérifiés que par émulateur, pas encore testés dans le jeu.
