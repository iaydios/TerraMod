"""Every module patches only its own bytes: the diffs of the single-module builds are pairwise disjoint and their union is the combined build."""
import sys, os, itertools
here = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(here, '..')); sys.path.insert(0, os.path.join(here, '..', 'natives'))
import nativelib as nl, il2cpp_lite
so_path = sys.argv[1]
so = open(so_path, 'rb').read(); v2o = il2cpp_lite.Elf(so).v2o
ctx = {'fx': {'fx_tap_gather': 271}}
ALL = ['yapkar_native', 'macuri_native', 'kana_native', 'gugba_native']
def diff(b): return {i for i in range(len(so)) if so[i] != b[i]}
def fast_diff(b):
    import numpy as np
    a = np.frombuffer(so, dtype=np.uint8); c = np.frombuffer(b, dtype=np.uint8)
    return set(np.nonzero(a != c)[0].tolist())
singles = {n: fast_diff(nl.apply_natives(so, v2o, [n], dict(ctx))) for n in ALL}
for a, b in itertools.combinations(ALL, 2):
    assert not (singles[a] & singles[b]), (a, b)
    print('%-14s %-14s share 0 patched bytes' % (a, b))
comb = fast_diff(nl.apply_natives(so, v2o, ALL, dict(ctx)))
assert comb == set().union(*singles.values())
for n in ALL:
    for k in range(2, 4):
        for sub in itertools.combinations(ALL, k):
            pass
print('sizes', {n: len(d) for n, d in singles.items()}, 'combined', len(comb))
# any subset equals the union of its members
for k in range(1, 5):
    for sub in itertools.combinations(ALL, k):
        assert fast_diff(nl.apply_natives(so, v2o, list(sub), dict(ctx))) == set().union(*(singles[n] for n in sub)), sub
print('ALL 15 SUBSETS OK: each module patches only its own bytes')
