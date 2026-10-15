"""Clone existing battle effects (particle prefabs) with a different colour.

A spec entry {"key": "fx_red", "template": 20, "hue": 2} copies EffectSet entry 20 and every particle prefab it
uses (textures and materials only when they are coloured, ParticleSystem colours/gradients), recolours the copies
towards `hue` (degrees) and appends new EffectSet / particleEffectSet entries. Originals are never edited:
objects are only added to resources.assets / resources.assets.resS, and the ResourceManager (globalgamemanagers)
gets the container + dependency entries for the new prefabs. Returns key -> new 1-based effID.
"""
import copy
import struct

import numpy as np

from mbcodec import encode, learn, load_tables  # noqa: F401
from unityfs import Bundle  # noqa: F401

ES_PID, RM_PID = 12692, 13
PES_IDS = {}          # effect key -> new particleEffectSet id (for native code that plays a cloned particle directly)
BASE_HUE = 167.0      # measured mean hue of the green poison glow


def rstr(raw,p):
    l=struct.unpack_from('<i',raw,p)[0]; return raw[p+4:p+4+l].decode('latin1'),(p+4+l+3)&~3
def parse_mat(raw):
    nm,p=rstr(raw,0)
    f,sh=struct.unpack_from('<iq',raw,p); p+=12
    kw,p=rstr(raw,p)
    lf,=struct.unpack_from('<I',raw,p); p+=4
    inst,dsg=raw[p],raw[p+1]; p+=4
    rq,=struct.unpack_from('<i',raw,p); p+=4
    n,=struct.unpack_from('<i',raw,p); p+=4
    for _ in range(n):
        _,p=rstr(raw,p); _,p=rstr(raw,p)
    n,=struct.unpack_from('<i',raw,p); p+=4+4*n   # disabledShaderPasses are strings? 
    return nm,sh,kw,rq,p

def mat_full(raw):
    """returns dict with off positions"""
    nm,p=rstr(raw,0)
    out={'name':nm,'shader_off':p}
    out['shader']=struct.unpack_from('<iq',raw,p); p+=12
    kw,p=rstr(raw,p); out['kw']=kw
    out['lmflags']=struct.unpack_from('<I',raw,p)[0]; p+=4
    out['inst']=raw[p:p+4]; p+=4  # instancing bool + dsgi... (4 aligned)
    out['rq']=struct.unpack_from('<i',raw,p)[0]; p+=4
    n,=struct.unpack_from('<i',raw,p); p+=4
    assert n==0
    n,=struct.unpack_from('<i',raw,p); p+=4
    assert n==0
    n,=struct.unpack_from('<i',raw,p); p+=4
    tex=[]
    for _ in range(n):
        t,p=rstr(raw,p)
        f,pid=struct.unpack_from('<iq',raw,p); toff=p; p+=12
        sc=struct.unpack_from('<4f',raw,p); p+=16
        tex.append((t,f,pid,toff,sc))
    out['tex']=tex
    n,=struct.unpack_from('<i',raw,p); p+=4
    fl=[]
    for _ in range(n):
        t,p=rstr(raw,p); v,=struct.unpack_from('<f',raw,p); p+=4; fl.append((t,v))
    out['floats']=fl
    n,=struct.unpack_from('<i',raw,p); p+=4
    cols=[]
    for _ in range(n):
        t,p=rstr(raw,p); v=struct.unpack_from('<4f',raw,p); coff=p; p+=16; cols.append((t,v,coff))
    out['cols']=cols
    out['end']=p
    return out
def comps(s,pid):
    raw=s.get(pid); n=struct.unpack_from('<i',raw,0)[0]
    return [struct.unpack_from('<q',raw,4+i*12+4)[0] for i in range(n)]
def go_name(s,pid):
    raw=s.get(pid); n=struct.unpack_from('<i',raw,0)[0]; p=4+n*12+4
    l=struct.unpack_from('<i',raw,p)[0]; return raw[p+4:p+4+l].decode('latin1')
def rend_mats(s,pid):
    raw=s.get(pid)
    # materials array at 56 for PSR (verified)
    n=struct.unpack_from('<i',raw,56)[0]
    return [struct.unpack_from('<iq',raw,60+12*i)[1] for i in range(n)]
