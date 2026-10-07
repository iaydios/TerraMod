import os,sys
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
W=os.environ.get('TERRAMOD_WORK','work')  # folder with libil2cpp.so, global-metadata.dat, symmap.json ...
import json,subprocess,sys,re
sym=json.load(open(W+'/symmap.json'))
got={int(k,16):v for k,v in json.load(open(W+'/got2str.json')).items()}
a,b=sys.argv[1],sys.argv[2]
out=subprocess.run(['llvm-objdump','-d','--no-show-raw-insn',f'--start-address={a}',f'--stop-address={b}',W+'/libil2cpp.so'],capture_output=True,text=True).stdout
pend={}
for l in out.splitlines()[6:]:
    ma=re.search(r'adrp\s+(x\d+), 0x([0-9a-f]+)',l)
    if ma: pend[ma.group(1)]=int(ma.group(2),16)
    ml=re.search(r'ldr\s+x\d+, \[(x\d+), #0x([0-9a-f]+)\]',l)
    if ml and ml.group(1) in pend and pend[ml.group(1)]+int(ml.group(2),16) in got: l+='   ; "'+got[pend[ml.group(1)]+int(ml.group(2),16)][:60].replace(chr(10),' ')+'"'
    l=re.sub(r' <[^>]*>','',l)
    m=re.search(r'\bbl?\s+0x([0-9a-f]+)',l)
    if m and hex(int(m.group(1),16)) in sym: l+='   ; '+sym[hex(int(m.group(1),16))]
    print(l)
