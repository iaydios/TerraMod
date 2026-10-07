import os,sys
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
W=os.environ.get('TERRAMOD_WORK','work')  # folder with libil2cpp.so, global-metadata.dat, symmap.json ...
import json,sys,bisect,subprocess,re
sym=json.load(open(W+'/symmap.json'))
addrs=sorted(int(k,16) for k in sym)
inv={}
for k,v in sym.items(): inv.setdefault(v,[]).append(int(k,16))
SKIP=re.compile(r'^(UnityEngine|System|Mono|il2cpp|UILabel|UIWidget|UISprite|UIBasicSprite|NGUI|UIRect|UITweener|TweenAlpha|BetterList|UIPanel|DG\.|MoonSharp|Debug::|AudioController|StringSet::GetUIString|AutoVerify|LiteEncrypted|EncryptedString|Encrypted)')
def calls(a):
    i=bisect.bisect_right(addrs,a); b=addrs[i]
    out=subprocess.run(['llvm-objdump','-d','--no-show-raw-insn',f'--start-address={hex(a)}',f'--stop-address={hex(b)}',W+'/libil2cpp.so'],capture_output=True,text=True).stdout
    r=[]
    for m in re.finditer(r'\bbl?\s+0x([0-9a-f]+)',out):
        t=int(m.group(1),16)
        if hex(t) in sym and not (a<=t<b): r.append(t)
    return r
root=sys.argv[1]; depth=int(sys.argv[2])
if root.startswith("0x"): inv[root]=[int(root,16)]; sym.setdefault(root,root)
seen=set()
def walk(a,d,ind):
    n=sym[hex(a)]
    print('  '*ind+n)
    if a in seen or d==0: return
    seen.add(a)
    for t in dict.fromkeys(calls(a)):
        if SKIP.match(sym[hex(t)]): continue
        walk(t,d-1,ind+1)
for a in inv[root]: walk(a,depth,0)