def walk(s,goid,fn,ind=0):
    fn(goid,ind)
    for c in comps(s,goid):
        if s.objects[c]['class']==4:
            raw=s.get(c); n=struct.unpack_from('<i',raw,52)[0]
            for k in range(n):
                cp=struct.unpack_from('<q',raw,56+k*12+4)[0]
                g=struct.unpack_from('<q',s.get(cp),4)[0]
                walk(s,g,fn,ind+1)

def find_gradients(raw):
    """Gradient (2017.4): key0..7 float4 (128) | ctime0..7 u16 (16) | atime0..7 u16 (16) | mode i32 | nColor u8,nAlpha u8,pad2 => 168 bytes"""
    out=[]
    for p in range(0,len(raw)-168+1,4):
        ct=struct.unpack_from('<8H',raw,p+128); at=struct.unpack_from('<8H',raw,p+144)
        mode,=struct.unpack_from('<i',raw,p+160); nc,na=raw[p+164],raw[p+165]
        if not(1<=nc<=8 and 1<=na<=8 and mode in(0,1) and raw[p+166:p+168]==b'\0\0'): continue
        if list(ct[:nc])!=sorted(ct[:nc]): continue
        if ct[nc-1]!=65535 and nc>1: continue
        if at[na-1]!=65535 and na>1: continue
        ks=struct.unpack_from('<32f',raw,p)
        if any(not(-0.01<=x<=100) for x in ks[:4*nc]): continue
        out.append(p)
    return out


def pad4(n): return (n+3)&~3
def mkstr(s: bytes):
    b=struct.pack('<i',len(s))+s
    return b+b'\0'*((-len(b))%4)

class SF:
    """v17 SerializedFile with ability to ADD objects (rewrites the metadata block, grows data_offset)."""
    def __init__(self, raw: bytes):
        self.raw=bytearray(raw)
        msize,fsize,ver,doff=struct.unpack_from('>IIII',raw,0)
        assert ver==17 and raw[16]==0
        self.msize,self.doff=msize,doff
        o=20
        e=raw.index(b'\0',o); o=e+1; o+=4
        tree=raw[o]; o+=1
        assert not tree
        nt,=struct.unpack_from('<i',raw,o); o+=4
        self.types=[]
        for _ in range(nt):
            cid,stripped,sidx=struct.unpack_from('<iBh',raw,o); o+=7
            if cid==114 or sidx>=0: o+=16
            o+=16; self.types.append(cid)
        nobj,=struct.unpack_from('<i',raw,o); o+=4
        self.nobj_off=o-4
        o=(o+3)&~3; self.table_start=o
        self.table_end=o+20*nobj
        # tail: scripttypes, externals, userinfo string(len 0)
        t=self.table_end
        n,=struct.unpack_from('<i',raw,t); t+=4+12*n
        ne,=struct.unpack_from('<i',raw,t); t+=4
        for _ in range(ne):
            t=raw.index(b'\0',t)+1; t+=20; t=raw.index(b'\0',t)+1
        ul,=struct.unpack_from('<i',raw,t); assert ul==0; t+=4
        self.core_end=t
        assert not any(raw[t:doff])
        self.objects={}
        for i in range(nobj):
            e=self.table_start+20*i
            pid,start,size,tidx=struct.unpack_from('<qIIi',raw,e)
            self.objects[pid]={'entry':e,'start':start,'size':size,'tidx':tidx,'class':self.types[tidx]}
        self.new=[]   # (pid, tidx, bytes)
        self.repl={}  # pid -> bytes
        self._max=max(self.objects)
    def get(self,pid):
        if pid in self.repl: return self.repl[pid]
        for p,_,b in self.new:
            if p==pid: return b
        ob=self.objects[pid]; s=self.doff+ob['start']
        return bytes(self.raw[s:s+ob['size']])
    def cls(self,pid):
        for p,t,_ in self.new:
            if p==pid: return self.types[t]
        return self.objects[pid]['class']
    def tidx_of_class(self,c):
        return next(i for i,x in enumerate(self.types) if x==c)
    def add(self,cls,data):
        self._max+=1
        self.new.append((self._max,self.tidx_of_class(cls),data)); return self._max
    def replace(self,pid,data): self.repl[pid]=data
    def build(self)->bytes:
        raw=self.raw
        N=len(self.new)
        core=bytearray(raw[self.table_end:self.core_end])
        body=bytearray(raw[self.doff:])
        ents=dict((p,dict(v)) for p,v in self.objects.items())
        def append(data):
            while len(body)%8: body.append(0)
            st=len(body); body.extend(data); return st,len(data)
        for pid,data in self.repl.items():
            st,sz=append(data); ents[pid]['start'],ents[pid]['size']=st,sz
        for pid,tidx,data in self.new:
            st,sz=append(data); ents[pid]={'start':st,'size':sz,'tidx':tidx}
        order=sorted(ents)
        tbl=b''.join(struct.pack('<qIIi',p,ents[p]['start'],ents[p]['size'],ents[p]['tidx']) for p in order)
        assert len(tbl)==20*(len(self.objects)+N)
        meta=bytearray(raw[:self.table_start])+bytearray(tbl)+core
        meta[self.nobj_off:self.nobj_off+4]=struct.pack('<i',len(order))
        newdoff=max((len(meta)+15)&~15, self.doff if len(meta)<=self.doff else 0)
        meta+=b'\0'*(newdoff-len(meta))
        out=bytes(meta)+bytes(body)
        out=bytearray(out)
        struct.pack_into('>IIII',out,0,self.msize+20*N,len(out),17,newdoff)
        return bytes(out)

