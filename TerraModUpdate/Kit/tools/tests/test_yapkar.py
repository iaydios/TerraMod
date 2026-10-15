import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from emu import *
import yapkar_native as yk
m = yk.build({}); e = Emu(m); g = Game(e)
# stubs for yapkar-specific game calls
heals = []; revived = []
e.stub(yk.GETHP, lambda e: (e.setreg('S0', struct.unpack('<I', struct.pack('<f', 1000.0))[0]), e.ret()))
e.stub(yk.HPDEC, lambda e: e.ret(500))
e.stub(yk.HEAL, lambda e: (heals.append((e.reg('X0'), e.reg('X1') & 0xffffffff)), e.ret()))
CUR = {}
def revive(e):
    revived.append((e.reg('X0'), e.sf('S0'), e.reg('X1') & 0xffffffff))
    st = e.r64(e.reg('X0') + 0x38); e.mu.mem_write(st + 0x36, bytes([0])); e.ret()
e.stub(yk.REVIVE, revive)
e.stub(yk.ENUM_WRAP, lambda e: e.ret(0x5555))
def eget(e): x8 = e.reg('X8'); e.mu.mem_write(x8, b'\0' * 32); e.w64(x8, 0); e.ret()
e.stub(yk.ENUM_GET, eget)
def enext(e):
    x0 = e.reg('X0'); i = e.r64(x0); lst = CUR['list']
    if i < len(lst): CUR['cur'] = lst[i]; e.w64(x0, i + 1); e.ret(1)
    else: e.ret(0)
e.stub(yk.ENUM_NEXT, enext)
e.stub(yk.ENUM_CUR, lambda e: e.ret(CUR['cur']))
e.stub(yk.ENUM_DISP, lambda e: e.ret())
for pg in (0x2a44000, 0x2acc000, 0x2a2f000, 0x2add000, 0x2a92000): e.mapr(pg, 0x1000)
mi = e.alloc(16)
for a in (0x2a44a20, 0x2acc930, 0x2a2f810, 0x2add090, 0x2a926b0): e.w64(a, mi)
caps = [(100,4901),(101,4902),(102,4911),(103,4912),(104,4903),(105,4913),(106,4914),(112,4904),(50,0)]
for sid, cap in caps: g.skill(sid, cap)
e.mapr(yk.SITE_TICK_BACK, 4); e.mapr(yk.SITE_SAH_BACK, 4)
def tick(bm):
    heals.clear(); revived.clear(); CUR['list'] = g.bms[bm]
    e.call(m.addr['tick'], yk.SITE_TICK_BACK, x19=bm)
    assert e.reg('X19') == 0x1234, hex(e.reg('X19'))      # displaced ldr replayed
    assert e.reg('SP') == e.STACK + 0x8000
# Lambda with Delusion/Madness/Craving, no Awakening
lam = g.ent(1292, 0, [100, 101, 104]); y = g.ent(557, 0, [50]); ye = g.ent(557, 1, [50]); yd = g.ent(557, 0, [50], dead=1); oth = g.ent(19, 0, [50])
bm = g.bm([lam, y, ye, yd, oth]); g.bms[bm] = [lam, y, ye, yd, oth, ]
tick(bm)
nm = {lam: 'lam', y: 'yk', ye: 'enemy557', yd: 'dead557', oth: 'other'}
print('heals', [(nm[a], b) for a, b in heals])
for x in (y, ye, yd, oth): print(nm[x], g.desc(x))
d = {s: (v, l) for s, v, l in g.desc(y)}
assert d[102][0] == 100.0 and d[103][0] == 100.0, d          # DEF / SDEF +100%
assert d[105][0] == 100.0 and d[106][0] == 100.0, d          # ATK / SATK +100%
assert d[100][1] == 2
assert not g.mods(ye) and not g.mods(oth)
assert sorted(nm[a] for a, _ in heals) == ['lam', 'yk']
assert not revived
tick(bm); assert len(g.mods(y)) == len(d), g.desc(y)       # no duplicates on turn 2
# Lambda dies -> buffs zeroed
e.mu.mem_write(e.r64(lam + 0x38) + 0x36, bytes([1])); tick(bm)
assert all(v == 0.0 for s, v, l in g.desc(y) if s in (102, 103, 105, 106)), g.desc(y)
# Awakening (aura): dead 557 revives at 1/2
lam2 = g.ent(1292, 0, [100, 112]); yd2 = g.ent(557, 0, [50], dead=1); yd3 = g.ent(557, 1, [50], dead=1)
bm2 = g.bm([lam2, yd2, yd3]); tick(bm2)
nm.update({lam2: 'lam2', yd2: 'dead_ally', yd3: 'dead_enemy'})
print('revived', [(nm[a], f, k) for a, f, k in revived])
assert [nm[a] for a, _, _ in revived] == ['dead_ally'] and revived[0][1] == 0.5
# SkillAttack hook: Madness -> +3 ids, Craving -> +3 ids
import struct as st
def run_sah(ids):
    lst = e.alloc(0x20 + 4 * 16); e.w32(lst + 0x18, len(ids)); arr = e.alloc(0x20 + 4 * 32); e.w64(lst + 0x10, arr); e.w32(arr + 0x18, 32)
    for i, s in enumerate(ids): e.w32(arr + 0x20 + 4 * i, s)
    obj = e.alloc(0x40); e.w64(obj + 0x18, lst)
    added = []
    def ladd(e): added.append(e.reg('X1') & 0xffffffff); e.w32(e.reg('X0') + 0x18, e.r32(e.reg('X0') + 0x18) + 1); e.ret()
    e.stub(nl.LIST_ADD, ladd)
    e.mapr(0x2ad5000, 0x1000); e.w64(0x2ad5848, e.alloc(16)); e.w64(e.r64(0x2ad5848), 0)
    e.call(m.addr['sah'], yk.SITE_SAH_BACK, x19=obj)
    assert e.reg('X20') == lst
    return added
for sid, cap in [(120,4902),(121,4903)]: g.skill(sid, cap)
print('sah madness', run_sah([101])); print('sah craving', run_sah([104])); print('sah other', run_sah([50, 7]))
assert run_sah([101]) == list(range(104, 115)) and run_sah([104]) == list(range(107, 118)) and run_sah([50]) == []
print('YAPKAR OK')
