"""Terra Battle ChrJobParams.calcHash (verified against the game's own job table).

hash = sum of the 4 little-endian int32 words of MD5(payload + UTF8(SALT)), wrapped to int32.
base = ChrBaseParams.calcHash(job, skipLevelStats=True); job payload starts with base.
"""
import hashlib
import struct

SALT = None  # set by find_salt / set explicitly
CANDIDATE_SALTS = ["mist_guardians_keycode", "tbguardmistkeycodehiso"]


def _i(v):
    return struct.pack("<i", v)


def _f(v):
    return struct.pack("<f", v)


def calc(payload: bytes, salt: str) -> int:
    d = hashlib.md5(payload + salt.encode("utf-8")).digest()
    s = sum(struct.unpack("<4i", d)) & 0xFFFFFFFF
    return s - (1 << 32) if s >> 31 else s


AVOID16 = ["avoidSleep", "avoidPoison", "avoidParalyze", "avoidConfuse", "avoidLoseHeart", "avoidStone",
           "avoidDeath", "avoidGravity", "avoidIced", "avoidAddWait", "avoidRatioDamage", "avoidATKDown",
           "avoidDEFDown", "avoidSATKDown", "avoidSDEFDown", "avoidMove"]


def base_payload(j, skip_level=True):
    b = _i(j["ID"]) + _i(j["chrID"]) + _i(j["ImageID"]) + _f(j["ImageScale"])
    for k in ("Gender", "Species", "SkillBoost", "PlusCount"):
        b += _i(j[k])
    if not skip_level:
        for k in ("LV", "HP", "ATK", "DEF", "SATK", "SDEF"):
            b += _i(j[k])
    for k in ("com_EXP", "EXP", "WAIT", "RANGE", "FrameType", "COIN", "DropJobID"):
        b += _i(j[k])
    b += _f(j["DropRatio"])
    for k in AVOID16:
        b += _f(j[k])
    for k in ("IconType", "Attrib", "SkillAttrib", "VS_Species"):
        b += _i(j[k])
    b += _f(j["VS_power"]) + _i(j["SkillMask"])
    for v in j["SkillSlot"]:
        b += _i(v)
    for v in j["DispSkillSlot"]:
        b += _i(v)
    b += _i(j["DropSummonID"]) + _f(j["DropSummonRatio"]) + _i(j["DropBuddyID"]) + _f(j["DropBuddyRatio"])
    return b


def job_hash(j, salt):
    b = _i(calc(base_payload(j), salt))
    for k in ("HPmin", "ATKmin", "DEFmin", "SATKmin", "SDEFmin", "HPmax", "ATKmax", "DEFmax", "SATKmax",
              "SDEFmax", "EXPmax"):
        b += _i(j[k])
    for k in ("HPcoeff", "ATKcoeff", "DEFcoeff", "SATKcoeff", "SDEFcoeff", "EXPcoeff"):
        b += _f(j[k])
    b += _i(j["_cost"])
    for v in j["skillMasterLevel"]:
        b += _i(v)
    for v in j["skills"]:
        b += _i(v)
    return calc(b, salt)