def parse_rm(raw):
    n,=struct.unpack_from('<i',raw,0); p=4; cont=[]
    for _ in range(n):
        nm,p=rstr(raw,p); f,pid=struct.unpack_from('<iq',raw,p); p+=12; cont.append((nm,f,pid))
    n,=struct.unpack_from('<i',raw,p); p+=4; deps=[]
    for _ in range(n):
        f,pid=struct.unpack_from('<iq',raw,p); p+=12
        m,=struct.unpack_from('<i',raw,p); p+=4
        d=[struct.unpack_from('<iq',raw,p+12*k) for k in range(m)]; p+=12*m
        deps.append(((f,pid),d))
    assert p==len(raw)
    return cont,deps
def build_rm(cont,deps):
    o=bytearray(struct.pack('<i',len(cont)))
    for nm,f,pid in cont: o+=mkstr(nm.encode())+struct.pack('<iq',f,pid)
    o+=struct.pack('<i',len(deps))
    for (f,pid),d in deps:
        o+=struct.pack('<iq',f,pid)+struct.pack('<i',len(d))+b''.join(struct.pack('<iq',a,b) for a,b in d)
    return bytes(o)



def circ(d): return (d + 180) % 360 - 180
def map_hue_arr(rgb, target, k=0.35, clamp=60.0, sat_floor=0.12):
    """rgb float (...,3). Pull every saturated colour towards `target` hue (keeps S,V). Greys untouched."""
    mx = rgb.max(-1); mn = rgb.min(-1); d = mx - mn
    sat = np.where(mx > 1e-9, d / np.where(mx > 1e-9, mx, 1), 0)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    dd = np.where(d > 1e-9, d, 1)
    h = np.where(mx == r, ((g - b) / dd) % 6, np.where(mx == g, (b - r) / dd + 2, (r - g) / dd + 4)) * 60.0
    nh = (target + k * np.clip(circ(h - BASE_HUE), -clamp, clamp)) % 360.0
    H = nh / 60.0; c = d; x = c * (1 - np.abs(H % 2 - 1)); i = np.floor(H).astype(int) % 6
    z = np.zeros_like(c)
    R = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [c, x, z, z, x, c])
    G = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [x, c, c, x, z, z])
    B = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5], [z, z, x, c, c, x])
    out = np.stack([R, G, B], -1) + (mx - c)[..., None]
    return np.where((sat > sat_floor)[..., None] & (d > 1e-9)[..., None], out, rgb)

