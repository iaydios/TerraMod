"""YapkarUpdate: Y'apkar? Lambda (1292), no buddy.  python3 make_yapkar.py <YapkarUpdate folder>"""
import sys
from common import *

out = sys.argv[1]
S = Skills()

delusion = S.add("delusion", shipped(3876), None,
                 tx("他細心鑽研，讓妄想一步步成真。免疫異常狀態，每回合恢復10%最大生命。若場上有亞普卡，亞普卡也獲得同等效果。",
                    "He studies with painstaking care and turns his delusions into reality, step by step. Immune to status ailments and recovers 10% max HP every turn. If Y'apkar is on the field, Y'apkar gains the same effect.",
                    "彼は丹念に研究を重ね、妄想を一歩ずつ現実にしていく。状態異常を無効にし、毎ターン最大HPの10%回復する。場にヤップカーがいれば、ヤップカーも同じ効果を得る。"))

mad = S.add("madness", base(299), tx("亞普卡瘋狂", "Y'apkar's Madness", "ヤップカーの狂気"),
            tx("高智慧機械的演算，化為四種元素的魔法。夾擊或連鎖時，有機率對被夾擊的敵人，連同其整條橫列、縱列與X型範圍，同時施放火、冰、暗、雷四種魔法傷害（各0.5倍）。若場上有亞普卡，亞普卡的防禦與魔防提升100%。",
               "The calculations of a highly intelligent machine become magic of four elements. On a pincer or chain, may unleash Fire, Ice, Dark and Thunder magic (0.5x each) on the pincered enemies plus their whole row, column and X-shaped area. If Y'apkar is on the field, Y'apkar's DEF and MDEF +100%.",
               "高度な知能を持つ機械の演算が、四つの元素の魔法となる。挟撃または連鎖時、確率で挟んだ敵とその横列・縦列・X型範囲すべてに火・氷・闇・雷の魔法ダメージ（各0.5倍）を同時に与える。場にヤップカーがいれば、ヤップカーの防御と魔防が100%上昇する。"),
            None, condition=0, emitRatio=50, power=0.5, iconNo=92, capacity=4902)
S.add("madness_def", shipped(3878))
S.add("madness_sdef", shipped(3879))
for key, tpl, cap, nm in (("ice", 409, 4941, tx("亞普卡瘋狂（冰）", "Y'apkar's Madness (Ice)", "ヤップカーの狂気（氷）")),
                          ("dark", 464, 4942, tx("亞普卡瘋狂（暗）", "Y'apkar's Madness (Dark)", "ヤップカーの狂気（闇）")),
                          ("thunder", 355, 4943, tx("亞普卡瘋狂（雷）", "Y'apkar's Madness (Thunder)", "ヤップカーの狂気（雷）"))):
    S.add("madness_" + key, base(tpl), nm, NONE, power=0.5, emitRatio=100, capacity=cap)
for key, tpl, cap, nm in (("fire_row", 302, 4944, tx("亞普卡瘋狂（火·橫列）", "Y'apkar's Madness (Fire, row)", "ヤップカーの狂気（火・横列）")),
                          ("ice_row", 412, 4945, tx("亞普卡瘋狂（冰·橫列）", "Y'apkar's Madness (Ice, row)", "ヤップカーの狂気（氷・横列）")),
                          ("dark_row", 467, 4946, tx("亞普卡瘋狂（暗·橫列）", "Y'apkar's Madness (Dark, row)", "ヤップカーの狂気（闇・横列）")),
                          ("thunder_row", 358, 4947, tx("亞普卡瘋狂（雷·橫列）", "Y'apkar's Madness (Thunder, row)", "ヤップカーの狂気（雷・横列）"))):
    S.add("madness_" + key, base(tpl), nm, NONE, power=0.5, emitRatio=100, capacity=cap)

for key, att, eff, cap, nm in (("fire_x", 1, 136, 4961, tx("亞普卡瘋狂（火·X）", "Y'apkar's Madness (Fire, X)", "ヤップカーの狂気（火・X）")),
                               ("ice_x", 2, 137, 4962, tx("亞普卡瘋狂（冰·X）", "Y'apkar's Madness (Ice, X)", "ヤップカーの狂気（氷・X）")),
                               ("dark_x", 4, 139, 4963, tx("亞普卡瘋狂（暗·X）", "Y'apkar's Madness (Dark, X)", "ヤップカーの狂気（闇・X）")),
                               ("thunder_x", 3, 138, 4964, tx("亞普卡瘋狂（雷·X）", "Y'apkar's Madness (Thunder, X)", "ヤップカーの狂気（雷・X）"))):
    S.add("madness_" + key, base(3345), nm, NONE, power=0.5, emitRatio=100, capacity=cap, attrib=att, effID=eff, range=16)

awk = S.add("awakening", base(3075), tx("亞普卡覺醒", "Y'apkar's Awakening", "ヤップカーの覚醒"),
            tx("精密的鑽研，讓高智慧機械的力量完全甦醒。夾擊或連鎖時，有機率對被夾擊的敵人，連同其整條橫列、縱列與X型範圍，同時施放太陽、月亮、重力、閃光四種魔法傷害（各1.0倍）。若場上有亞普卡，亞普卡的攻擊與魔攻提升100%。",
               "Meticulous research fully awakens the power of the highly intelligent machine. On a pincer or chain, may unleash Sun, Moon, Gravity and Photon magic (1.0x each) on the pincered enemies plus their whole row, column and X-shaped area. If Y'apkar is on the field, Y'apkar's ATK and MATK +100%.",
               "緻密な研究が、高度な知能を持つ機械の力を完全に目覚めさせる。挟撃または連鎖時、確率で挟んだ敵とその横列・縦列・X型範囲すべてに太陽・月・重力・閃光の魔法ダメージ（各1.0倍）を同時に与える。場にヤップカーがいれば、ヤップカーの攻撃と魔攻が100%上昇する。"),
            None, condition=0, emitRatio=30, power=1.0, iconNo=92, capacity=4903)
