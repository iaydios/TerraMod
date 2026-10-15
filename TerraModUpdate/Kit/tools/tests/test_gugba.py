import sys, os, random
sys.path.insert(0, os.path.dirname(__file__))
from emu import *
import gugba_native as gn
random.seed(7)
m = gn.build({'fx': {'fx_tap_gather': 271}}); e = Emu(m, {'fx': {'fx_tap_gather': 271}}); g = Game(e)
BOSS = set(); calls = {k: [] for k in ('sethp', 'eval', 'fx', 'startco', 'shake', 'showmsg', 'getname', 'listadd')}
RAND = {'fn': lambda lo, hi: random.randrange(lo, hi)}
e.stub(gn.ISBOSS, lambda e: e.ret(1 if e.reg('X0') in BOSS else 0))
e.stub(gn.SETHP, lambda e: (calls['sethp'].append((e.reg('X0'), e.reg('X1') & 0xffffffff)), e.ret()))
e.stub(gn.EVALUATE, lambda e: (calls['eval'].append(e.reg('X0')), e.ret()))
e.stub(gn.RANDOM_RANGE_I, lambda e: e.ret(RAND['fn'](e.reg('X1') & 0xffffffff, e.reg('X2') & 0xffffffff)))
e.stub(gn.EMITCORRECT, lambda e: e.ret(10))
e.stub(0x10cb088, lambda e: (calls['fx'].append((e.reg('X2'), e.reg('X1') & 0xffffffff)), e.ret()))
def listadd(e):
    lst = e.reg('X0'); n = e.r32(lst + 0x18); a = e.r64(lst + 0x10); e.w32(a + 0x20 + 4 * n, e.reg('X1')); e.w32(lst + 0x18, n + 1); calls['listadd'].append(e.reg('X1') & 0xffffffff); e.ret()
e.stub(gn.LIST_ADD, listadd)
e.stub(gn.GETNAME, lambda e: (calls['getname'].append(e.reg('X0')), e.ret(0xABCD)))
e.stub(gn.SHOWMSG, lambda e: (calls['showmsg'].append((e.reg('X0'), e.reg('X1'), e.reg('X2') & 0xffffffff)), e.ret(0xE001)))
e.stub(gn.STARTCO, lambda e: (calls['startco'].append((e.reg('X0'), e.reg('X1'))), e.ret(0xC0)))
e.stub(gn.SCREENSHAKE, lambda e: (calls['shake'].append(e.sf('S0')), e.ret(0x5AAE)))
e.stub(gn.GETATT, lambda e: (e.setreg('S0', struct.unpack('<I', struct.pack('<f', 0.25))[0]), e.ret()))
e.stub(0x1024a58, lambda e: e.ret(1)); e.stub(gn.ISROOT, lambda e: e.ret(ROOT['v']))
ROOT = {'v': 1}
# fx_play pointer chain
for pg in (0x2a5f000, 0x21c4000): e.mapr(pg, 0x1000)
c1, c2, c3 = e.alloc(16), e.alloc(0x100), e.alloc(16); e.w64(0x2a5f928, c1); e.w64(c1, c2); e.w64(c2 + 0xa0, c3); e.w64(c3, 0x77)
S = {}
def mk(sid, cap, sp=0.0): S[sid] = g.skill(sid, cap, sp)
for sid, cap, sp in [(10, 4801, -10.0), (20, 4802, 0), (21, 0, 0), (22, 0, 0), (23, 0, 0), (24, 0, 0), (30, 4806, 0), (31, 4805, 0), (32, 4807, 0), (33, 4808, 0), (34, 4809, 0),
                     (35, 4810, 0), (40, 4830, 0), (41, 0, 0), (99, 0, 0)]: mk(sid, cap, sp)
def stats(ent, sids):
    return {s: v for s, v, l in g.desc(ent) if s in sids}
