import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from emu import *
import macuri_native as mn
m = mn.build({}); e = Emu(m); g = Game(e); e.allow = {'x1'}      # the damage argument is changed on purpose (it is the value the hook is there to alter)
heals = []
e.stub(mn.GETATK, lambda e: e.ret(200))
e.stub(mn.HEAL, lambda e: (heals.append((e.reg('X0'), e.reg('X1') & 0xffffffff)), e.ret()))
HP = {}
e.stub(mn.HPDEC, lambda e: e.ret(e.reg('X1')))
e.stub(mn.GETHP, lambda e: (e.setreg('S0', struct.unpack('<I', struct.pack('<f', 1000.0))[0]), e.ret()))
for a in (mn.SITE_DMG_BACK, mn.SITE_SAH_BACK, mn.SITE_POW_BACK): e.mapr(a, 4)
e.mapr(mn.FLAG_PAGE, 0x1000)
for sid, cap in [(10, 5101), (11, 5102), (12, 5110), (13, 5120), (14, 5130), (15, 5140), (50, 0), (51, 4242)]: g.skill(sid, cap)
mac = g.ent(1289, 0, [10, 12, 13, 14], hp=900); buddy = g.ent(1289, 0, [15, 12], hp=900)
foe = g.ent(900, 1, [50], hp=900); foe2 = g.ent(901, 1, [50], hp=900)
nm = {mac: 'mac', foe: 'foe', foe2: 'foe2', buddy: 'thirst'}
def dmg(victim, attacker, d, sk=50):
    heals.clear()
    e.call(m.addr['dmg'], mn.SITE_DMG_BACK, x0=victim, x1=d, x2=g.skills[sk], x3=attacker, x4=0)
    assert e.reg('X8') == 0x2aae000 and e.reg('SP') == e.STACK + 0x8000 and e.reg('X0') == victim and e.reg('X3') == attacker
    return e.reg('X1') & 0xffffffff
# --- Mechanical Reflect HP lock (victim = owner with mark 5101): HPDEC stub = [data+0x60]
def flag(): return e.mu.mem_read(mn.FLAG_PAGE + mn.FLAG_OFF, 1)[0]
def sethp(ent, hp): e.w64(e.r64(ent + 0x38) + 0x60, hp)
def lock_reset(): e.mu.mem_write(mn.FLAG_PAGE + mn.FLAG_OFF, bytes([0]))
sethp(mac, 900); lock_reset()
assert dmg(mac, foe, 300) == 300 and flag() == 0                    # not lethal
assert dmg(mac, foe, 899) == 899 and flag() == 1                    # leaves exactly 1 HP -> lock on
lock_reset(); assert dmg(mac, foe, 900) == 899 and flag() == 1      # lethal -> clamped to 899, 1 HP left
sethp(mac, 1)
assert dmg(mac, foe, 500) == 0 and heals == []                      # lock held: 2nd hit of the same attack does nothing
assert dmg(mac, foe, 500) == 0
lock_reset(); assert dmg(mac, foe, 500) == 500 and flag() == 0      # next attack (flag released) kills
sethp(mac, 900); assert dmg(foe, mac, 5000) == 5000                  # owner is the attacker, victim has no mark -> untouched
sethp(mac, 900); assert dmg(buddy, foe, 5000) == 5000 and flag() == 0   # victim without 5101
assert dmg(mac, foe, 0) == 0 and dmg(mac, foe, -5) == (-5 & 0xffffffff)
# --- Thirst for blood: attacker with mark 5140 heals 0.5 ATK (=100) per damaging hit on someone else
assert dmg(foe, buddy, 120) == 120 and heals == [(buddy, 100)], heals
assert dmg(foe, mac, 120) == 120 and heals == []                   # no mark -> no heal
assert dmg(buddy, buddy, 120) == 120 and heals == []               # self hit
e.mu.mem_write(e.r64(buddy + 0x38) + 0x36, bytes([1])); assert dmg(foe, buddy, 5) == 5 and heals == []   # dead attacker
e.mu.mem_write(e.r64(buddy + 0x38) + 0x36, bytes([0]))
sm = e.r64(mac + 0x48); lst = e.r64(sm + 0x10); e.w32(lst + 0x18, 0)
assert dmg(foe, None or 0, 9) == 9
# --- Spear Tomb x3
def run_sah(ids):
    lst = e.alloc(0x20 + 4 * 16); e.w32(lst + 0x18, len(ids)); arr = e.alloc(0x20 + 4 * 64); e.w64(lst + 0x10, arr); e.w32(arr + 0x18, 64)
    for i, s in enumerate(ids): e.w32(arr + 0x20 + 4 * i, s)
    obj = e.alloc(0x40); e.w64(obj + 0x18, lst); added = []
    def ladd(e):
        n = e.r32(e.reg('X0') + 0x18); a = e.r64(e.reg('X0') + 0x10); e.w32(a + 0x20 + 4 * n, e.reg('X1')); e.w32(e.reg('X0') + 0x18, n + 1); e.ret()
    e.stub(nl.LIST_ADD, ladd)
    e.mapr(0x2ad5000, 0x1000); e.mapr(0x2ac1000, 0x1000); e.w64(0x2ad5848, e.alloc(16))
    e.call(m.addr['sah'], mn.SITE_SAH_BACK, x19=obj)
    assert e.reg('X8') == 0x2ac1000 and e.reg('X19') == obj
    n = e.r32(lst + 0x18); arr = e.r64(lst + 0x10)
    return [e.r32(arr + 0x20 + 4 * i) for i in range(n)]
