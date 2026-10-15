"""Static callee-saved-register discipline check for every cave of every native module (written 2026-10-13, independent of the scenario tests).

For each cave it follows EVERY path (not only the ones a test happens to run) and proves that on every exit (`ret`, or a branch leaving the cave) the registers
x19-x30 and d8-d15 hold their ENTRY values again and the stack pointer is back at its entry value.  Stack saves/restores are tracked slot by slot
(`stp`/`str`/`ldp`/`ldr` via sp, pre/post-index, `sub/add sp`).  Registers that a hook's displaced original instruction writes on purpose are allowed to differ
at the final jump back into the game.  Calls (`bl`) are assumed to preserve x19-x29 (AAPCS) and clobber x30.
usage: python3 -I check_caves.py <original libil2cpp.so>   (exit code 1 on any violation)"""
import sys, os, re, importlib
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, '..')); sys.path.insert(0, os.path.join(here, '..', 'natives'))
import capstone
from capstone import arm64 as A
md = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM); md.detail = True
so = open(sys.argv[1], 'rb').read()

TRACK = ['x%d' % k for k in range(19, 31)] + ['v%d' % k for k in range(8, 16)]

def norm(n):
    n = {'fp': 'x29', 'lr': 'x30'}.get(n, n)
    m = re.fullmatch(r'[xw](\d+)', n or '')
    if m: return 'x' + m.group(1)
    m = re.fullmatch(r'[dsvqbh](\d+)', n or '')
    if m: return 'v' + m.group(1)
    if n in ('sp', 'wsp'): return 'sp'
    return None

def parse_mem(i):
    """-> (base_name, disp) of the memory operand or None"""
    for op in i.operands:
        if op.type == A.ARM64_OP_MEM:
            return norm(md.reg_name(op.mem.base)), op.mem.disp
    return None

def step(i, st, slots, delta, errs, where):
    """apply one instruction; returns (st, slots, delta) (mutated copies)"""
    mn = i.mnemonic
    rd, wr = i.regs_access()
    wnames = {norm(md.reg_name(r)) for r in wr} - {None}
    mem = parse_mem(i)
    regops = [norm(md.reg_name(op.reg)) for op in i.operands if op.type == A.ARM64_OP_REG]
    txt = i.op_str
    if mem and mem[0] == 'sp' and mn in ('stp', 'str', 'stur', 'ldp', 'ldr', 'ldur'):
        pre = txt.endswith('!')
        post = bool(re.search(r'\],\s*#', txt))
        disp = mem[1]
        if post: disp = 0
        d = delta + disp
        n_regs = 2 if mn in ('stp', 'ldp') else 1
        rs = regops[:n_regs]
        if mn.startswith('st'):
            for k, r in enumerate(rs):
                slots[d + 8 * k] = r if (r in TRACK and st.get(r)) else None
        else:
            for k, r in enumerate(rs):
                if r in TRACK: st[r] = (slots.get(d + 8 * k) == r)
        if pre or post:
            wb = [op for op in i.operands if op.type == A.ARM64_OP_IMM]
            m = re.search(r'#(-?0x[0-9a-fA-F]+|-?\d+)\s*$', txt.rstrip('!'))
            if post:
                delta += int(m.group(1), 0)
            else:
                delta += disp
        return st, slots, delta
    if mn in ('sub', 'add') and regops and regops[0] == 'sp' and i.operands[1].type == A.ARM64_OP_REG and norm(md.reg_name(i.operands[1].reg)) == 'sp' and i.operands[2].type == A.ARM64_OP_IMM:
        delta += i.operands[2].imm * (-1 if mn == 'sub' else 1)
        return st, slots, delta
    if 'sp' in wnames or (regops and regops[0] == 'sp'):
        errs.append('%s: unsupported write to sp: %s %s' % (where, mn, txt)); return st, slots, None
    for r in wnames:
        if r in TRACK: st[r] = False
    if mn in ('bl', 'blr'):
        st['x30'] = False
    return st, slots, delta