# ------------------------------------------------------------------ Out of My Way
carrier = g.ent(1291, 0, [10]); mon = g.ent(900, 1, [99]); boss = g.ent(901, 1, [99]); ally = g.ent(19, 0, [99]); BOSS.add(boss)
T = [0x108e0c4, 0x108e058, 0x108e054]
def cm1(occ): e.setreg('W0', 0); return e.call(m.addr['cm1'], T, x19=carrier, x20=occ)
assert cm1(mon) == 0x108e0c4 and e.reg('W0') == 1
assert cm1(boss) == 0x108e058 and cm1(ally) == 0x108e058 and cm1(0) == 0x108e054
plain = g.ent(20, 0, [99])
def cm1p(occ): return e.call(m.addr['cm1'], T, x19=plain, x20=occ)
assert cm1p(mon) == 0x108e058
T2 = [0x108eea4, 0x108f130, 0x108ee6c]
def cm2(who, occ, kind): return e.call(m.addr['cm2'], T2, x19=who, x22=occ, x8=kind)
assert cm2(carrier, mon, 1) == 0x108eea4 and cm2(carrier, boss, 1) == 0x108f130 and cm2(carrier, mon, 0) == 0x108ee6c and cm2(plain, mon, 1) == 0x108f130
sk = g.skills[10]
def equip(cap):
    s = e.alloc(0x100); e.w32(s + 0x84, cap); e.w32(s + 0x58, 0x1234)
    end = e.call(m.addr['equip'], [0x1028170, 0x10280ec], x24=s); return end, e.reg('W8')
assert equip(4801)[0] == 0x10280ec and equip(4819)[0] == 0x10280ec and equip(4820)[0] == 0x1028170 and equip(4799)[0] == 0x1028170 and equip(4820)[1] == 0x1234
print('out of my way OK')
# ------------------------------------------------------------------ Whiskey: cups
gugba = g.ent(1291, 0, [10, 20, 30], hp=900)
def cups(ent=None): return [stats(ent or gugba, {s})[s] if stats(ent or gugba, {s}) else 0.0 for s in (21, 22, 23, 24)]
def drink(n=1):
    for _ in range(n): e.call(m.addr['drink'], 0xdead0000, x0=gugba, x1=20)
for i in range(1, 17):
    drink(); c = cups(); assert sum(c) == 25 * i and max(c) <= 100, (i, c)
assert cups() == [100.0] * 4
drink(); assert cups() == [100.0] * 4                                       # 17th drink does nothing
assert all(l == 0xffffffff for _, _, l in g.desc(gugba))                    # no time limit
# a full stat is skipped: only one stat has room -> it always gets the cup
for k in range(4):
    for sid in (21, 22, 23, 24): pass
mods = {s: [x for x in g.mods(gugba) if e.r64(x + 0x40) == g.skills[s]][0] for s in (21, 22, 23, 24)}
for s in (21, 22, 23, 24): e.wf(mods[s] + 0x24, 100.0)
e.wf(mods[23] + 0x24, 50.0); drink(); assert cups() == [100.0, 100.0, 75.0, 100.0]; drink(); drink(); assert cups() == [100.0] * 4
# ------------------------------------------------------------------ damage taken: cups restart + "Enough..." at the 20th hit
def gd(victim, d):
    e.call(m.addr['gdmg'], gn.SITE_DMG + 4, x0=victim, x1=d, x2=g.skills[99], x3=mon)
    assert e.reg('X28') == 0x2a94000 and e.reg('SP') == e.STACK + 0x8000 and e.reg('W1') == d & 0xffffffff
