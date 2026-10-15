"""GugbaUpdate: Gugba Lambda (1291) + buddy Moon Soul (500).  python3 make_gugba.py <GugbaUpdate folder>"""
import sys
from common import *

out = sys.argv[1]
S = Skills()
MARKER = shipped(3857)

way = S.add("out_of_my_way", shipped(3864), None,
            tx("橫衝直撞，擋路的全被撞開。可推動所有方塊（Boss除外）。",
               "He charges through everything, and whatever stands in the way gets knocked aside. Can push every block except Bosses.",
               "猪突猛進、道を塞ぐものはすべて弾き飛ばす。ボス以外のすべてのブロックを押せる。"),
            spower=0.0)

whiskey = S.add("whiskey", shipped(3865), None,
                tx("私釀威士忌，越喝越有勁。夾擊時發動：每杯隨機讓攻擊、防禦、魔攻、魔防其中一項提升25%（每項最多4杯），受到任何傷害就全部歸零。",
                   "Home-brewed whiskey: the more he drinks, the stronger he gets. On a pincer: each drink raises one random stat of ATK, DEF, MATK or MDEF by 25% (4 drinks per stat). Any damage taken resets them all.",
                   "自家製ウイスキー、飲むほどに力が湧く。挟撃時に発動。1杯ごとに攻撃・防御・魔攻・魔防のいずれかがランダムで25%上昇（各4杯まで）。ダメージを受けると全てリセット。"),
                iconNo=140)
for sid in (3866, 3867, 3868, 3869):                                           # hidden id+1..+4: ATK% / DEF% / MATK% / MDEF% modifiers whose value the native sets
    S.add("whiskey_%d" % (sid - 3865), shipped(sid))

slash = S.add("quake_slash", shipped(3870), tx("地震斬", "Quake Slash", "地震斬り"),
              tx("一劍劈下，大地隨之崩裂。橫掃3列敵人，並使其受到重力壓制。", "One downward stroke and the earth splits open. Sweeps 3 rows and weighs the foes down with gravity.",
                 "剣を振り下ろせば、大地が裂ける。横3列を薙ぎ払い、重力で押さえつける。"),
              kind=3, status=38, spower=2.0, successRate=75, life=2, power=3.0, emitRatio=30)

headbutt = S.add("rhythm_headbutt", base(1677), tx("節奏頭槌", "Rhythm Headbutt", "リズム頭突き"),
                 tx("重現在酒館的愚鈍舞步，在旁人看起來是玩笑，但在敵人的眼裡不是如此。夾擊時發動：造成1.0倍攻擊的物理傷害，每發動一次傷害增加1.0倍，同一場戰鬥內沒有上限，下一場戰鬥歸零重新開始。",
                    "He re-enacts the clumsy dance steps from the tavern. To bystanders it looks like a joke, but not to the enemy. On a pincer: deals physical damage equal to 1.0x ATK, and every use adds another 1.0x ATK with no limit for the rest of the battle. The next battle starts again at 1.0x.",
                    "酒場での不格好なステップを再現する。周りには冗談に見えるが、敵の目にはそうは映らない。挟撃時に発動。攻撃力の1.0倍の物理ダメージを与え、使うたびにさらに1.0倍ずつ増える。同じ戦闘中は上限なし、次の戦闘では最初に戻る。"),
                 tx("單體", "Single", "単体"),
                 condition=1, emitRatio=30, power=1.0, spower=0.0, effID=99, capacity=4830, iconNo=34)
S.add("rhythm_headbutt_count", base(1960), tx("節奏頭槌（連擊數）", "Rhythm Headbutt (count)", "リズム頭突き（回数）"), NONE)   # hidden id+1: inert, its modifier value = uses so far this battle

tap = S.add("grandma_tap", shipped(3871), tx("奶奶的意志", "Grandma's Will", "おばあちゃんの意志"),
            tx("金孫，不能光被挨打呀~點擊格古巴：敵人的防禦降低，下一次夾擊化為毀滅一擊，被打越多次，傷害越高。每場戰鬥限一次。",
               "Dear grandson, you can't just stand there taking hits~ Tap Gugba: foes' DEF is reduced and the next pincer becomes a Doom Strike that hits harder the more times he has been hit, the harder it hits. Once per battle.",
               "孫よ、殴られてばかりじゃいけないよ〜。ググバをタップ：敵の防御が低下し、次の挟撃は滅びの一撃に変わる。殴られた回数が多いほど強い。1戦闘に1回だけ。"),
            iconNo=141, capacity=4806)
fist = shipped(3872)
S.add("grandma_fist", fist, tx("奶奶的意志（毀滅一擊）", "Grandma's Will (Doom Strike)", "おばあちゃんの意志（滅びの一撃）"), NONE, power=1.0, successRate=100)      # was 4444 (a Kana line mark carried over): that value would make Kana's line hook rewrite this skill in a combo build
S.add("grandma_used", shipped(3873), tx("奶奶的意志（已發動）", "Grandma's Will (used)", "おばあちゃんの意志（発動済み）"), NONE, status=0)
S.add("grandma_stun", shipped(3874), tx("奶奶的意志（暈眩）", "Grandma's Will (Stun)", "おばあちゃんの意志（気絶）"), NONE)
S.add("grandma_enough", MARKER, tx("夠了…", "Enough…", "もう、たくさんだ…"), NONE, iconNo=141, capacity=4809, emitRatio=0, status=0)
S.add("grandma_defdown", shipped(3867), tx("奶奶的意志（破防）", "Grandma's Will (Break)", "おばあちゃんの意志（破防）"), NONE,
      spower=-99.0, capacity=4810)

gugba_chr = character(1291, 5168, [way, whiskey, slash, headbutt])
gugba_chr["raw"]["jobs"][0]["HPmax"] = 9000          # Sam 2026-10-13: max-level HP 9000 (was 10287; 8000 asked first, then 9000)

bd = EX["buddies"]["500"]
mod = {
    "_note": "Gugba Lambda (1291), self-contained native module gugba_native.  Marks: 4801 Out of the Way, 4802 Whiskey (+1..+4 hidden stat skills), 4830 Rhythm Headbutt "
             "(+1 hidden use counter), buddy 500 Grandma's Will: tap 4806 (+1 fist 4805, +2 used 4807, +3 stun 4808, +4 'Enough...' 4809, +5 DEF-99% 4810).",
    "skills": S.items,
    "buddies": [buddy(500, tap)],
    "characters": [gugba_chr],
    "icons": [{"icon_no": 140, "file": "art/skill_icon_140.png"}, {"icon_no": 141, "file": "art/skill_icon_141.png"}],
    "asset_db": {"Pieces": [{"id": 3003, "w": 106, "h": 106, "ver": 138}], "Illusts": [{"id": 3003, "w": 878, "h": 1024, "ver": 131}],
                 "BuddyThumbs": [{"id": 523, "w": 106, "h": 106, "ver": 131}],
                 "BuddyImages": [{"id": 0, "name": "buddy_523a", "w": 367, "h": 605, "ver": 131}, {"id": 0, "name": "buddy_523b", "w": 235, "h": 327, "ver": 131}]},
    "native": ["gugba_native"],
}
sb = [server_buddy(500, 1291, bd["NameString"])]
write_mod(out, "14_gugba.json", mod, sb, {"name": "Gugba", "chr_ids": [1291], "native": ["gugba_native"], "icons": [140, 141]})
