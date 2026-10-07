import os,sys
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
W=os.environ.get('TERRAMOD_WORK','work')  # folder with libil2cpp.so, global-metadata.dat, symmap.json ...
import json,re,sys,bisect
sym=json.load(open(W+'/symmap.json')); addrs=sorted(int(k,16) for k in sym)
f=json.load(open(W+'/fullmap.json'))
tg={}
for n in sys.argv[1:]:
    for a in f.get(n,[]): tg[int(a,16)]=n
pat=re.compile(r'^\s*([0-9a-f]+):\s+bl?\s+0x([0-9a-f]+)')
for l in open(W+'/full.s'):
    m=pat.match(l)
    if m and int(m.group(2),16) in tg:
        a=int(m.group(1),16); i=bisect.bisect_right(addrs,a)-1
        print(tg[int(m.group(2),16)],'<-',sym[hex(addrs[i])],hex(a))