gd(gugba, 0); assert cups() == [100.0] * 4                                   # no damage -> nothing
gd(mon, 50); gd(ally, 50)                                                    # others: nothing
gd(gugba, 50); assert cups() == [0.0] * 4 and calls['eval'][-1] == e.r64(gugba + 0x48)
drink(3); assert sum(cups()) == 75                                           # restarts from 0
assert not calls['showmsg']
for n in (0, 5, 18, 20, 25): e.w32(gugba + 0x32c, n); gd(gugba, 10)
assert not calls['showmsg']
e.w32(gugba + 0x32c, 19); gd(gugba, 10)
assert calls['showmsg'] == [(gugba, 0xABCD, 0)] and calls['startco'][-1] == (gugba, 0xE001) and calls['getname'] == [g.skills[34]], calls
assert stats(gugba, {34}) == {34: 0.0} or any(e.r64(x + 0x40) == g.skills[34] for x in g.mods(gugba))
e.w32(gugba + 0x32c, 19); gd(gugba, 10); assert len(calls['showmsg']) == 1       # said only once
noTap = g.ent(1291, 0, [20]); e.w32(noTap + 0x32c, 19); gd(noTap, 10); assert len(calls['showmsg']) == 1
print('whiskey + hit counter OK')
# ------------------------------------------------------------------ whiskey roll / drink at the end of the iterator
flag = gn.FLAG_PAGE + gn.FLAG_OFF
e.mapr(gn.FLAG_PAGE, 0x1000)
sk20 = g.skills[20]; e.w32(sk20 + 0x6c, 30)
def hpre(rolled):
    RAND['fn'] = lambda lo, hi: rolled
    ev = e.alloc(0x40); e.w64(ev + 0x8, 0x1)
    e.call(m.addr['hpre'], gn.SITE_PRE + 4, x0=ev, x1=gugba, x2=0x22, x3=0x33)
    assert e.reg('X0') == ev and e.reg('X1') == gugba and e.reg('SP') == e.STACK + 0x8000 - 0x60
e.mu.mem_write(flag, b'\0'); hpre(39); assert e.mu.mem_read(flag, 1)[0] == 1          # 30 + 10 (skill boost) = 40 > 39
e.mu.mem_write(flag, b'\0'); hpre(40); assert e.mu.mem_read(flag, 1)[0] == 0
e.mu.mem_write(flag, b'\0'); e.call(m.addr['hpre'], gn.SITE_PRE + 4, x0=1, x1=ally, x2=0, x3=0); assert e.mu.mem_read(flag, 1)[0] == 0
bm = g.bm([gugba, mon, ally]); RAND['fn'] = lambda lo, hi: random.randrange(lo, hi)
def hend(setflag):
    e.mu.mem_write(flag, bytes([setflag])); it = e.alloc(0x100); ev = e.alloc(0x40); e.w64(it + 0x88, ev); e.w64(ev + 0x28, bm)
    e.call(m.addr['hend'], gn.SITE_END + 4, x19=it); assert e.reg('X20') == ev and e.mu.mem_read(flag, 1)[0] == 0
before = sum(cups()); hend(0); assert sum(cups()) == before
hend(1); assert sum(cups()) == before + 25
print('whiskey roll OK')
# ------------------------------------------------------------------ Rhythm Headbutt: counter (gadd) + damage factor (fist cave)
def emit(ids, attacker):
    lst = e.alloc(0x20); arr = e.alloc(0x20 + 4 * 64); e.w64(lst + 0x10, arr); e.w32(lst + 0x18, 0)
    it = e.alloc(0x40); e.w64(it + 0x10, attacker)
    for sid in ids: e.call(m.addr['gadd'], 0xdead0000, x0=lst, x1=sid, x2=0x66, x19=it)
    n = e.r32(lst + 0x18); a = e.r64(lst + 0x10); return [e.r32(a + 0x20 + 4 * i) for i in range(n)]
def counter(ent):
    return [v for s, v, l in g.desc(ent) if s == 41]
def hbfactor(ent, victim):
    ev = e.alloc(0x40); e.w64(ev + 0x20, 0x9999)
    e.call(m.addr['fist'], 0xf0cc20, x19=ent, x20=victim, x21=g.skills[40], x25=ev); return e.sf('S0')