assert run_sah([12]) == [12, 12, 12]
assert run_sah([14, 12, 13]) == [14, 12, 13, 12, 12]
assert run_sah([50, 14]) == [50, 14] and run_sah([]) == []
# --- Coercion
def pw(att, tgt, skill, hp, s9=2.0, s10=1.0):
    e.w64(e.r64(tgt + 0x38) + 0x60, hp)
    e.setreg('S9', struct.unpack('<I', struct.pack('<f', s9))[0]); e.setreg('S10', struct.unpack('<I', struct.pack('<f', s10))[0])
    e.call(m.addr['pow'], mn.SITE_POW_BACK, x19=att, x20=tgt, x21=g.skills[skill], x22=0x1111, x23=0x2222, x26=0x3333, x28=0x4444)
    assert (e.reg('X22'), e.reg('X23'), e.reg('X26'), e.reg('X28')) == (0x1111, 0x2222, 0x3333, 0x4444)
    return e.sf('S9')
assert pw(mac, foe, 50, 329) == 3.0                    # 329 < 330 -> x1.5   (2.0 * 1.5)
assert pw(mac, foe, 50, 330) == 2.0                    # exactly 33% -> no bonus (strictly below)
assert pw(mac, foe, 14, 100) == 2.0                    # Ten Thousand Spears excluded
assert pw(foe2, foe, 50, 100) == 2.0                   # attacker without Coercion
assert pw(mac, foe, 12, 1) == 3.0                      # spear tomb hits count too
# --- flag released at the start of a SkillAttack
e.mu.mem_write(mn.FLAG_PAGE + mn.FLAG_OFF, bytes([1])); run_sah([50]); assert flag() == 0
# --- Mechanical Reflect kill: counter skill (mark 5101) kills -> kill counter +1 and full heal; reflect damage bonus x(1+0.25*kills)
assert pw(mac, foe, 50, 1000) == 2.0
sethp(foe, 100); heals.clear(); assert dmg(foe, mac, 150, 10) == 150
assert heals == [(mac, 1000)], heals
assert pw(mac, foe, 50, 1000) == 2.5                                 # 1 kill -> x1.25
sethp(foe, 500); heals.clear(); assert dmg(foe, mac, 150, 10) == 150 and heals == []     # not lethal -> no kill
sethp(foe, 100); assert dmg(foe, mac, 100, 10) == 100 and heals == [(mac, 1000)]      # exactly lethal
assert pw(mac, foe, 50, 1000) == 3.0                                 # 2 kills -> x1.5
assert pw(buddy, foe, 50, 1000) == 2.0                               # no mark 5101 -> no bonus
sethp(foe, 100); heals.clear(); assert dmg(foe, mac, 150, 50) == 150 and heals == []     # other skill (no mark) -> no kill credit
print('MACURI OK')
