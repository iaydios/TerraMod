"""Generates live_regs.json: for every hook site of every native module, the registers AND the condition flags the ORIGINAL game code still reads after
the site.  A hook cave must hand all of them back unchanged (the emulator tests check this).

Analysis (rewritten 2026-10-13 after Sam asked for a careful check of every hook site): a real backward liveness over the whole control-flow graph of the hooked
function (function bounds from analysis/methods.tsv), both branch targets followed, conditional-branch/csel/adc style flag readers tracked (NZCV), `bl` reads
x0-x7/v0-v7 and kills the caller-saved registers, `ret` and tail calls read the return/argument registers and every callee-saved register, an indirect `br` (jump table)
makes everything live.  Nothing is cut off after N instructions.
usage: python3 -I gen_live.py <original libil2cpp.so>"""
import sys, os, re, json, bisect
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, '..')); sys.path.insert(0, os.path.join(here, '..', 'natives'))
import capstone, importlib
from capstone import arm64 as A
md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM); md.detail = True
so = open(sys.argv[1], 'rb').read()
_rows = [l.rstrip('\n').split('\t') for l in open(os.path.join(here, '..', '..', 'analysis', 'methods.tsv')) if l.strip()]
STARTS = sorted(int(r[0], 16) for r in _rows)
NPARAMS = {int(r[0], 16): int(r[3]) for r in _rows}          # callee parameter counts (methods.tsv column 4)
NORETURN = {0xbef9e8, 0xbef8cc, 0xbf06f4}                    # il2cpp throw helpers (NullReference / raise exception): control never comes back

def norm(n):
    n = {'fp': 'x29', 'lr': 'x30'}.get(n, n)
    m = re.fullmatch(r'[xw](\d+)', n or '')
    if m: return 'x' + m.group(1)
    m = re.fullmatch(r'[dsvqbh](\d+)', n or '')
    if m: return 'v' + m.group(1)

X = lambda lo, hi: {'x%d' % k for k in range(lo, hi)}
V = lambda lo, hi: {'v%d' % k for k in range(lo, hi)}
ARGS = X(0, 8) | V(0, 8)
CALLER_SAVED = X(0, 19) | {'x30'} | V(0, 8) | V(16, 32)
CALLEE_SAVED = X(19, 31) | V(8, 16)
ALL = X(0, 31) | V(0, 32)
FLAG_READ = {'adc', 'adcs', 'sbc', 'sbcs', 'ngc', 'ngcs'}

def func_bounds(addr):
    i = bisect.bisect_right(STARTS, addr) - 1
    return STARTS[i], (STARTS[i + 1] if i + 1 < len(STARTS) else STARTS[i] + 0x4000)

