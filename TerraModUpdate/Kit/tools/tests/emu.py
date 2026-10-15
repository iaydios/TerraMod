"""Shared unicorn harness: mocked Terra Battle structures + hook-based stubs for game functions."""
import sys, os, struct
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..')); sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'natives'))
from unicorn import *
from unicorn.arm64_const import *
import nativelib as nl

R = lambda n: getattr(__import__('unicorn.arm64_const', fromlist=['x']), 'UC_ARM64_REG_' + n)

class Emu:
    def __init__(self, module, ctx=None):
        self.mu = Uc(UC_ARCH_ARM64, UC_MODE_ARM)
        self.pages = set()
        self.stubs = {}                      # addr -> python fn(emu)
        self.module = module
        caves, sites = module.assemble(ctx or {'fx': {}})
        for va, code in caves.items():
            self.mapr(va, len(code)); self.mu.mem_write(va, code)
        self.sites = {a: n for a, e, n in sites}
        self.HEAP = 0x20000000; self.mapr(self.HEAP, 0x400000); self.brk = self.HEAP + 0x10000
        self.STACK = 0x7f000000; self.mapr(self.STACK, 0x10000)
        self.mapr(0xdead0000, 8); self.mu.hook_add(UC_HOOK_CODE, self._hook)
        self.mu.hook_add(UC_HOOK_MEM_UNMAPPED, self._unmapped)
        self.live_hit = set(); self.review = {}
        import atexit; atexit.register(lambda: print('register-preservation check ran on %d of %d hook caves%s' % (len(self.live_hit), len(self.live), '' if len(self.live_hit) == len(self.live) else '   NOT COVERED: ' + ', '.join(chk_name for chk_name in sorted(self.live[a][0] for a in self.live if a not in self.live_hit)))))
        atexit.register(lambda: [print('  REVIEW site %s: cave changed live caller-saved %s' % (k, sorted(v, key=lambda r: (r[0], int(r[1:]))))) for k, v in sorted(self.review.items()) if v])
        self.live = {}                       # cave va -> registers the original game code still needs after this hook (live_regs.json)
        try:
            import json
            lj = json.load(open(os.path.join(os.path.dirname(__file__), 'live_regs.json')))
            for site, d in lj.get(module.name + '_native', {}).items():
                if d['cave'] in self.addr_of(module): self.live[self.addr_of(module)[d['cave']]] = (site, d)
        except FileNotFoundError:
            pass
    @staticmethod
    def addr_of(module): return module.addr
    def mapr(self, a, sz):
        lo, hi = a & ~0xfff, (a + sz + 0xfff) & ~0xfff
        for p in range(lo, hi, 0x1000):
            if p not in self.pages:
                self.mu.mem_map(p, 0x1000); self.pages.add(p)
    def _unmapped(self, mu, access, addr, size, value, ud):
        raise RuntimeError("unmapped access %#x (type %d) pc=%#x" % (addr, access, mu.reg_read(UC_ARM64_REG_PC)))
    def alloc(self, n):
        a = self.brk; self.brk += (n + 15) & ~15; return a
    def w64(self, a, v): self.mu.mem_write(a, struct.pack('<Q', v))
    def w32(self, a, v): self.mu.mem_write(a, struct.pack('<I', v & 0xffffffff))
    def wf(self, a, v): self.mu.mem_write(a, struct.pack('<f', v))
    def r64(self, a): return struct.unpack('<Q', self.mu.mem_read(a, 8))[0]
    def r32(self, a): return struct.unpack('<I', self.mu.mem_read(a, 4))[0]
    def rf(self, a): return struct.unpack('<f', self.mu.mem_read(a, 4))[0]
    def reg(self, n): return self.mu.reg_read(R(n))
    def setreg(self, n, v): self.mu.reg_write(R(n), v)
    def sf(self, n): return struct.unpack('<f', struct.pack('<I', self.reg(n) & 0xffffffff))[0]
    def stub(self, addr, fn):
        self.mapr(addr, 4); self.stubs[addr] = fn
    def ret(self, x0=None):
        if x0 is not None: self.setreg('X0', x0)
        self.setreg('PC', self.reg('X30'))
    def _hook(self, mu, addr, size, ud):
        f = self.stubs.get(addr)
        if f: f(self)
    def call(self, start, stop, **regs):
        """stop: address or list of addresses; returns the address where the run ended"""
        stops = [stop] if isinstance(stop, int) else list(stop)
        self.setreg('SP', self.STACK + 0x8000)
        for k, v in regs.items(): self.setreg(k.upper(), v)
        chk = self.live.get(start)
        CALLEE = ['x%d' % n for n in range(19, 30)] + ['v%d' % n for n in range(8, 16)]
        ALLR = ['x%d' % n for n in range(29)] + ['v%d' % n for n in range(32)]
        rn = lambda r: ('X' if r[0] == 'x' else 'D') + r[1:]
        if chk:                              # every register/flag the game still needs must come back unchanged: give all others sentinel values
            given = {k.lower() for k in regs}
            for r in ALLR:
                if r not in given and ('w' + r[1:]) not in given and (r[0] == 'x' or self.reg(rn(r)) == 0): self.setreg(rn(r), 0x5E570000 + int(r[1:]) * 0x10 + (0 if r[0] == 'x' else 0x1000))
            self.setreg('NZCV', 0xA0000000)
            before = {r: self.reg(rn(r)) for r in ALLR}
            nzcv0 = self.reg('NZCV')
        self.setreg('X30', 0xdead0000)
        self.ended = None
        def mk(a):
            def f(e): e.ended = a; e.mu.emu_stop()
            return f
        saved = {}
        for a in stops:
            self.mapr(a, 4); saved[a] = self.stubs.get(a); self.stubs[a] = mk(a)
        try:
            self.mu.emu_start(start, stops[0] if len(stops) == 1 else 0xdead0000)
        finally:
            for a, f in saved.items():
                if f is None: self.stubs.pop(a, None)
                else: self.stubs[a] = f
        if self.ended is None: self.ended = self.reg('PC')
        if chk:
            self.live_hit.add(start)
            site, d = chk
            allow = getattr(self, 'allow', ())
            changed = {r for r in ALLR if self.reg(rn(r)) != before[r] and r not in allow and r != 'x30'}
            live = set(d['live'])
            hard = sorted((changed & live & set(CALLEE)))                     # callee-saved registers the game (or its caller) still needs: never allowed
            assert not hard, "hook cave at site %s changed callee-saved registers the game still uses: %s" % (site, hard)
            if d['flags']:
                assert self.reg('NZCV') == nzcv0, "hook cave at site %s changed the condition flags the game still reads" % site
            if not d['link']:                # a hooked bl clobbers the caller-saved registers anyway; for a mid-function hook every changed live caller-saved register is reported
                rev = changed & live - set(CALLEE)
                self.review.setdefault(site, set()).update(rev)
        return self.ended

