"""Runs the REAL (patched) game code of Entity.SkillDamage from its entry through the hooked spot with the real Gugba/Macuri/Kana caves in place
and checks that the game's own registers come out exactly as they do in the unpatched game.  usage: test_real_splice.py <original libil2cpp.so> <patched libil2cpp.so> [<module>...]"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from emu import *
import importlib, gugba_native as gn, kana_native as kn, macuri_native as mn
orig, patched = [open(p, 'rb').read() for p in sys.argv[1:3]]
mods = {'gugba': gn, 'kana': kn, 'macuri': mn}
which = sys.argv[3:] or list(mods)
TEXT_LO, TEXT_HI = 0x913ed0, 0x204eb40
def run(blob, module, marks_on=False):
    m = module.build({'fx': {'fx_tap_gather': 271}}); e = Emu(m, {'fx': {'fx_tap_gather': 271}}); g = Game(e)
    have = sorted(pg for pg in e.pages if TEXT_LO <= pg < TEXT_HI); cur = TEXT_LO & ~0xfff       # map the code image in a few big chunks (page-by-page mapping is far too slow)
    for pg in have + [(TEXT_HI + 0xfff) & ~0xfff]:
        if pg > cur: e.mu.mem_map(cur, pg - cur); e.pages.update(range(cur, pg, 0x1000))
        cur = pg + 0x1000
    e.mu.mem_write(TEXT_LO, blob[TEXT_LO:TEXT_HI])  # (caves are part of the patched image; the original has none there)
    for pg in (0x2aae000, 0x2a94000, 0x2a64000): e.mapr(pg, 0x1000)
    P = e.alloc(16); e.w32(P, 0x4242); e.w64(0x2aae640, P)
    e.w64(0x2a94f78, 0x1111); e.w64(0x2a64318, 0x2222)
    e.mapr(gn.FLAG_PAGE, 0x1000)
    for a in (gn.ISBOSS, gn.SETHP, gn.EVALUATE, gn.RANDOM_RANGE_I, gn.GETNAME, gn.SHOWMSG, gn.STARTCO, gn.GETATT, kn.IS_MAGIC if hasattr(kn, 'IS_MAGIC') else gn.ISBOSS):
        e.stub(a, lambda e: e.ret(0))
    S = g.skill(99, 0, 0.0)
    if marks_on:                             # both fighters carry every skill mark of the module (buddy marks included), so every cave runs its full path
        ids = []
        for i, mk in enumerate(sorted(module.MARKS)):
            g.skill(100 + i, mk); ids.append(100 + i)
        for a in (nl.GETHP, nl.GETATK, nl.HEAL):
            e.stub(a, lambda e: e.ret(0))
        vic = g.ent(1291, 0, ids, hp=500); att = g.ent(900, 1, ids)
    else:
        vic = g.ent(1291, 0, [10], hp=500); att = g.ent(900, 1, [99])
    out = {}
    for dmg in (0, 1, 50):                   # damage 0 skips most of the caves, damage >= 1 runs all of them
        e.call(0x10917a8, 0x1091800, x0=vic, x1=dmg, x2=S, x3=att, x4=7)
        out[dmg] = (e.reg('X19'), e.reg('W23'), e.reg('X21'), e.reg('W24'), e.reg('X28'), e.reg('X20'), e.reg('X22'))
    return out
fail = 0
for name in which:
  for marks_on in (False, True):
    want = run(orig, mods[name], marks_on); got = run(patched, mods[name], marks_on)
    for dmg in want:
        # w23 (= the damage argument) may differ on purpose when a hook changes the damage; everything else must match exactly
        w = list(want[dmg]); gt = list(got[dmg]); w[1] = gt[1] = None
        ok = w == gt
        print('%-7s %-9s damage %-3d %s' % (name, 'marks on' if marks_on else 'no marks', dmg, 'OK' if ok else 'MISMATCH  original=%s  patched=%s' % ([hex(x) if x is not None else None for x in w], [hex(x) if x is not None else None for x in gt])))
        fail += not ok
print('REAL-CODE SPLICE', 'FAILED' if fail else 'OK')
sys.exit(1 if fail else 0)