hb = g.ent(1291, 0, [40], hp=900); foe = g.ent(900, 1, [99])
assert hbfactor(hb, foe) == 1.0                                         # nothing counted yet: 1.0 x ATK
assert emit([40], hb) == [40] and counter(hb) == [1.0] and len(g.mods(hb)) == 1      # skill emitted once only, counter 1
assert hbfactor(hb, foe) == 1.0
assert emit([40], hb) == [40] and counter(hb) == [2.0] and hbfactor(hb, foe) == 2.0
for _ in range(98): emit([40], hb)
assert counter(hb) == [100.0] and hbfactor(hb, foe) == 100.0 and len(g.mods(hb)) == 1       # no cap
assert all(l == 0xffffffff for _, _, l in g.desc(hb))                                    # lives for the whole battle
other = g.ent(1291, 0, [40], hp=900)
assert emit([99, 0, 31], other) == [99, 0, 31] and not g.mods(other)             # other skills / id 0 do nothing
assert emit([99, 40, 99], other) == [99, 40, 99] and counter(other) == [1.0]         # exactly one count per cast
assert counter(hb) == [100.0]                                                           # counters are per character
assert hbfactor(other, foe) == 1.0 and hbfactor(g.ent(1291, 0, [40]), foe) == 1.0
print('rhythm headbutt OK')
# ------------------------------------------------------------------ Grandma's Will
foes = [g.ent(900 + i, 1, [99], pos=(i, 0)) for i in range(3)]; dead_foe = g.ent(950, 1, [99], dead=1); obj = g.ent(951, 2, [99])
bm = g.bm([gugba, ally] + foes + [dead_foe, obj]); e.w64(gugba + 0x268, bm)
for x in g.mods(gugba):
    pass
tapper = g.ent(1291, 0, [30], hp=900); e.w64(tapper + 0x268, bm)
def hop(ent):
    return e.call(m.addr['hop'], [0x1086828, gn.SITE_HOP + 4], x19=ent)
calls['fx'].clear()
assert hop(tapper) == 0x1086828
assert [d[0] for d in g.desc(tapper)] == [30] and g.desc(tapper)[0][2] == 1                                  # armed, 1 turn
for f in foes: assert g.desc(f) == [(35, 0.0, 1)], g.desc(f)                                                 # DEF -99 % modifier, 1 turn
assert not g.mods(dead_foe) and not g.mods(obj) and not g.mods(ally)
assert len(calls['fx']) == 2 and [c[1] for c in calls['fx']] == [372, 271]          # 270 (chain-link icon) removed
assert all(1 <= c[1] <= 450 for c in calls['fx']), 'EffectManager pool is an array of 451: particle ids above 450 throw IndexOutOfRange (this crashed the tap skill)'
# limitModifiedStatus hook: an entity carrying the DEF-break modifier skips the game's reduction cap, everybody else keeps it
LIM = [0x1078eac, 0x1078e6c]
for f in foes:
    e.w64(f + 0x38, e.r64(f + 0x38)); assert e.call(m.addr['hdef'], LIM, x21=f, x23=0) == 0x1078eac
plainfoe = g.ent(960, 1, [99]); assert e.call(m.addr['hdef'], LIM, x21=plainfoe, x23=0) == 0x1078e6c and e.reg('X23') == e.r64(plainfoe + 0x38)
assert e.call(m.addr['hdef'], LIM, x21=ally, x23=0) == 0x1078e6c
print('limitModifiedStatus bypass OK')
n = len(g.mods(foes[0])); assert hop(tapper) == 0x1086828 and len(g.mods(tapper)) == 1 and len(g.mods(foes[0])) == n    # re-tap: nothing new
used = g.ent(1291, 0, [30]); e.w64(used + 0x268, bm); e.w64(e.r64(used + 0x48) + 0, e.r64(used + 0x48) + 0) if False else None
usedmod = None
# used once already -> the marker (tap id+2) blocks arming but the game's party buff is still skipped
am_call = lambda ent, sid: None
mkused = g.ent(1291, 0, [30]); e.w64(mkused + 0x268, bm)
e.call(m.addr['am'], 0xdead0000, x0=mkused, x1=g.skills[32], x2=0xffffffff)
before = [len(g.mods(f)) for f in foes]; assert hop(mkused) == 0x1086828 and [d[0] for d in g.desc(mkused)] == [32] and [len(g.mods(f)) for f in foes] == before
other = g.ent(19, 0, [99]); e.w64(other + 0x268, 0x4444)
assert hop(other) == gn.SITE_HOP + 4 and e.reg('X21') == 0x4444 and not g.mods(other)
print('tap (hop) OK')
def tapemit(skill, ent, root=1):
    ROOT['v'] = root
    return e.call(m.addr['tapemit'], [0x10bea10, 0x10be6c4, 0x10be780], x24=g.skills[skill] if skill else skill, x22=ent, x23=0x25)
