import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from emu import *
import kana_native as kn
m = kn.build({}); e = Emu(m); g = Game(e); e.allow = {'x1', 'x24'}      # the damage argument is changed on purpose (w1 = damage, w24 = AddModifier flags: values the hooks are there to alter)
heals = []; onhit = []; evals = []
e.stub(kn.ONHIT, lambda e: (onhit.append((e.reg('X0'), e.reg('X1'), e.reg('X2'))), e.ret()))
e.stub(kn.GETATK, lambda e: e.ret(250))
e.stub(kn.HEAL, lambda e: (heals.append((e.reg('X0'), e.reg('X1') & 0xffffffff)), e.ret()))
e.stub(kn.HPDEC, lambda e: e.ret(500))
e.stub(kn.EVALUATE, lambda e: (evals.append(e.reg('X0')), e.ret()))
MAGIC = set()
e.stub(kn.IS_MAGIC, lambda e: e.ret(1 if e.reg('X0') in MAGIC else 0))
for a in (0x10917ac, 0x10bea10, 0xD350CC, 0xF06AAC): e.mapr(a, 4)
for sid, cap in [(30, 4611), (31, 0), (32, 4601), (33, 4612), (34, 4614), (35, 4613), (50, 0), (51, 0)]: g.skill(sid, cap)
g.skills[31] and e.wf(g.skills[31] + 0x20, 1.1)
magic = g.skills[50]; phys = g.skills[51]; MAGIC.add(magic)
kana = g.ent(1290, 0, [30, 32, 33, 35], hp=900); ally = g.ent(19, 0, [50]); dead_ally = g.ent(20, 0, [50], dead=1); foe = g.ent(900, 1, [50]); foe2 = g.ent(901, 1, [50])
obj = g.ent(902, 2, [50]); foe_dead = g.ent(903, 1, [50], dead=1); plain = g.ent(21, 0, [50])
nm = {kana: 'kana', ally: 'ally', dead_ally: 'dead_ally', foe: 'foe', foe2: 'foe2', obj: 'obj', foe_dead: 'foe_dead', plain: 'plain'}
# ---- Heartbeat
def heart(mover, disp):
    onhit.clear(); e.call(m.addr['heart'], 0xdead0000, x0=mover, x1=disp, x2=0)
e.mapr(0x108D02C + 4, 4)
heart(kana, ally); assert onhit == [(kana, ally, 0)] and g.desc(ally)[0][0] == 31 and abs(g.desc(ally)[0][1] - 1.1) < 1e-6 and g.desc(ally)[0][2] == 1, g.desc(ally)
heart(kana, ally); assert len(g.mods(ally)) == 1 and g.desc(ally)[0][2] == 1                       # refreshed, not stacked
heart(kana, foe); assert not g.mods(foe) and len(onhit) == 1                                         # enemy: nothing
heart(kana, dead_ally); assert not g.mods(dead_ally)
heart(plain, ally); assert len(g.mods(ally)) == 1 and onhit == [(plain, ally, 0)]                   # mover without Heartbeat: no new mod
heart(kana, kana); assert not g.mods(kana)
# ---- Queen Bee (attacker.+0x268 = battle manager)
bm = g.bm([kana, ally, foe, foe2, obj, foe_dead, dead_ally, plain]); e.w64(kana + 0x268, bm)
def queen():
    e.call(m.addr['queen'], 0x10bea10, x24=g.skills[35], x22=kana, x23=0x45)
    assert e.reg('X8') == 5 and e.reg('X22') == kana and e.reg('X24') == g.skills[35]