class Game:
    """skill DB, entities, modifiers, battle manager"""
    def __init__(self, e):
        self.e = e; e.mapr(0x2ab3000, 0x1000); e.mapr(0x2ab9000, 0x1000)
        p1, p2, p3, db = e.alloc(16), e.alloc(0x100), e.alloc(0x20), e.alloc(16)
        e.w64(0x2ab34a8, p1); e.w64(p1, p2); e.w64(p2 + 0xa0, p3); e.w64(p3 + 8, db)
        klass, k2 = e.alloc(16), e.alloc(16); e.w64(0x2ab9bb0, k2); e.w64(k2, klass)
        self.skills = {}; self.rev = {}; self.bms = {}
        e.stub(nl.GETTYPE, lambda e: e.ret(self.skills.get(e.reg('X1') & 0xffffffff, 0)))
        e.stub(nl.NEWOBJ, lambda e: e.ret(e.alloc(0x80)))
        def ctor(e):
            m = e.reg('X0'); s = e.reg('X1'); life = e.reg('X3') & 0xffffffff
            e.w64(m + 0x40, s); e.w32(m + 0x18, life); e.w32(m + 0x1c, life); e.mu.mem_write(m + 0x24, bytes(e.mu.mem_read(s + 0x20, 4))); e.ret()
        e.stub(nl.MOD_CTOR, ctor)
        def addmod(e):
            sm = e.reg('X0'); m = e.reg('X1'); lst = e.r64(sm + 0x10); n = e.r32(lst + 0x18); arr = e.r64(lst + 0x10)
            e.w64(arr + 0x20 + 8 * n, m); e.w32(lst + 0x18, n + 1); e.ret()
        e.stub(nl.ADDMOD5, addmod)
    def skill(self, sid, cap, spower=0.0):
        s = self.e.alloc(0x100); self.e.w32(s + 0x84, cap); self.e.wf(s + 0x20, spower)
        self.skills[sid] = s; self.rev[s] = sid; return s
    def ent(self, chr_id, kind, skill_ids, hp=500, dead=0, locked=0, pos=(0, 0)):
        e = self.e
        ent = e.alloc(0x80); cb = e.alloc(0x100); st = e.alloc(0x80); sm = e.alloc(0x40); lst = e.alloc(0x40); arr = e.alloc(0x20 + 8 * 64); ids = e.alloc(0x20 + 4 * 16)
        e.w64(ent + 0x30, cb); e.w64(ent + 0x38, st); e.w64(ent + 0x48, sm)
        e.w32(cb + 0x14, chr_id); e.w32(cb + 0xdc, locked); e.w64(cb + 0xe0, ids); e.w32(ids + 0x18, len(skill_ids))
        for i, s in enumerate(skill_ids): e.w32(ids + 0x20 + 4 * i, s)
        e.w32(st + 0x4c, pos[0]); e.w32(st + 0x50, pos[1]); e.mu.mem_write(st + 0x36, bytes([dead])); e.w32(st + 0x2c, kind); e.w64(st + 0x60, hp)
        e.w64(sm + 0x10, lst); e.w32(lst + 0x18, 0); e.w64(lst + 0x10, arr); e.w32(arr + 0x18, 64)
        return ent
    def mods(self, ent):
        e = self.e; sm = e.r64(ent + 0x48); lst = e.r64(sm + 0x10); n = e.r32(lst + 0x18); arr = e.r64(lst + 0x10)
        return [e.r64(arr + 0x20 + 8 * i) for i in range(n)]
    def desc(self, ent):
        e = self.e
        return [(self.rev.get(e.r64(m + 0x40)), e.rf(m + 0x24), e.r32(m + 0x18)) for m in self.mods(ent)]
    def bm(self, ents, w=5, h=5, magic=0x1234):
        e = self.e
        bm = e.alloc(0x300); arr = e.alloc(0x20 + 8 * w * h); bounds = e.alloc(0x30)
        e.w64(bm + 0x1e8, arr); e.w64(arr + 0x10, bounds); e.w64(bounds, w); e.w64(bounds + 0x10, h)
        for i, x in enumerate(ents): e.w64(arr + 0x20 + 8 * i, x)
        e.w64(bm + 0x1f0, magic); self.bms[bm] = list(ents)
        return bm