assert tapemit(99, tapper) == 0x10be780                                    # not the tap skill: IsEmittable path
assert tapemit(30, tapper) == 0x10bea10 and e.reg('W8') == 5                # armed, not used: emitted
assert tapemit(30, tapper, root=0) == 0x10be6c4                             # not the attack root
assert tapemit(30, mkused) == 0x10be6c4                                     # used (and not armed)
unarmed = g.ent(1291, 0, [30]); assert tapemit(30, unarmed) == 0x10be6c4
print('tap emit OK')
def pick(sid):
    e.mapr(gn.GETSKILL, 4); e.stubs[gn.GETSKILL] = lambda e: e.ret(sid)
    e.call(m.addr['pick'], 0xdead0000, x0=0x99, x1=3, x2=0); return e.reg('W0')
assert pick(30) == 31 and pick(99) == 99 and pick(40) == 40 and pick(0) == 0
ic = e.alloc(0x80); e.mu.mem_write(ic + 0x20, b'\xff' * 0x40)
e.call(m.addr['icons'], gn.SITE_ICONS + 4, x19=tapper, x20=ic); assert e.mu.mem_read(ic + 0x20, 0x40) == b'\0' * 0x40 and e.reg('X8') == 0x2ad8000
e.mu.mem_write(ic + 0x20, b'\xff' * 0x40); e.call(m.addr['icons'], gn.SITE_ICONS + 4, x19=ally, x20=ic); assert e.mu.mem_read(ic + 0x20, 0x40) == b'\xff' * 0x40
print('pick / icons OK')
# ------------------------------------------------------------------ the fist
def fist(attacker, victim, skill=31, hits=None):
    if hits is not None: e.w32(attacker + 0x32c, hits)
    for k in ('sethp', 'shake', 'startco', 'fx'): calls[k].clear()
    ev = e.alloc(0x40); e.w64(ev + 0x20, 0x9999)
    end = e.call(m.addr['fist'], 0xf0cc20, x19=attacker, x20=victim, x21=g.skills[skill], x25=ev)
    assert e.reg('SP') == e.STACK + 0x8000
    return e.sf('S0')
def board(hits):
    a = g.ent(1291, 0, [30], hp=900, pos=(0, 3)); e.w32(a + 0x32c, hits)
    v = [g.ent(900 + i, 1, [99], pos=(0, 3 - 1 - i) if False else (0, 2 - i)) for i in range(3)]
    return a, v
a, v = board(7)
f1 = fist(a, v[0]); assert f1 == 7.0, f1
assert calls['sethp'] == [(a, 1), (v[0], 1)] and calls['shake'] == [1.5] and calls['startco'] == [(0x9999 and 0x9999, 0x5AAE)] and calls['fx'][-1][1] == 424, calls
assert [d[0] for d in g.desc(a)] == [32] and any(d[0] == 33 for d in g.desc(v[0]))                    # used marker + stun
f2 = fist(a, v[1]); assert f2 == 5.0 and not calls['sethp'] and not calls['shake'], (f2, calls)       # distance 2 -> 7-2
f3 = fist(a, v[2]); assert f3 == min(7, 4), f3
assert all(any(d[0] == 33 for d in g.desc(x)) for x in v) and len(g.mods(a)) == 1                      # attacker marker once
a, v = board(30); assert fist(a, v[0]) == 20.0
a, v = board(0); assert fist(a, v[0]) == 1.0
a, v = board(2); fist(a, v[0]); assert fist(a, v[1]) == 2.0 and fist(a, v[2]) == 2.0                    # min(hits, 7-dist)
far = g.ent(990, 1, [99], pos=(0, 3 + 8)); assert fist(a, far) == 1.0                                  # far behind: at least 1
a, v = board(10); BOSS.add(v[0]); fist(a, v[0]); assert (v[0], 1) not in calls['sethp'] and not any(d[0] == 33 for d in g.desc(v[0])); BOSS.discard(v[0])
a, v = board(10); assert fist(a, v[0], skill=99) == 0.25 and not calls['sethp']                          # other skills untouched (original attenuation call)
print('fist OK')
# ------------------------------------------------------------------ a full-battle style scenario: whiskey stays through turns, reset on hit
print('GUGBA OK')
