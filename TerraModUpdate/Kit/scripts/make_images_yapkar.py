"""Rebuilds the Pieces/Illust/Profile bins of Y'apkar? Lambda (image id 3007) from YapkarUpdate/art into YapkarUpdate/gdresources_new.
usage: python3 make_images_yapkar.py <global-metadata.dat> <TerraModUpdate root>"""
import glob, os, sys
root = sys.argv[2]
sys.path.insert(0, os.path.join(root, "Kit", "tools"))
from PIL import Image
from assets import decrypt_enca, encrypt_enca
from assets_build import prefix_for
import assets_inplace

meta = sys.argv[1]
art = os.path.join(root, "YapkarUpdate", "art"); out = os.path.join(root, "YapkarUpdate", "gdresources_new")
tpl_dir = os.path.join(root, "Kit", "templates")
inv = open(meta, "rb").read()[0x601CAD:0x601CAD + 256]
for sub, name, src in (("Pieces", "img_3007", "yapkar_piece.png"), ("Illust", "illust_3007", "yapkar_illust.png")):
    tpl = glob.glob(os.path.join(tpl_dir, sub, "*" + name + ".bin"))[0]
    enc, plain, fname = assets_inplace.build(tpl, inv, name, name, Image.open(os.path.join(art, src)))
    for old in glob.glob(os.path.join(out, sub, "*" + name + ".bin")):
        os.remove(old)
    os.makedirs(os.path.join(out, sub), exist_ok=True)
    open(os.path.join(out, sub, fname), "wb").write(enc)
    print(sub, fname, len(enc))
pre = prefix_for("profile_3007")
os.makedirs(os.path.join(out, "Profile"), exist_ok=True)
for name, src in (("profile_3007", "yapkar_profile.jpg"), ("profile_3007_m", "yapkar_profile_m.jpg")):
    jpg = open(os.path.join(art, src), "rb").read()
    enc = encrypt_enca(jpg, inv)
    assert decrypt_enca(enc, inv) == jpg
    open(os.path.join(out, "Profile", pre + name + ".bin"), "wb").write(enc)
    print("Profile", pre + name + ".bin", len(enc))
