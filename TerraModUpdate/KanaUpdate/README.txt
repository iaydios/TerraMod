================ 繁體中文 ================
KanaUpdate：卡奈・Λ (1290) + 夥伴 心動左輪 (499)
這個資料夾只包含這一個角色的所有東西（技能資料、原生補丁、圖示、圖片），可單獨打包成自己的 APK，也可以和別的 Update 資料夾組合進同一個 APK（見上層 組合說明）。

技能：
心跳加速：不變（移動她所在的夥伴得到一回合全能力提升）
病毒子彈：夾擊或連鎖 40%，中毒（2.0），毒發時卡奈回血
反差萌（裝備）：受到魔法傷害時傷害歸零並讓對方染上粉毒；物理不處理；已移除50%迴避
女王蜂：夾擊或連鎖 10%，只對敵人施加粉毒
夥伴 心動左輪「心動病毒」：直線夾擊；敵人技能/攻擊發動機率 −50%（3回合）

自己打包：先看上層 Kit\BUILD 說明；基本上只要雙擊「build.bat」（需要 WSL；請保持 TerraModUpdate 整個資料夾完整，不要只複製這一個資料夾）。
成品：out\TerraBattle-mod.apk、out\reTB-Host-mod.apk、out\SHA256.txt（遊戲 APK 簽名與以前相同，可直接覆蓋安裝；先裝 Host 再裝遊戲）。
release\：已經打包好的分割檔，雙擊 join_apk.bat 合併並顯示 SHA256。
圖片：make_gdresources_tar.bat 只把 gdresources_new 的新圖打成 gdresources_new.tar（不碰你的原檔）；沒有新圖的角色表示你已安裝的圖片仍然有效。
注意：原生補丁只有模擬器驗證，尚未在遊戲內實測。

================ English ================
KanaUpdate: Kana Λ (1290) + buddy Heart-Throb Revolver (499)
This folder holds everything of this one character (skill data, native patch, icons, images). It builds its own standalone APK, and can also be combined with other Update folders into one APK (see the combo notes one level up).

Skills:
Heartbeat: unchanged (an ally moved with her gets a 1-turn all-stats boost)
Virus Bullet: pincer or chain 40%, poison (2.0), each tick heals Kana
Contrast (equip): magic damage against her becomes 0 and leaves the attacker with Pink Heart Poison; physical untouched; the 50% evade is gone
Queen Bee: pincer or chain 10%, Pink Heart Poison on enemies only
Buddy Heart-Throb Revolver 'Heart-Throb Virus': pincer line; foe skill/attack rate -50% (3 turns)

Build it yourself: double-click "build.bat" (needs WSL; keep the whole TerraModUpdate folder together, do not copy only this folder).
Results: out\TerraBattle-mod.apk, out\reTB-Host-mod.apk, out\SHA256.txt (same signing key as before, installs over the old one; install the Host first, then the game).
release\: the prebuilt split files; double-click join_apk.bat to join them and show the SHA256.
Images: make_gdresources_tar.bat packs only the new images of gdresources_new into gdresources_new.tar (your own files are untouched); a character without new images keeps the images you already installed.
Note: the native patches are emulator-verified only and have not been tested in the game yet.

================ Français ================
KanaUpdate : Kana Λ (1290) + compagnon Heart-Throb Revolver (499)
Ce dossier contient tout ce qui concerne ce personnage (données de compétences, patch natif, icônes, images). Il produit son propre APK autonome et peut aussi être combiné avec d'autres dossiers Update dans un seul APK.
Compiler : double-cliquer sur « build.bat » (WSL requis ; garder tout le dossier TerraModUpdate ensemble). Résultats dans out\. join_apk.bat assemble les parties de release\. make_gdresources_tar.bat emballe uniquement les nouvelles images.
Remarque : les patchs natifs ne sont vérifiés que par émulateur, pas encore testés dans le jeu.
