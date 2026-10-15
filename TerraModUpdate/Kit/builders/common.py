"""Shared helpers for the per-character mod builders (MacuriUpdate / KanaUpdate / GugbaUpdate / YapkarUpdate)."""
import copy, json, os, struct

HERE = os.path.dirname(os.path.abspath(__file__))
EX = json.load(open(os.path.join(HERE, "shipped_extract.json"), encoding="utf-8"))
LANGS = ("en", "ja", "fr", "de", "es", "zh_tw")


def f32(x):
    return struct.unpack("<f", struct.pack("<f", x))[0]


def tx(zh, en, ja):
    """Texts for the three written languages; fr/de/es follow en (done by langs())."""
    return {"en": en, "ja": ja, "zh_tw": zh}


def langs(v):
    en = v.get("en", "")
    return {l: (v.get(l) or en) if l != "ja" else v.get("ja", en) for l in LANGS}


NONE = tx("", "", "")


def shipped(i):
    return copy.deepcopy(EX["shipped_skills"][str(i)])


def base(i):
    return copy.deepcopy(EX["base_skills"][str(i)])


class Skills:
    """Ordered skill list; every add() returns the entry key.  Hidden helper skills must be added directly after their visible skill."""

    def __init__(self):
        self.items = []

    def add(self, key, rec, name=None, desc=None, rng=None, **fields):
        rec = copy.deepcopy(rec)
        late = {}
        for k, v in fields.items():
            if k not in rec:
                raise KeyError(k)
            if isinstance(v, str) and v.startswith("@"):      # effect cloned by an "effects" entry, resolved at build time
                late[k] = v
                continue
            rec[k] = f32(v) if isinstance(rec[k], float) else v
        if name is not None:
            rec["nameString"] = langs(name)
        if desc is not None:
            rec["descString"] = langs(desc)
        if rng is not None:
            rec["rangePrefixString"] = langs(rng)
        item = {"key": key, "raw": rec}
        if late:
            item["set"] = late
        self.items.append(item)
        return "@" + key


def character(chr_id, job_id, skill_keys, levels=None):
    info = copy.deepcopy(EX["infos"][str(chr_id)])
    job = copy.deepcopy(EX["jobs"][str(job_id)])
    assert len(skill_keys) == len(job["skills"]), (len(skill_keys), len(job["skills"]))
    job["skills"] = list(skill_keys)
    if levels:
        job["skillMasterLevel"] = levels
    return {"raw": {"info": info, "jobs": [job], "rebirth": copy.deepcopy(EX["rebirth"].get(str(chr_id)))}}


def buddy(buddy_id, skill_key, desc=None):
    b = copy.deepcopy(EX["buddies"][str(buddy_id)])
    spec = {"id": buddy_id, "raw": b, "name": b["NameString"], "skill": skill_key}
    if desc:
        spec["desc"] = desc
    return spec


def server_buddy(buddy_id, chr_id, names):
    return {"id": buddy_id, "rarity_letter": "Z", "name": langs(names), "max_level": 1, "exp_max": 0, "base_exp": 1, "base_coin": 1,
            "exp_coeff": f32(2.1), "evolve_id": 0, "coins_to_evolve": 0, "same_bonus_bias": 1, "unique": True, "pool": None,
            "after_chr": chr_id}


def write_mod(folder, filename, mod, server=None, meta=None):
    os.makedirs(os.path.join(folder, "mods"), exist_ok=True)
    json.dump(mod, open(os.path.join(folder, "mods", filename), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if server is not None:
        json.dump(server, open(os.path.join(folder, "server_buddies.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if meta is not None:
        json.dump(meta, open(os.path.join(folder, "update.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote", folder, filename, len(mod.get("skills", [])), "skills")
