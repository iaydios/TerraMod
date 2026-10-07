#!/usr/bin/env python3
"""Build the symbol maps used by the analysis scripts (run once per game version).

    python3 build_maps.py <global-metadata.dat> <libil2cpp.so> <workdir>

Writes <workdir>/symmap.json   {"0xADDR": "Namespace.Type::Method"}
       <workdir>/fullmap.json  {"Namespace.Type::Method": ["0xADDR", ...]}
       <workdir>/full.s        full arm64 disassembly (llvm-objdump), used by callers.py
"""
import json
import os
import subprocess
import sys

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import il2cpp_lite as L  # noqa: E402

meta_b, so_b, work = open(sys.argv[1], "rb").read(), open(sys.argv[2], "rb").read(), sys.argv[3]
meta, elf = L.Meta(meta_b), L.Elf(so_b)
ms = list(meta.methods())
count = max(m["methodIndex"] for m in ms) + 1
_, ptrs = next(L.find_code_registration(elf, count))
sym, full = {}, {}
for m in ms:
    if m["methodIndex"] < 0:
        continue
    a = elf.q(ptrs + 8 * m["methodIndex"])
    if not a:
        continue
    n = meta.type_name(m["declaringType"]) + "::" + meta.s(m["name"])
    sym.setdefault(hex(a), n)
    full.setdefault(n, [])
    if hex(a) not in full[n]:
        full[n].append(hex(a))
os.makedirs(work, exist_ok=True)
json.dump(sym, open(os.path.join(work, "symmap.json"), "w"), ensure_ascii=False)
json.dump(full, open(os.path.join(work, "fullmap.json"), "w"), ensure_ascii=False)
with open(os.path.join(work, "full.s"), "w") as f:
    subprocess.run(["llvm-objdump", "-d", "--no-show-raw-insn", sys.argv[2]], stdout=f, check=True)
print(len(sym), "methods")