def recolor_ps(raw, target, stats):
    raw = bytearray(raw)
    def rot(off):   # float4 colour at off: rotate rgb, keep a
        v = np.array(struct.unpack_from('<3f', raw, off), dtype=np.float64)
        n = map_hue_arr(v[None, :], target)[0]
        if not np.allclose(n, v, atol=1e-6): stats['colours'] += 1
        struct.pack_into('<3f', raw, off, *[float(x) for x in n])
    # InitialModule.startColor MinMaxGradient: state u16 @192, minColor @196, maxColor @212, maxGradient @228, minGradient @396
    rot(196); rot(212)
    for p in find_gradients(bytes(raw)):
        for k in range(8): rot(p + 16 * k)     # colour keys (alpha keys live in .a and are untouched)
        stats['gradients'] += 1
    return bytes(raw)

def clone_texture(sf, resS, pid, target, cache):
    if pid in cache: return cache[pid]
    raw = sf.get(pid); nm, p = rstr(raw, 0)
    w, h, sz, fmt, mips = struct.unpack_from('<iiiii', raw, p + 8)
    off, ssz = struct.unpack_from('<II', raw, len(raw) - 36)
    assert raw[-28:] == mkstr(b'resources.assets.resS') and fmt in (3, 4) and sz == ssz
    ch = 4 if fmt == 4 else 3
    a = np.frombuffer(bytes(resS[off:off + ssz]), np.uint8).copy().reshape(-1, ch)   # every mip is just more pixels
    rgb = a[:, :3].astype(np.float64) / 255
    a[:, :3] = np.clip(np.rint(map_hue_arr(rgb, target) * 255), 0, 255).astype(np.uint8)
    while len(resS) % 16: resS.append(0)
    noff = len(resS); resS.extend(a.tobytes())
    new_name = nm.encode() + b'_' + cache['_suffix'].encode()
    new = mkstr(new_name) + raw[p:len(raw) - 36] + struct.pack('<II', noff, ssz) + raw[-28:]
    cache[pid] = sf.add(28, new)
    return cache[pid]

def clone_material(sf, resS, pid, target, cache, tcache):
    if pid in cache: return cache[pid]
    raw = sf.get(pid); mf = mat_full(raw)
    if not any(tp and tex_is_coloured(sf, resS, tp) for _, _, tp, _, _ in mf['tex']):
        cache[pid] = pid          # grey texture: tint comes from the particle system, share the original material
        return pid
    body = bytearray(raw[(4 + len(mf['name']) + 3) & ~3:])
    delta = (4 + len(mf['name']) + 3) & ~3
    for t, f, tp, toff, sc in mf['tex']:
        if tp == 0: continue
        if tex_is_coloured(sf, resS, tp):
            struct.pack_into('<q', body, toff + 4 - delta, clone_texture(sf, resS, tp, target, tcache))
    new = mkstr((mf['name'] + '_' + cache['_suffix']).encode()) + bytes(body)
    cache[pid] = sf.add(21, new)
    return cache[pid]

_coloured = {}
def tex_is_coloured(sf, resS, pid):
    if pid in _coloured: return _coloured[pid]
    raw = sf.get(pid); nm, p = rstr(raw, 0)
    w, h, sz, fmt, mips = struct.unpack_from('<iiiii', raw, p + 8)
    off, ssz = struct.unpack_from('<II', raw, len(raw) - 36)
    if fmt not in (3, 4): _coloured[pid] = False; return False
    ch = 4 if fmt == 4 else 3
    px = np.frombuffer(bytes(resS[off:off + w * h * ch]), np.uint8).reshape(-1, ch).astype(float) / 255
    mx = px[:, :3].max(1); mn = px[:, :3].min(1)
    sat = np.where(mx > 0, (mx - mn) / np.where(mx > 0, mx, 1), 0); wgt = (px[:, 3] if ch == 4 else 1) * mx
    _coloured[pid] = bool((sat * wgt).sum() / max(wgt.sum(), 1e-9) > 0.2)
    return _coloured[pid]

