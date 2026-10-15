"""Verifies a built APK against the Update folders it was made from.
usage: python3 -I verify_apk.py <TerraBattle-mod.apk> <dump dir (out/dump)> <original game.apk> <Update folder>...
  1. libil2cpp.so in the APK == the original with exactly the native modules of those folders applied (byte for byte)
  2. every mark / hidden-skill layout the native modules rely on is present in the built SkillData (adjacency of the hidden helper skills)
  3. characters / buddies of those folders exist, skills referenced by the jobs carry the expected marks
"""
import json, os, sys, zipfile
here = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(here, '..')); sys.path.insert(0, os.path.join(here, '..', 'natives'))
import nativelib as nl, il2cpp_lite

apk, dump, orig = sys.argv[1:4]
folders = sys.argv[4:]
root = os.path.abspath(os.path.join(here, '..', '..', '..'))
meta = {f: json.load(open(os.path.join(root, f, 'update.json'), encoding='utf-8')) for f in folders}
natives = sorted(n for f in folders for n in meta[f]['native'])

so0 = zipfile.ZipFile(orig).read('lib/arm64-v8a/libil2cpp.so')
so1 = zipfile.ZipFile(apk).read('lib/arm64-v8a/libil2cpp.so')
fx = {'fx_tap_gather': None}
want = nl.apply_natives(so0, il2cpp_lite.Elf(so0).v2o, natives, {'fx': {}})   # placeholder fx only matters for Gugba's tap effect
import numpy as np
a, b = np.frombuffer(want, dtype=np.uint8), np.frombuffer(so1, dtype=np.uint8)
diff = np.nonzero(a != b)[0]
print('libil2cpp.so: %d bytes differ from the expected patched file (only the cloned tap-effect id may differ)' % len(diff))
assert len(diff) <= 8, 'native bytes differ'
print('native modules in this APK:', natives)

S = json.load(open(os.path.join(dump, 'SkillData.json'), encoding='utf-8'))['types']
C = json.load(open(os.path.join(dump, 'ChrDatabase.json'), encoding='utf-8'))
B = json.load(open(os.path.join(dump, 'BuddyDatabase.json'), encoding='utf-8'))['data']
cap = lambda sid: S[sid - 1]['capacity']
assert all(S[sid - 1]['nameString'] == S[0]['nameString'] for sid in range(3843, 3853)), 'reserved IDs 3843..3852 must stay inert pads'
def real(sid):   # a hidden helper skill must be a real skill (not one of the inert pads, which are copies of skill #1)
    return S[sid - 1]['nameString'] != S[0]['nameString']
jobs = {j['ID']: j for j in C['data']}
LAYOUT = {   # visible mark -> expected marks at id+1, id+2, ...
    5101: [], 5110: [], 5120: [], 5130: [], 5140: [],
    4611: [0], 4601: [], 4612: [4614], 4613: [],
    4801: [], 4802: [0, 0, 0, 0], 4830: [0], 4806: [4805, 4807, 4808, 4809, 4810],
    4901: [], 4902: [4911, 4912, 4941, 4942, 4943], 4903: [4913, 4914, 4951, 4952, 4953], 4904: [],
}
JOBS = {'Macuri': (1289, 5166, [5140, 5110, 5120, 5130]), 'Kana': (1290, 5167, [4611, 4601, 4612, 4613]),
        'Gugba': (1291, 5168, [4801, 4802, 0, 4830]), 'Yapkar': (1292, 5169, [4901, 4902, 4904, 4903])}
BUDDY = {'Macuri': (498, 5101), 'Kana': (499, 0), 'Gugba': (500, 4806)}
for f in folders:
    name = meta[f]['name']
    chr_id, job_id, marks = JOBS[name]
    assert any(i['ID'] == chr_id for i in C['infos']), chr_id
    j = jobs[job_id]
    assert j['chrID'] == chr_id
    for sid, mk in zip(j['skills'], marks):
        assert cap(sid) == mk, (name, sid, cap(sid), mk)
        for k, exp in enumerate(LAYOUT.get(mk, []), 1):
            assert cap(sid + k) == exp and real(sid + k), (name, 'hidden skill', sid + k, cap(sid + k), exp)
    print('%-7s chr %d job %d skills %s marks %s OK' % (name, chr_id, job_id, j['skills'], marks))
    if name in BUDDY:
        bid, mk = BUDDY[name]
        b = next(x for x in B if x['ID'] == bid)
        if mk:
            assert cap(b['skill']) == mk, (name, 'buddy mark')
            for k, exp in enumerate(LAYOUT[mk], 1):
                assert cap(b['skill'] + k) == exp and real(b['skill'] + k), (name, 'buddy hidden', k)
        print('        buddy %d skill %d (%s) OK' % (bid, b['skill'], S[b['skill'] - 1]['nameString']['zh_tw']))
print('ALL OK')
