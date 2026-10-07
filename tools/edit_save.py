#!/usr/bin/env python3
"""Set a character's job level in a reTBHost account export (format retb-save/1).

    python3 edit_save.py --save retb-save.json --chrdb ChrDatabase.json --chr 1289 --level 90 --out retb-save-lv90.json

Both copies of the level are updated:
  * session data -> chrdata[].jobLevels[slot] = (exp << 12) | level   (what the client reads)
  * characters table -> job_levels JSON list                          (what the server reads)
EXP needed for level L: EXP + (EXPmax - EXP) * ((L - 1) / 98) ** EXPcoeff, rounded up.
"""
import argparse
import json
import math


def exp_for(job, level):
    lo, hi, k = job.get("EXP", 0), job["EXPmax"], job["EXPcoeff"]
    return math.ceil(lo + (hi - lo) * ((level - 1) / 98) ** k)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--save", required=True)
    ap.add_argument("--chrdb", required=True, help="(modded) ChrDatabase.json")
    ap.add_argument("--chr", type=int, required=True)
    ap.add_argument("--level", type=int, required=True)
    ap.add_argument("--slot", type=int, default=0, help="job slot 0..2 (default 0)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    assert 1 <= a.level <= 99

    db = json.load(open(a.chrdb, encoding="utf-8"))
    info = next(i for i in db["infos"] if i["ID"] == a.chr)
    job_id = info["Jobs"][a.slot]
    job = next(j for j in db["data"] if j["ID"] == job_id)
    packed = (exp_for(job, a.level) << 12) | a.level

    s = json.load(open(a.save, encoding="utf-8"))
    assert s.get("format") == "retb-save/1", "unknown save format"
    done = 0
    for row in s["tables"]["session"]["rows"]:
        data = json.loads(row[1])
        for c in data.get("chrdata", []):
            if c["id"] == a.chr:
                c["jobLevels"][a.slot] = float(packed)
                done += 1
        row[1] = json.dumps(data, ensure_ascii=False)
    t = s["tables"]["characters"]
    ci, li = t["cols"].index("chr_id"), t["cols"].index("job_levels")
    for row in t["rows"]:
        if row[ci] == a.chr:
            lv = json.loads(row[li])
            lv[a.slot] = a.level
            row[li] = json.dumps(lv)
            done += 1
    if not done:
        raise SystemExit(f"character {a.chr} not found in the save - obtain it in game first")
    json.dump(s, open(a.out, "w", encoding="utf-8"), ensure_ascii=False)
    print(f"chr {a.chr} job {job_id} -> Lv{a.level} (packed {packed}), {done} record(s) updated")


if __name__ == "__main__":
    main()
