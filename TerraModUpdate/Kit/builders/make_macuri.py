"""MacuriUpdate: Ma'curi Lambda (1289) + buddy Mech Arm (498).  python3 make_macuri.py <MacuriUpdate folder>"""
import sys
from common import *

out = sys.argv[1]
S = Skills()
MARKER = shipped(3857)          # equip-style passive (kind 5), the base of every mark-only skill.  Its status must be 0: status 53 makes the game show the red power-up glow on the portrait for the whole battle

thirst = S.add("thirst", MARKER, tx("渴血", "Bloodthirst", "渇血"),
               tx("墜毀無畏艦的裝甲鑄成的巨臂，吞下戰場的每一滴血，仍嫌不夠。每次造成傷害，回復攻擊力一半的生命。",
                  "A great arm cast from the armor of a crashed dreadnought, it drinks every drop of blood on the battlefield and is never sated. Each time damage is dealt, heals half of the wielder's ATK.",
                  "墜落した無畏艦の装甲から鋳造された巨腕は、戦場の血を一滴残らず飲み干してもなお足りない。ダメージを与えるたび、攻撃力の半分だけHPを回復する。"),
               iconNo=128, capacity=5140, emitRatio=0, status=0)
tomb = S.add("spear_tomb", shipped(3853), None,
             tx("長槍所過之處，屍骸與槍林連成一片墓地。夾擊或連鎖時，連續貫穿周圍的敵人3次。", "Where the lances pass, corpses and a forest of spears join into one graveyard. On a pincer or chain, impales surrounding foes 3 times in a row.",
                "槍の通った後には、屍と槍の林が連なり一面の墓地となる。挟撃または連鎖時、周囲の敵を3回連続で貫く。"),
             capacity=5110, condition=0, emitRatio=20, power=1.0)
coer = S.add("coercion", MARKER, tx("威逼", "Coercion", "威圧"),
             tx("他踏過千百座戰場，一眼便知誰已走到盡頭。對生命低於33%的敵人，傷害提高50%（萬槍除外）。", "He has crossed a thousand battlefields and knows at a glance who has reached the end. Deals 50% more damage to foes below 33% HP (Ten Thousand Spears excepted).",
                "幾千もの戦場を踏み越えた彼は、誰が終わりに近いか一目で見抜く。HPが33%未満の敵へのダメージが50%上がる（一万本槍を除く）。"),
             iconNo=3, capacity=5120, emitRatio=0, status=0)
spears = S.add("ten_thousand_spears", shipped(3855), None, tx("凝神出擊造成10000點傷害", "Focus strike deals 10000 damage", "集中の一撃で10000ダメージ"), capacity=5130)
life = S.add("mech_reflect", base(47), tx("機械反射", "Mechanical Reflect", "機械反射"),
             tx("機械手臂可是很記仇的，絕不放過任何一個對馬卡利動手的敵人。被夾擊時，對所有夾擊他的敵人以2.5倍攻擊力的無屬性物理傷害反擊，受到致命傷害時會以1點生命撐住；若反擊擊倒敵人，生命全數回復，本場戰鬥造成的傷害提高25%，可無限疊加；沒擊倒的話，下一次受到攻擊就會倒下。",
                "The mechanical arm holds a grudge and spares no enemy that strikes Ma'curi. When pincered, counters every enemy that pincered him with 2.5x ATK non-elemental physical damage, and a lethal hit leaves 1 HP. If the counter defeats the enemy, HP is fully restored and damage dealt for the rest of the battle rises by 25%, stacking without limit; if it does not, the next hit is fatal.",
                "機械の腕は恨みを忘れず、マクリに手を出した敵を一体も逃さない。挟撃された時、挟撃した敵すべてに攻撃力の2.5倍の無属性物理ダメージで反撃し、致命傷を受けてもHP1で踏みとどまる。反撃で敵を倒すとHPが全回復し、この戦闘中の与ダメージが25%上がる（何度でも重ねがけ可）。倒せなければ、次の攻撃で倒れる。"),
             capacity=5101, emitRatio=100, power=2.5)
S.add("mech_reflect_kills", base(1960), tx("機械反射（擊殺數）", "Mechanical Reflect (kills)", "機械反射（撃破数）"), NONE)   # hidden id+1: inert, its modifier value = kills made by the counter this battle


mod = {
    "_note": "Ma'curi Lambda (1289), self-contained native module macuri_native.  Marks: 5101 Mechanical Reflect (buddy 498, the game's Counterattack 47 with power 2.5, +1 hidden kill counter), 5110 Spear Tomb, "
             "5120 Coercion, 5130 Ten Thousand Spears, 5140 Bloodthirst (character skill 1).",
    "skills": S.items,
    "buddies": [buddy(498, life)],
    "characters": [character(1289, 5166, [thirst, tomb, coer, spears])],
    "icons": [{"icon_no": 128, "file": "art/skill_icon_128.png"}],
    "asset_db": {"Pieces": [{"id": 3001, "w": 106, "h": 106, "ver": 131}], "Illusts": [{"id": 3001, "w": 878, "h": 1024, "ver": 131}],
                 "BuddyThumbs": [{"id": 521, "w": 106, "h": 106, "ver": 131}],
                 "BuddyImages": [{"id": 0, "name": "buddy_521a", "w": 367, "h": 605, "ver": 131}, {"id": 0, "name": "buddy_521b", "w": 235, "h": 327, "ver": 131}]},
    "native": ["macuri_native"],
}
sb = [server_buddy(498, 1289, EX["buddies"]["498"]["NameString"])]
write_mod(out, "10_macuri.json", mod, sb, {"name": "Macuri", "chr_ids": [1289], "native": ["macuri_native"], "icons": [128]})