queen()
for x in (foe, foe2): d = g.desc(x); assert d == [(34, 1.0, 0xffffffff)], d
for x in (ally, obj, foe_dead, dead_ally, plain): assert x == ally or not g.mods(x), nm[x]
assert [d[0] for d in g.desc(ally)] == [31]
pm = g.mods(foe)[0]; assert e.r64(pm + 0x30) == kana and e.r32(pm + 0x28) == 500
queen(); assert g.desc(foe)[0][1] == 2.0 and len(g.mods(foe)) == 1
# non-queen skill: nothing happens, only the displaced instruction
e.call(m.addr['queen'], 0x10bea10, x24=g.skills[32], x22=kana, x23=3); assert g.desc(foe)[0][1] == 2.0 and e.reg('X8') == 3
# ---- Contrast
def hit(victim, attacker, skill, d):
    e.call(m.addr['contrast'], 0x10917ac, x0=victim, x1=d, x2=skill, x3=attacker)
    assert e.reg('SP') == e.STACK + 0x8000 - 0x70 and e.reg('X0') == victim and e.reg('X3') == attacker and e.reg('X2') == skill
    return e.reg('X1') & 0xffffffff
assert hit(kana, foe, phys, 123) == 123 and g.desc(foe)[0][1] == 2.0
assert hit(kana, foe, magic, 123) == 0 and g.desc(foe)[0][1] == 3.0                    # nullified + one more stack
assert hit(kana, plain, magic, 50) == 50                                                # attacker is a player piece: untouched
assert hit(ally, foe, magic, 77) == 77 and g.desc(foe)[0][1] == 3.0                     # victim without Contrast
assert hit(kana, foe_dead, magic, 77) == 77
assert hit(kana, foe, magic, 0) == 0 and g.desc(foe)[0][1] == 3.0
assert hit(kana, 0, magic, 9) == 9
# ---- poison tick heal
def red(skill, s9, tick=50):
    heals.clear(); mod = e.alloc(0x80); e.w64(mod + 0x40, g.skills[skill]); e.w64(mod + 0x30, kana)
    e.setreg('S9', struct.unpack('<I', struct.pack('<f', s9))[0])
    e.call(m.addr['red'], 0xD350CC, x20=mod, x21=tick)
    assert e.reg('X0') == 0 and e.reg('X1') == 0 and e.reg('SP') == e.STACK + 0x8000
red(32, 1.0); assert heals == [(kana, 50)], heals                    # Virus Bullet: heal = tick
red(34, 3.0); assert heals == [(kana, 75)], heals                    # queen poison: tick x stacks x 0.5
red(50, 1.0); assert heals == []
# ---- forced poison
def force(skill, caster_is_target=False):
    mod = e.alloc(0x80); ctx = e.alloc(0x40); casterobj = e.alloc(0x10)
    e.w32(mod + 0x10, 1); e.w64(mod + 0x40, g.skills[skill]); e.w64(mod + 0x30, casterobj); e.w64(ctx + 0x18, casterobj if caster_is_target else 0x777)
    e.call(m.addr['force'], 0xdead0000, x19=mod, x20=ctx, x24=0x10)
    return e.reg('X24') & 1, e.reg('X8')
e.mapr(0xdead0000, 8)
assert force(32) == (1, 1) and force(32, True)[0] == 0 and force(50)[0] == 0
# ---- pincer line
def line(attacker_y, target_y, mark=4444):
    st = e.alloc(0x40); sk = e.alloc(0x100); e.w32(sk + 0x78, mark)
    co = e.alloc(0x80); e.w64(co + 0x40, sk)
    a = e.alloc(0x80); ast = e.alloc(0x80); e.w64(a + 0x38, ast); e.w32(ast + 0x50, attacker_y)
    t = e.alloc(0x80); tst = e.alloc(0x80); e.w64(t + 0x38, tst); e.w32(tst + 0x50, target_y)
    lst = e.alloc(0x40); arr = e.alloc(0x40); e.w64(lst + 0x10, arr); e.w32(lst + 0x18, 1); e.w64(arr + 0x20, t)
    e.call(m.addr['line'], 0xF06AAC, x19=co, x2=a, x3=lst)
    return e.r32(sk + 0x64), e.r32(sk + 0x68)
assert line(3, 3) == (5, 0) and line(3, 4) == (0, 7) and line(3, 4, 9) == (0, 0)
print('KANA OK')
