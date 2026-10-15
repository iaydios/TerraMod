import struct
from jobhash import calc
def payload(b):
    P=lambda v: struct.pack('<i',v); F=lambda v: struct.pack('<f',v)
    s=P(b['ID'])
    for k in ('rarity','type','attrib','kind','RequiredLevel','MaxLevel','ImageID','ATKmin','DEFmin','SATKmin','SDEFmin','BOOSTmin','ATKmax','DEFmax','SATKmax','SDEFmax','BOOSTmax','EXPmax','BaseEXP','BaseCOIN'):
        s+=P(b[k])
    s+=F(b['Coeff'])+F(b['EXPcoeff'])
    for k in ('skill','evolveID','coinsToEvolve','exclusiveChrID','exclusiveSpeciesID','_cost'): s+=P(b[k])
    for it in b['items']: s+=P(it['code'])
    return s
def buddy_hash(b,salt='mist_guardians_keycode'): return calc(payload(b),salt)
