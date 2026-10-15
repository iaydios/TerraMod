================ 繁體中文 ================
MacuriUpdate：馬卡利・Λ (1289) + 夥伴 機械手臂 (498)
這個資料夾只包含這一個角色的所有東西（技能資料、原生補丁、圖示、圖片），可單獨打包成自己的 APK，也可以和別的 Update 資料夾組合進同一個 APK（見上層 組合說明）。

技能：
機械生命（裝備）：每回合受到的第一次傷害無效
槍塚：夾擊或連鎖 20%，攻擊力×1.0，連續3下
威逼（裝備）：對生命低於33%的敵人傷害×1.5（萬槍除外）
萬槍：夾擊 5%，10000傷害（不變）
夥伴 機械手臂「渴血」：每次造成傷害回復 攻擊力×0.5

自己打包：先看上層 Kit\BUILD 說明；基本上只要雙擊「build.bat」（需要 WSL；請保持 TerraModUpdate 整個資料夾完整，不要只複製這一個資料夾）。
成品：out\TerraBattle-mod.apk、out\reTB-Host-mod.apk、out\SHA256.txt（遊戲 APK 簽名與以前相同，可直接覆蓋安裝；先裝 Host 再裝遊戲）。
release\：已經打包好的分割檔，雙擊 join_apk.bat 合併並顯示 SHA256。
圖片：make_gdresources_tar.bat 只把 gdresources_new 的新圖打成 gdresources_new.tar（不碰你的原檔）；沒有新圖的角色表示你已安裝的圖片仍然有效。
注意：原生補丁只有模擬器驗證，尚未在遊戲內實測。

================ English ================
MacuriUpdate: Ma'curi Λ (1289) + buddy Mech Arm (498)
This folder holds everything of this one character (skill data, native patch, icons, images). It builds its own standalone APK, and can also be combined with other Update folders into one APK (see the combo notes one level up).

Skills:
Mechanical Life (equip): the first damage taken each turn is nullified
Spear Tomb: pincer or chain 20%, 1.0x ATK, 3 hits
Coercion (equip): x1.5 damage against foes below 33% HP (Ten Thousand Spears excepted)
Ten Thousand Spears: pincer 5%, 10000 damage (unchanged)
Buddy Mech Arm 'Bloodthirst': every damaging hit heals 0.5x ATK

Build it yourself: double-click "build.bat" (needs WSL; keep the whole TerraModUpdate folder together, do not copy only this folder).
Results: out\TerraBattle-mod.apk, out\reTB-Host-mod.apk, out\SHA256.txt (same signing key as before, installs over the old one; install the Host first, then the game).
release\: the prebuilt split files; double-click join_apk.bat to join them and show the SHA256.
Images: make_gdresources_tar.bat packs only the new images of gdresources_new into gdresources_new.tar (your own files are untouched); a character without new images keeps the images you already installed.
Note: the native patches are emulator-verified only and have not been tested in the game yet.

================ Français ================
MacuriUpdate : Ma'curi Λ (1289) + compagnon Mech Arm (498)
Ce dossier contient tout ce qui concerne ce personnage (données de compétences, patch natif, icônes, images). Il produit son propre APK autonome et peut aussi être combiné avec d'autres dossiers Update dans un seul APK.
Compiler : double-cliquer sur « build.bat » (WSL requis ; garder tout le dossier TerraModUpdate ensemble). Résultats dans out\. join_apk.bat assemble les parties de release\. make_gdresources_tar.bat emballe uniquement les nouvelles images.
Remarque : les patchs natifs ne sont vérifiés que par émulateur, pas encore testés dans le jeu.
