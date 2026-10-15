"""KanaUpdate: Kana Lambda (1290) + buddy Heart-Throb Revolver (499).  python3 make_kana.py <KanaUpdate folder>"""
import sys
from common import *

out = sys.argv[1]
S = Skills()
MARKER = shipped(3857)

def keep(sid, extra_zh, extra_en, extra_ja, name=None):
    """Keeps Sam's quote and appends one short line saying what the skill now does."""
    r = shipped(sid)
    d = r["descString"]
    return tx(d["zh_tw"] + "\n" + extra_zh, d["en"] + "\n" + extra_en, d["ja"] + "\n" + extra_ja)

heart = S.add("heartbeat", shipped(3857), None,
              tx("你好像碰到我了，身上有我的味道呢~", "You seem to have touched me... you smell of me now~", "私に触れたみたいね。もう私の匂いがするわよ〜"), iconNo=129, status=0)   # status 0: status 53 would make the portrait glow red all battle
S.add("heartbeat_buff", shipped(3858), iconNo=129)                                          # hidden id+1: all stats x1.1 for the ally she moves
bullet = S.add("virus_bullet", shipped(3859), tx("魅惑子彈", "Charm Bullet", "魅惑弾"),
               shipped(3859)["descString"],
               condition=0, emitRatio=40, power=2.0, spower=2.0, status=1, successRate=100, life=2, capacity=4601, iconNo=129)
contrast = S.add("contrast", MARKER, shipped(3860)["nameString"],
                 shipped(3860)["descString"],
                 iconNo=129, capacity=4612, emitRatio=0, status=0)
S.add("pink_poison", shipped(3862), tx("愛心粉毒（反差萌）", "Pink Heart Poison (Contrast)", "ハート毒（ギャップ萌え）"), NONE)   # hidden id+1 of Contrast
queen = S.add("queen_bee", shipped(3861), None,
              tx("嗯~?是新來的嗎?", "Mmm~? Are you new here?", "んん〜？新入りかしら？"),
              condition=0, emitRatio=10, effID=205, capacity=4613, iconNo=130)
virus = S.add("heart_virus", shipped(3863), None,
              shipped(3863)["descString"],
              status=9, spower=-50.0, life=3, iconNo=129)

mod = {
    "_note": "Kana Lambda (1290), self-contained native module kana_native.  Marks: 4611 Heartbeat (+1 buff), 4601 Virus Bullet, 4612 Contrast (+1 = hidden permanent "
             "Pink Heart Poison, mark 4614), 4613 Queen Bee.  Buddy 499 skill Heart-Throb Virus: pincer line (successRate 4444), status 9 = skill rate -50%.",
    "skills": S.items,
    "buddies": [buddy(499, virus)],
    "characters": [character(1290, 5167, [heart, bullet, contrast, queen])],
    "icons": [{"icon_no": 129, "file": "art/skill_icon_129.png"}, {"icon_no": 130, "file": "art/skill_icon_130.png"}],
    "asset_db": {"Pieces": [{"id": 3002, "w": 106, "h": 106, "ver": 131}], "Illusts": [{"id": 3002, "w": 878, "h": 1024, "ver": 131}],
                 "BuddyThumbs": [{"id": 522, "w": 106, "h": 106, "ver": 131}],
                 "BuddyImages": [{"id": 0, "name": "buddy_522a", "w": 367, "h": 605, "ver": 131}, {"id": 0, "name": "buddy_522b", "w": 235, "h": 327, "ver": 131}]},
    "native": ["kana_native"],
}
sb = [server_buddy(499, 1290, EX["buddies"]["499"]["NameString"])]
write_mod(out, "12_kana.json", mod, sb, {"name": "Kana", "chr_ids": [1290], "native": ["kana_native"], "icons": [129, 130]})
