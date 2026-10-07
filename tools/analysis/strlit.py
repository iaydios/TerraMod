import os,sys
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
W=os.environ.get('TERRAMOD_WORK','work')  # folder with libil2cpp.so, global-metadata.dat, symmap.json ...
import il2cpp_lite as L, struct, json, random
m=open(W+'/global-metadata.dat','rb').read(); so=open(W+'/libil2cpp.so','rb').read()
M=L.Meta(m); E_=L.Elf(so)
h=struct.unpack_from("<%di"%64,m,8)
upo,ups=h[48],h[49]
pairs=[struct.unpack_from('<II',m,upo+8*i) for i in range(ups//8)]
slo,sls=M.sec['stringLiteral']; sdo,sds=M.sec['stringLiteralData']
def lit(i):
    ln,off=struct.unpack_from('<II',m,slo+8*i); return m[sdo+off:sdo+off+ln].decode('utf-8','replace')
best=0x28f5ea0
slot2str={}
for dst,src in pairs:
    if src>>29==5:
        slot2str[E_.relocs[best+8*dst]]=lit(src&0x1fffffff)
# map GOT entries (pointer-to-slot) too
got={}
for k,v in E_.relocs.items():
    if v in slot2str: got[k]=slot2str[v]
json.dump({hex(k):v for k,v in got.items()},open(W+'/got2str.json','w'),ensure_ascii=False)
print(len(slot2str),len(got), got.get(0x2acaaf8))
