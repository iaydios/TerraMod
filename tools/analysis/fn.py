import os,sys
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
W=os.environ.get('TERRAMOD_WORK','work')  # folder with libil2cpp.so, global-metadata.dat, symmap.json ...
import json,sys,bisect,subprocess
sym=json.load(open(W+'/symmap.json'))
inv={}
for k,v in sym.items(): inv.setdefault(v,[]).append(int(k,16))
addrs=sorted(int(k,16) for k in sym)
def rng(name):
    out=[]
    for a in inv.get(name,[]):
        i=bisect.bisect_right(addrs,a); out.append((a,addrs[i]))
    return out
if __name__=='__main__':
    for n in sys.argv[1:]:
        for a,b in rng(n):
            print('=====',n,hex(a),hex(b))
            print(subprocess.run(['python3',os.path.join(os.path.dirname(os.path.abspath(__file__)),'disasm.py'),hex(a),hex(b)],capture_output=True,text=True).stdout)