def go_tree(sf, root):
    """pre-order list of (go, [component pids]) for a prefab"""
    out = []
    def rec(g):
        cs = comps(sf, g); out.append((g, cs))
        for c in cs:
            if sf.cls(c) == 4:
                raw = sf.get(c); n, = struct.unpack_from('<i', raw, 52)
                for k in range(n):
                    tp = struct.unpack_from('<q', raw, 56 + 12 * k + 4)[0]
                    rec(struct.unpack_from('<q', sf.get(tp), 4)[0])
    rec(root); return out

def clone_prefab(sf, resS, root, new_name, target, tcache, mcache, log, deps_new, dep_old):
    tree = go_tree(sf, root)
    objs = []                                   # (old pid, class)
    for g, cs in tree:
        objs.append((g, 1)); objs += [(c, sf.cls(c)) for c in cs]
    assert all(c in (1, 4, 198, 199) for _, c in objs), [c for _, c in objs]
    base = sf._max + 1
    # materials first would shift ids -> clone them before planning
    mats = {}
    for _, c in objs:
        pass
    for o, c in objs:
        if c == 199:
            for m in rend_mats(sf, o):
                if m and m not in mats: mats[m] = clone_material(sf, resS, m, target, mcache, tcache)
    base = sf._max + 1
    nm = {o: base + i for i, (o, _) in enumerate(objs)}
    stats = {'colours': 0, 'gradients': 0}
    for o, c in objs:
        raw = bytearray(sf.get(o))
        if c == 1:
            n, = struct.unpack_from('<i', raw, 0)
            for i in range(n): struct.pack_into('<q', raw, 4 + 12 * i + 4, nm[struct.unpack_from('<q', raw, 4 + 12 * i + 4)[0]])
            p = 4 + 12 * n; name, p2 = rstr(raw, p + 4)
            if o == root: name = new_name
            raw = bytes(raw[:p + 4]) + mkstr(name.encode()) + bytes(raw[p2:])
        elif c == 4:
            struct.pack_into('<q', raw, 4, nm[struct.unpack_from('<q', raw, 4)[0]])
            n, = struct.unpack_from('<i', raw, 52)
            for k in range(n): struct.pack_into('<q', raw, 56 + 12 * k + 4, nm[struct.unpack_from('<q', raw, 56 + 12 * k + 4)[0]])
            fo = 56 + 12 * n; fa, = struct.unpack_from('<q', raw, fo + 4)
            if fa: struct.pack_into('<q', raw, fo + 4, nm[fa])      # father: only inside the clone (root has 0)
        elif c == 198:
            struct.pack_into('<q', raw, 4, nm[struct.unpack_from('<q', raw, 4)[0]])
            raw = recolor_ps(raw, target, stats)
        elif c == 199:
            struct.pack_into('<q', raw, 4, nm[struct.unpack_from('<q', raw, 4)[0]])
            for i, m in enumerate(rend_mats(sf, o)):
                if m: struct.pack_into('<q', raw, 60 + 12 * i + 4, mats[m])
        got = sf.add(c, bytes(raw)); assert got == nm[o]
        d = dep_old.get(o)
        if d is not None:
            nd = []
            for fid, pid in d:
                nd.append((fid, nm.get(pid, mats.get(pid, pid))))
            deps_new.append(((3, got), nd))
    # material dependency entries
    for m, nmid in mats.items():
        d = dep_old.get(m)
        if d is not None and nmid != m and not any(k == (3, nmid) for k, _ in deps_new):
            deps_new.append(((3, nmid), [(f, tcache.get(p, p)) for f, p in d]))
    log.append(f'prefab {go_name(sf, root)!r}({root}) -> {new_name!r} root GO {nm[root]}  objs {nm[objs[0][0]]}..{nm[objs[-1][0]]}  mats {mats}  recoloured {stats}')
    return nm[root]



