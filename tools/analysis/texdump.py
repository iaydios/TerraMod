import os,sys
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..'))
W=os.environ.get('TERRAMOD_WORK','work')  # folder with libil2cpp.so, global-metadata.dat, symmap.json ...
import sys,zipfile,os,glob,struct
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..')); 
import texture2ddecoder as T
from PIL import Image
from assets import decrypt_enca,serialized_objects,texture_info
from mbcodec import load_tables
from unityfs import Bundle
meta=open(W+'/global-metadata.dat','rb').read()
inv,fwd=load_tables(meta)
def dump(p,out):
    b=Bundle(decrypt_enca(open(p,'rb').read(),inv)); (cab,)=b.order; data=b.files[cab][0]
    for pid,cid,od in serialized_objects(data):
        if cid==28:
            ti=texture_info(od); w,h,f=ti['width'],ti['height'],ti['format']
            k=od.rfind(struct.pack('<i',ti['size'])); px=od[k+4:k+4+ti['size']]
            if f==4: im=Image.frombytes('RGBA',(w,h),px)
            elif f==3: im=Image.frombytes('RGB',(w,h),px)
            elif f==47: im=Image.frombytes('RGBA',(w,h),T.decode_etc2a8(px,w,h),'raw','BGRA')
            elif f==34: im=Image.frombytes('RGBA',(w,h),T.decode_etc1(px,w,h),'raw','BGRA')
            elif f==45: im=Image.frombytes('RGBA',(w,h),T.decode_etc2(px,w,h),'raw','BGRA')
            else: print('fmt',f); continue
            im=im.transpose(Image.FLIP_TOP_BOTTOM); im.save(out); print(os.path.basename(p),ti['name'],w,h,f)
if __name__=='__main__':
    for p in sys.argv[2:]:
        dump(p, os.path.join(sys.argv[1], os.path.basename(p)[32:-4]+'.png'))
