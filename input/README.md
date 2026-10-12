# input/

TerraBattle.apk, reTB-Host.apk, game_data/, gdresources/ — see the main README. Not part of the repository.

build_all.py recognizes these by content, so the names can be anything sensible. Nothing
here is ever written to: a gdresources *.tar is unpacked once into out/, and a reTB folder
(PC server) stands in for reTB-Host.apk by being copied to out/ and patched there.
