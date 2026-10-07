import os,sys
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
W=os.environ.get('TERRAMOD_WORK','work')  # folder with libil2cpp.so, global-metadata.dat, symmap.json ...
import re,struct,sys,json
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
import il2cpp_lite as L
so=open(W+'/libil2cpp.so','rb').read(); E=L.Elf(so)
def rd(va,fmt): return struct.unpack_from(fmt,so,E.v2o(va))[0]
lines=open(W+'/pe.s').read().splitlines()
ins={}; order=[]
for l in lines:
    m=re.match(r'\s*([0-9a-f]+):\s+(\S+)\s*(.*?)(\s+;.*)?$',l)
    if m:
        a=int(m.group(1),16); ins[a]=(m.group(2),m.group(3),(m.group(4) or '').strip()); order.append(a)
nxt={order[i]:order[i+1] for i in range(len(order)-1)}; nxt[order[-1]]=None
FIELDS={0x7c:int(sys.argv[1]),0x28:int(sys.argv[2]),0x2c:0,0x54:0,0x58:10,0x80:4242,0x70:1}
R={}; flags=None
pc=0x10120b8
# start state: assume iterator state at start (x19+0x44?) -> we just start at the effID dispatch block
pc=int(sys.argv[3],16) if len(sys.argv)>3 else 0x1012270
steps=0
def val(op):
    op=op.strip()
    if op.startswith('#'): return int(op[1:],0)
    if op in('wzr','xzr'): return 0
    return R.get(op.replace('x','w'),None)
while steps<3000:
    steps+=1
    mn,ops,cm=ins[pc]
    if cm and 'SkillEvaluator' in cm: print('CALL',hex(pc),cm); break
    a=[o.strip() for o in re.split(r',(?![^\[]*\])',ops)]
    newpc=nxt[pc]
    if mn=='ldr' or mn=='ldrsw':
        m=re.match(r'\[(x\d+), #(0x[0-9a-f]+)\]',a[1])
        if m and m.group(1)=='x19' and int(m.group(2),16)==0x10: R['skill_'+a[0]]=1
        elif m and m.group(1)=='x19' and int(m.group(2),16)==0x28: R[a[0].replace('x','w')]=FIELDS[0x7c]
        elif m and R.get('skill_'+m.group(1)) and int(m.group(2),16) in FIELDS: R[a[0].replace('x','w')]=FIELDS[int(m.group(2),16)]
        m2=re.match(r'\[(x\d+), (w|x)(\d+), (sxtw|lsl) #2\]',a[1])
        if m2:
            base=R.get('addr_'+m2.group(1)); idx=R.get('w'+m2.group(3))
            v=rd(base+4*idx,'<i'); R[a[0].replace('x','w')]=v; R['tblbase_'+a[0].replace('w','x')]=base
    elif mn=='adrp': R['addr_'+a[0]]=int(a[1],16)
    elif mn=='add' and a[0].startswith('w') and a[2].startswith('#'):
        v=val(a[1]); R[a[0]]=None if v is None else v+int(a[2][1:],0)
    elif mn=='add' and a[0].startswith('x') and a[1]==a[0] and a[2].startswith('#'):
        if 'addr_'+a[0] in R: R['addr_'+a[0]]+=int(a[2][1:],0)
    elif mn=='add' and len(a)==3 and a[0]=='x8' and a[2]=='x10' :
        R['jmp']=R['addr_x10']+R['w8']
    elif mn=='add' and len(a)==3 and a[0]=='x8' and a[2]=='x9' :
        R['jmp']=R['addr_x9']+R['w8']
    elif mn=='sub' and a[2].startswith('#'):
        v=val(a[1]); R[a[0].replace('x','w')]=None if v is None else v-int(a[2][1:],0)
    elif mn=='str': pass
    elif mn=='cmp':
        x=val(a[0]); y=val(a[1]); flags=None if x is None or y is None else (x,y)
    elif mn.startswith('b.'):
        c=mn[2:]; x,y=flags
        t={'eq':x==y,'ne':x!=y,'hi':(x&0xffffffff)>(y&0xffffffff),'ls':(x&0xffffffff)<=(y&0xffffffff),'lo':(x&0xffffffff)<(y&0xffffffff),'hs':(x&0xffffffff)>=(y&0xffffffff),'gt':x>y,'lt':x<y,'ge':x>=y,'le':x<=y}[c]
        if t: newpc=int(a[0],16)
    elif mn=='b': newpc=int(a[0],16)
    elif mn=='br': newpc=R['jmp']; print('  br ->',hex(newpc))
    elif mn in('cbnz','cbz'):
        v=R.get(a[0].replace('x','w'))
        if v is None: t=(mn=='cbnz')
        else: t=(v!=0) if mn=='cbnz' else (v==0)
        if t: newpc=int(a[1],16)
    elif mn in('tbz','tbnz'): pass
    elif mn=='and' and a[2].startswith('#'):
        v=val(a[1]); R[a[0].replace('x','w')]=None if v is None else (v & int(a[2][1:],0))
    elif mn=='csel':
        x,y=flags; c=a[3]
        t={'eq':x==y,'ne':x!=y,'hi':(x&0xffffffff)>(y&0xffffffff),'lo':(x&0xffffffff)<(y&0xffffffff),'ge':x>=y,'lt':x<y,'gt':x>y,'le':x<=y}[c]
        R[a[0].replace('x','w')]=val(a[1]) if t else val(a[2])
    elif mn=='mov' and a[1].startswith('w') and a[0].startswith('w'): R[a[0]]=R.get(a[1])
    if mn.startswith("b") or mn=="br": print("  ",hex(pc),mn,ops,"->",hex(newpc) if newpc else None)
    if newpc is None: break
    pc=newpc
print('end',hex(pc),steps)