def check_cave(name, code, va, allowed_at_exit, is_func, want_delta=0):
    insns = list(md.disasm(code, va))
    by = {i.address: i for i in insns}
    end = va + len(code)
    errs = []
    init = ({r: True for r in TRACK}, {}, 0)
    state = {va: init}
    work = [va]
    exits = []
    def merge(a, new):
        if a not in state:
            state[a] = new; work.append(a); return
        st0, sl0, d0 = state[a]; st1, sl1, d1 = new
        if d0 != d1: errs.append('%#x: stack depth differs between paths (%s vs %s)' % (a, d0, d1)); return
        ch = False
        for r in TRACK:
            if st0[r] and not st1[r]: st0[r] = False; ch = True
        for k in list(sl0):
            if sl0[k] != sl1.get(k): del sl0[k]; ch = True
        if ch: work.append(a)
    steps = 0
    while work:
        a = work.pop(); steps += 1
        if a not in by: continue
        i = by[a]
        st0, sl0, d0 = state[a]
        st, sl, d = dict(st0), dict(sl0), d0
        mem0 = parse_mem(i)
        if (i.mnemonic in ('bl', 'blr') or (mem0 and mem0[0] == 'sp')) and d0 % 16 != 0 and not ('!' in i.op_str):
            errs.append('%#x: sp not 16-byte aligned (offset %d) at %s %s' % (a, d0, i.mnemonic, i.op_str))
        st, sl, d = step(i, st, sl, d, errs, '%#x' % a)
        if d is None: continue
        mn = i.mnemonic
        tgt = None
        if i.operands and i.operands[-1].type == A.ARM64_OP_IMM and (mn in ('b', 'bl') or mn.startswith('b.') or mn in ('cbz', 'cbnz', 'tbz', 'tbnz')):
            tgt = i.operands[-1].imm
        if mn == 'ret':
            exits.append((a, st, d)); continue
        if mn == 'br':
            errs.append('%#x: indirect branch' % a); continue
        if mn == 'b':
            if va <= tgt < end: merge(tgt, (st, sl, d))
            else: exits.append((a, st, d))
            continue
        succ = [a + 4]
        if tgt is not None and mn != 'bl':
            if va <= tgt < end: succ.append(tgt)
            else: exits.append((a, st, d))                 # conditional exit
        if a + 4 >= end:
            errs.append('%#x: runs off the end of the cave' % a); continue
        for s in succ: merge(s, (dict(st), dict(sl), d))
    for a, st, d in exits:
        bad = [r for r in TRACK if not st[r] and r not in allowed_at_exit]
        if bad: errs.append('exit at %#x: not restored: %s' % (a, bad))
        if d != want_delta: errs.append('exit at %#x: stack pointer off by %d (expected %d)' % (a, d - want_delta, want_delta))
    return errs, len(exits)

def regs_written(addr, n):
    out = set(); sp = 0
    for k in range(n):
        i = next(md.disasm(so[addr + 4 * k:addr + 4 * k + 4], addr + 4 * k))
        _, wr = i.regs_access()
        out |= {norm(md.reg_name(r)) for r in wr} - {None}
        mem = parse_mem(i)
        if mem and mem[0] == 'sp' and i.op_str.endswith('!'): sp += mem[1]          # displaced pre-index push: the cave must leave sp moved the same way
    return out, sp

import json
LIVE = json.load(open(os.path.join(here, 'live_regs.json')))
bad_total = 0
for mn in ('gugba_native', 'kana_native', 'macuri_native', 'yapkar_native'):
    mod = importlib.import_module(mn); m = mod.build({'fx': {'fx_tap_gather': 271}})
    caves, sites = m.assemble({'fx': {}})
    intended = getattr(m, 'intended_writes', {})
    hooked = {}                                  # cave name -> (registers allowed to differ at the end, kind, sp change)
    for addr, orig, lines in m.sites:
        first = lines[0].split()
        if first[0] in ('b', 'bl') and first[1].startswith('@') and first[1][1:] in m.caves:
            n = orig.count(';') + 1
            cname = first[1][1:]
            if first[0] == 'b':
                w, spd = regs_written(addr, n)
                free = {r for r in TRACK if r not in set(LIVE[mn][hex(addr)]['live'])}       # not read by the game after the site: free scratch
                hooked[cname] = (w | free | set(intended.get(cname, ())), 'b', spd)
            else:
                hooked[cname] = (set(intended.get(cname, ())), 'bl', 0)
    for name in m.caves:
        va = m.addr[name]
        allowed, kind, spd = hooked.get(name, (set(intended.get(name, ())), None, 0))
        errs, nexit = check_cave(name, caves[va], va, allowed, kind != 'b', spd)
        print('%-7s %-9s %s exits=%d %s' % (mn[:6], name, ('hook-b' if kind == 'b' else 'hook-bl' if kind else 'helper'), nexit, 'OK' if not errs else 'VIOLATIONS'))
        for e in errs:
            print('        ', e); bad_total += 1
print('TOTAL violations:', bad_total)
sys.exit(1 if bad_total else 0)
