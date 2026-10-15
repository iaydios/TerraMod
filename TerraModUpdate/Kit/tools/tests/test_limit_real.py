"""Runs the REAL game function Entity.limitModifiedStatus (0x1078E40) of the original and of the patched libil2cpp.so with the real Gugba hook (0x1078E68):
an enemy carrying the DEF-break modifier (mark 4810) must lose the full amount, every other enemy must still be capped at 30 % (original behaviour), and the
original and patched code must agree everywhere except for that one case.   usage: test_limit_real.py <original libil2cpp.so> <patched libil2cpp.so>"""
import sys, os, struct
sys.path.insert(0, os.path.dirname(__file__))
from emu import *
import gugba_native as gn
orig, patched = [open(p, 'rb').read() for p in sys.argv[1:3]]
EM = {}
def machine(blob):
    if id(blob) in EM: return EM[id(blob)]
    m = gn.build({'fx': {}}); e = Emu(m, {'fx': {}})
    e.mapr(0x1078000, 0x1000); e.mu.mem_write(0x1078000, blob[0x1078000:0x1079000])
    e.mapr(0x204f000, 0x1000); e.mu.mem_write(0x204f000, blob[0x204f000:0x2050000])
    e.stub(0xe45978, lambda e: e.ret(struct.unpack('<i', struct.pack('<i', int(e.sf('S0'))))[0] & 0xffffffff))     # Mathf.RoundToInt
    e.stub(0xcb2d2c, lambda e: e.ret(0)); e.stub(0xbef9e8, lambda e: (_ for _ in ()).throw(RuntimeError('NullReference')))
    EM[id(blob)] = e; return e
def run(blob, side, mark, modified, base, lim=0):
    e = machine(blob)
    ent, data = e.alloc(0x400), e.alloc(0x200)
    e.w64(ent + 0x38, data); e.w32(data + 0x2c, side); e.w32(data + 0x28, 1)           # side 1 = enemy, +0x28 == 1 skips the positive-side clamp
    e.w64(ent + 0x268, e.alloc(0x40))
    mods = e.alloc(0x40); arr = e.alloc(0x40); lst = e.alloc(0x40)
    st = e.alloc(0x100); e.w32(st + 0x84, 4810 if mark else 4801); mo = e.alloc(0x80); e.w64(mo + 0x40, st)
    e.w64(ent + 0x48, mods); e.w64(mods + 0x10, lst); e.w32(lst + 0x18, 1); e.w64(lst + 0x10, arr); e.w32(arr + 0x18, 1); e.w64(arr + 0x20, mo)
    e.call(0x1078e40, 0xdead0000, x0=ent, x1=modified, x2=base, x3=lim)
    return struct.unpack('<i', struct.pack('<I', e.reg('W0')))[0]
fail = 0
for side in (1, 0):
    for mark in (0, 1):
        for modified, base in ((1, 100), (50, 100), (120, 100), (4, 400)):
            o = run(orig, side, mark, modified, base); p = run(patched, side, mark, modified, base)
            expect_diff = (side == 1 and mark == 1 and modified < base)
            ok = (o != p) if expect_diff else (o == p)
            if expect_diff: ok = ok and p == 1 if modified == 1 else ok and p <= o
            print('side %d mark %d modified %3d base %3d: original %4d patched %4d %s' % (side, mark, modified, base, o, p, 'OK' if ok else 'FAIL'))
            fail += not ok
print('LIMIT REAL-CODE', 'FAILED' if fail else 'OK'); sys.exit(1 if fail else 0)