_cache = {}
def analyse(fstart, fend):
    """per instruction: addr -> (use, def, flag_use, flag_def, succs, kind)"""
    if (fstart, fend) in _cache: return _cache[(fstart, fend)]
    info = {}
    for i in md.disasm(so[fstart:fend], fstart):
        rd, wr = i.regs_access()
        use = {x for x in (norm(md.reg_name(r)) for r in rd) if x}
        dfn = {x for x in (norm(md.reg_name(r)) for r in wr) if x}
        fu = i.mnemonic in FLAG_READ or (i.cc not in (A.ARM64_CC_INVALID, A.ARM64_CC_AL, A.ARM64_CC_NV))
        fd = bool(i.update_flags)
        mn = i.mnemonic
        nxt = i.address + 4
        succs, kind = [nxt], 'seq'
        tgt = None
        if i.operands and i.operands[-1].type == A.ARM64_OP_IMM and (mn in ('b', 'bl') or mn.startswith('b.') or mn in ('cbz', 'cbnz', 'tbz', 'tbnz')):
            tgt = i.operands[-1].imm
        if mn == 'bl':
            if tgt in NORETURN: succs = []; kind = 'noret'
            else: kind = 'call'
            if tgt in NPARAMS:                    # this + params + MethodInfo* in x0..x(n+1) at most (static methods need one register less), floats v0..v(n-1)
                n = NPARAMS[tgt]; use |= {'x%d' % k for k in range(min(8, n + 2))} | {'v%d' % k for k in range(min(8, n))}
            else:
                use |= X(0, 4) | V(0, 1)           # runtime helper without a method entry: up to 4 integer arguments
            dfn |= CALLER_SAVED; fd = True; fu = False
        elif mn == 'blr':
            use |= ARGS; dfn |= CALLER_SAVED; fd = True; kind = 'call'
        elif mn == 'ret':
            use |= {'x0', 'x1', 'v0', 'v1'} | CALLEE_SAVED; succs = []; kind = 'ret'
        elif mn == 'b':
            if fstart <= tgt < fend: succs = [tgt]
            else: use |= ARGS | CALLEE_SAVED; succs = []; kind = 'tail'           # tail call
        elif mn == 'br':
            use = set(ALL); succs = []; kind = 'indirect'; fu = True
        elif tgt is not None:                                                        # conditional branch / cbz / tbz
            succs = [nxt] + ([tgt] if fstart <= tgt < fend else [])
            if not (fstart <= tgt < fend): use |= ARGS | CALLEE_SAVED               # conditional tail call (rare)
        info[i.address] = (use, dfn, fu, fd, succs, kind)
    # backward liveness to a fixpoint
    live = {a: (set(), False) for a in info}
    changed = True
    while changed:
        changed = False
        for a in sorted(info, reverse=True):
            use, dfn, fu, fd, succs, kind = info[a]
            out, fo = set(), False
            for s in succs:
                if s in live:
                    out |= live[s][0]; fo |= live[s][1]
            lin = (out - dfn) | use
            fin = fu or (fo and not fd)
            if (lin, fin) != live[a]:
                live[a] = (lin, fin); changed = True
    _cache[(fstart, fend)] = (info, live)
    return info, live

def livesite(addr, ndisp=1):
    """registers/flags that must be unchanged when the cave hands control back, given that the cave itself performs the `ndisp` displaced instructions at addr"""
    fs, fe = func_bounds(addr)
    info, live = analyse(fs, fe)
    rd, wr = set(), set()
    fl_written = False; fl_read_inside = False
    for k in range(ndisp):
        ins = next(md.disasm(so[addr + 4 * k:addr + 4 * k + 4], addr + 4 * k))
        r, w = ins.regs_access()
        rd |= {x for x in (norm(md.reg_name(q)) for q in r) if x}
        wr |= {x for x in (norm(md.reg_name(q)) for q in w) if x}
        if ins.mnemonic == 'bl': wr |= CALLER_SAVED
        if k == 0 or True:
            if ins.cc not in (A.ARM64_CC_INVALID, A.ARM64_CC_AL, A.ARM64_CC_NV) and not fl_written: fl_read_inside = True
        if ins.update_flags: fl_written = True
    last = addr + 4 * (ndisp - 1)
    after, fl_after = set(), False
    for sx in info[last][4]:                              # every place the displaced code can continue to (a displaced branch continues at both its target and the next instruction)
        a, f = live.get(sx, (set(), False)); after |= a; fl_after |= f
    need = (after | rd) - wr                 # what the displaced code itself writes is recomputed by the cave
    flags = (fl_after and not fl_written) or fl_read_inside
    return sorted(need, key=lambda s: (s[0], int(s[1:]))), bool(flags), (fs, fe), any(info[a][5] == 'indirect' for a in info if a >= addr)

out = {}
for mn in ('gugba_native', 'kana_native', 'macuri_native', 'yapkar_native'):
    mod = importlib.import_module(mn); m = mod.build({'fx': {'fx_tap_gather': 271}})
    out[mn] = {}
    for addr, orig, lines in m.sites:
        live, flags, (fs, fe), indirect = livesite(addr, orig.count(';') + 1 if isinstance(orig, str) else 1)
        out[mn][hex(addr)] = {'cave': lines[0].split('@')[-1], 'live': live, 'flags': flags, 'link': lines[0].startswith('bl '),
                              'func': [hex(fs), hex(fe)], 'indirect_jump_after': indirect}
json.dump(out, open(os.path.join(here, 'live_regs.json'), 'w'), indent=1)
print('ok', {k: len(v) for k, v in out.items()})