S.add("awakening_atk", shipped(3884))
S.add("awakening_satk", shipped(3885))
for key, tpl, cap, nm in (("moon", 3179, 4951, tx("亞普卡覺醒（月亮）", "Y'apkar's Awakening (Moon)", "ヤップカーの覚醒（月）")),
                          ("gravity", 2272, 4952, tx("亞普卡覺醒（重力）", "Y'apkar's Awakening (Gravity)", "ヤップカーの覚醒（重力）")),
                          ("photon", 2262, 4953, tx("亞普卡覺醒（閃光）", "Y'apkar's Awakening (Photon)", "ヤップカーの覚醒（閃光）"))):
    S.add("awakening_" + key, base(tpl), nm, NONE, power=1.0, emitRatio=100, capacity=cap)
for key, tpl, cap, nm in (("sun_row", 3076, 4954, tx("亞普卡覺醒（太陽·橫列）", "Y'apkar's Awakening (Sun, row)", "ヤップカーの覚醒（太陽・横列）")),
                          ("moon_row", 3180, 4955, tx("亞普卡覺醒（月亮·橫列）", "Y'apkar's Awakening (Moon, row)", "ヤップカーの覚醒（月・横列）")),
                          ("gravity_row", 2273, 4956, tx("亞普卡覺醒（重力·橫列）", "Y'apkar's Awakening (Gravity, row)", "ヤップカーの覚醒（重力・横列）")),
                          ("photon_row", 2263, 4957, tx("亞普卡覺醒（閃光·橫列）", "Y'apkar's Awakening (Photon, row)", "ヤップカーの覚醒（閃光・横列）"))):
    S.add("awakening_" + key, base(tpl), nm, NONE, power=1.0, emitRatio=100, capacity=cap)

for key, tpl, att, eff, cap, nm in (("sun_x", 3345, 23, 419, 4971, tx("亞普卡覺醒（太陽·X）", "Y'apkar's Awakening (Sun, X)", "ヤップカーの覚醒（太陽・X）")),
                                    ("moon_x", 3311, 24, 425, 4972, tx("亞普卡覺醒（月亮·X）", "Y'apkar's Awakening (Moon, X)", "ヤップカーの覚醒（月・X）")),
                                    ("gravity_x", 3345, 18, 335, 4973, tx("亞普卡覺醒（重力·X）", "Y'apkar's Awakening (Gravity, X)", "ヤップカーの覚醒（重力・X）")),
                                    ("photon_x", 3345, 17, 329, 4974, tx("亞普卡覺醒（閃光·X）", "Y'apkar's Awakening (Photon, X)", "ヤップカーの覚醒（閃光・X）"))):
    S.add("awakening_" + key, base(tpl), nm, NONE, power=1.0, emitRatio=100, capacity=cap, attrib=att, effID=eff, range=16)

aura = S.add("aura", shipped(3889), None,
             tx("高智慧機械的庇護，讓倒下的同伴再次站起。全場復活1次，血量1/2。若場上有亞普卡，亞普卡死亡後可無限復活，血量1/2。",
                "The protection of a highly intelligent machine lets fallen comrades stand again. Revives the whole field once, at 1/2 HP. If Y'apkar is on the field, Y'apkar can revive endlessly at 1/2 HP.",
                "高度な知能を持つ機械の庇護が、倒れた仲間を再び立ち上がらせる。場の全員を1回復活させる（HP1/2）。場にヤップカーがいれば、ヤップカーは倒れても何度でも復活できる（HP1/2）。"),
             spower=0.5)

mod = {
    "_note": "Y'apkar? Lambda (1292), self-contained native module yapkar_native.  Marks: 4901 Delusion, 4902 Madness (+1 DEF% 4911, +2 SDEF% 4912, +3..+5 ice/dark/thunder columns 4941..4943, +6..+9 fire/ice/dark/thunder rows 4944..4947, +10..+13 fire/ice/dark/thunder X 4961..4964), 4903 Awakening (+1 ATK% 4913, +2 SATK% 4914, +3..+5 moon/gravity/photon columns 4951..4953, +6..+9 sun/moon/gravity/photon rows 4954..4957, +10..+13 sun/moon/gravity/photon X 4971..4974), 4904 Aura.  Madness/Awakening are pincer-or-chain column attacks "
             "(one shared emit roll, the hidden elements are appended to the emitted list); the symbiotic Y'apkar (557) gets +100%.",
    "skills": S.items,
    "characters": [character(1292, 5169, [delusion, mad, aura, awk])],
    "asset_db": {"Pieces": [{"id": 3007, "w": 106, "h": 106, "ver": 132}], "Illusts": [{"id": 3007, "w": 878, "h": 1024, "ver": 131}]},
    "native": ["yapkar_native"],
}
write_mod(out, "15_yapkar.json", mod, [], {"name": "Yapkar", "chr_ids": [1292], "native": ["yapkar_native"], "icons": []})
