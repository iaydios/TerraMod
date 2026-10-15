"""One-off: copies the records of the previously shipped (old native design) game DBs that the new per-character mod builders start from.
usage: python3 extract_shipped.py <dir with shipped_*.json> <dir with base/*.json> <out shipped_extract.json>"""
import json, sys
sh, base, out = sys.argv[1:4]
S = json.load(open(f"{sh}/shipped_SkillData.json"))["types"]
C = json.load(open(f"{sh}/shipped_ChrDatabase.json"))
B = json.load(open(f"{sh}/shipped_BuddyDatabase.json"))["data"]
BS = json.load(open(f"{base}/SkillData.json"))["types"]
BASE_IDX = [98, 116, 133, 155, 147, 750, 751, 2057, 274, 299, 409, 355, 464, 3075, 3179, 2272, 2262, 1677, 1960]
ex = {
    "shipped_skills": {str(i): S[i - 1] for i in range(3842, 3890)},
    "base_skills": {str(i): BS[i] for i in BASE_IDX},
    "infos": {str(i["ID"]): i for i in C["infos"] if i["ID"] in (1289, 1290, 1291, 1292)},
    "jobs": {str(j["ID"]): j for j in C["data"] if j["ID"] in (5166, 5167, 5168, 5169)},
    "rebirth": {str(r["dstChrID"]): r for r in C["rebirthInfo"] if r["dstChrID"] in (1289, 1290, 1291, 1292)},
    "buddies": {str(b["ID"]): b for b in B if b["ID"] in (498, 499, 500)},
}
json.dump(ex, open(out, "w", encoding="utf-8"), ensure_ascii=False)
print({k: len(v) for k, v in ex.items()})