def apply_effects(bundle, specs, es, log):
    """bundle: unityfs.Bundle (modified in place). es: EffectSet dict (modified in place). Returns {key: effID}."""
    # "combo" specs only add an EffectSet entry: copy `template` and take its impact effect (subPid) from the pid of effect `sub` (no prefab is cloned)
    efs0 = es["effectSet"]; keys0 = {}
    for sp in [x for x in specs if "combo" in x]:
        c = sp["combo"]; ne = dict(efs0[int(c["template"]) - 1])
        ne["subPid"] = efs0[int(c["sub"]) - 1]["pid"]; ne["subWait"] = float(c.get("subWait", 0.0)); ne["desc"] = ne["desc"] + "_" + sp["key"]
        efs0.append(ne); keys0[sp["key"]] = len(efs0)
        log.append("effects combo %s -> effID %d (pid %d, subPid %d)" % (sp["key"], len(efs0), ne["pid"], ne["subPid"]))
    # "se_clone" specs add a particleEffectSet entry that reuses an existing prefab but plays a different sound (seID); the new 1-based id goes to PES_IDS
    for sp in [x for x in specs if "se_clone" in x]:
        c = sp["se_clone"]; base = es["particleEffectSet"][int(c["pes"]) - 1]
        es["particleEffectSet"].append({"name": base["name"], "seID": c["seID"], "initialInstance": base["initialInstance"]})
        PES_IDS[sp["key"]] = keys0[sp["key"]] = len(es["particleEffectSet"])
        log.append("effects se_clone %s -> particle id %d (%s, se %s)" % (sp["key"], PES_IDS[sp["key"]], base["name"], c["seID"]))
    specs = [x for x in specs if "combo" not in x and "se_clone" not in x]
    if not specs:
        return keys0
    ra = SF(bundle.files["resources.assets"][0]); gm = SF(bundle.files["globalgamemanagers"][0])
    resS = bytearray(bundle.files["resources.assets.resS"][0]); n_res0 = len(resS)
    cont, deps = parse_rm(gm.get(RM_PID)); dep_old = {p: [(f, q) for f, q in d] for (f, p), d in deps}
    pes, efs = es["particleEffectSet"], es["effectSet"]
    n_pes0, n_efs0 = len(pes), len(efs)
    keys, deps_new, caches, pidmaps = {}, [], {}, {}
    for sp in specs:
        target = float(sp["hue"]); var = "%s" % sp["key"]
        if sp["key"] in keys:
            raise SystemExit("duplicate effect key " + sp["key"])
        tcache = caches.setdefault(("t", target), {"_suffix": var})
        mcache = caches.setdefault(("m", target), {"_suffix": var})
        pidmap = pidmaps.setdefault(target, {})
        e = efs[int(sp["template"]) - 1] if "template" in sp else {"type": 0, "pid": int(sp["pes"]), "timeToImpact": 0.4000000059604645, "subPid": 0, "subWait": 0.0, "desc": "pes%d" % int(sp["pes"])}
        ne = dict(e)
        for key in ("pid", "subPid"):
            op = e[key]
            if op == 0:
                continue
            if op not in pidmap:
                pe = pes[op - 1]; nm0 = pe["name"]
                root = next(pid for (n, f, pid) in cont if n == "battleeffects/" + nm0.lower())
                newname = "%s_fx%d" % (nm0, int(target))
                nroot = clone_prefab(ra, resS, root, newname, target, tcache, mcache, log, deps_new, dep_old)
                cont.append(("battleeffects/" + newname.lower(), 3, nroot))
                pes.append({"name": newname, "seID": pe["seID"], "initialInstance": pe["initialInstance"]})
                pidmap[op] = len(pes)
            ne[key] = pidmap[op]
        ne["desc"] = e["desc"] + "_" + sp["key"]
        efs.append(ne); keys[sp["key"]] = len(efs); PES_IDS[sp["key"]] = ne["pid"]
    cont.sort(key=lambda t: t[0])
    deps.extend(deps_new)
    gm.replace(RM_PID, build_rm(cont, deps))
    bundle.files["resources.assets"][0] = ra.build()
    bundle.files["globalgamemanagers"][0] = gm.build()
    bundle.files["resources.assets.resS"][0] = bytes(resS)
    log.append("effects: +%d effectSet, +%d particleEffectSet, resS +%d bytes, %d objects: %s"
               % (len(efs) - n_efs0, len(pes) - n_pes0, len(resS) - n_res0, len(ra.new), keys))
    keys.update(keys0)
    return keys
