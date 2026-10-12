#!/usr/bin/env python3
"""Build one KeyLab mk3 script for Logic Pro, GarageBand and MainStage.

The repository holds no Arturia code. Inputs are Arturia's own downloads, placed
in downloads/ (or fetched with --download):
  KeyLab_mk3_Logic_Pro_Daw_Integration_Script_<version>.zip
  KeyLab_mk3_Mainstage_Daw_Integration_Script_<version>.zip
Outputs (build/, not tracked):
  build/KeyLab <size> mk3.device/config.lua    the merged script to install
  build/arturia/{logic,mainstage}/...          Arturia's scripts, as extracted
  build/logic-patched/...                      the fixed Logic script alone

Each Arturia script runs in its own Lua 5.2 _ENV namespace, so their ~45 shared
names (SetCenterPage, S_INIT_MESSAGES, ...) don't clash. The file then exposes
the host callbacks of whichever script fits the running app.
"""
import argparse
import hashlib
import re
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOWNLOADS = ROOT / "downloads"
BUILD = ROOT / "build"
SIZES = ["49", "61", "88"]

ARTURIA_URL = "https://www.arturia.com/api/download/products/keylab-49-mk3/daw-integration-script/"
ZIPS = {  # app: (file pattern, file fetched by --download)
    "logic": ("KeyLab_mk3_Logic_Pro_Daw_Integration_Script_*.zip",
              "KeyLab_mk3_Logic_Pro_Daw_Integration_Script_1_1_0.zip"),
    "mainstage": ("KeyLab_mk3_Mainstage_Daw_Integration_Script_*.zip",
                  "KeyLab_mk3_Mainstage_Daw_Integration_Script_1_1_0.zip"),
}

# SHA-256 of the Arturia scripts this build was tested with (Logic script 1.1.0,
# MainStage script 1.1.0; on a KeyLab 61 mk3 in GarageBand and MainStage).
TESTED = {
    ("logic", "49"): "75c8d4603efb3815cd845dfa6520c4fb8e1e5395c96f2cdc66177d7fae6bbffc",
    ("logic", "61"): "b67ec01cae179a78684da2ef967f9d6a27dc9c351a2c71284deea43b90adb37f",
    ("logic", "88"): "849e85bcfed927c0fab3e5404f3e79c5df55be3c77ad0c78aea26d6b4b9515be",
    ("mainstage", "49"): "c75258ca14b187fe35614f3155466b56fbbfd9721bb3dc7483edb2f6b49a05c9",
    ("mainstage", "61"): "5549d4967bdaf9fd72c0909f3f0fd75546e893c616a03d1522a598a6f8b00b26",
    ("mainstage", "88"): "d33e6187646be71d1036a59f31314e5b0a75630729f08da84cdcc5d8097821de",
}


def download():
    DOWNLOADS.mkdir(exist_ok=True)
    for _, name in ZIPS.values():
        dest = DOWNLOADS / name
        if dest.exists():
            print("already downloaded", dest.relative_to(ROOT))
            continue
        req = urllib.request.Request(ARTURIA_URL + name, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as r:
            data = r.read()
        if not data.startswith(b"PK"):
            sys.exit(f"{name}: Arturia didn't return a zip; download it from the KeyLab mk3 "
                     "resources page into downloads/ instead")
        dest.write_bytes(data)
        print("downloaded", dest.relative_to(ROOT))


def extract(app: str) -> None:
    """Copy each size's config.lua out of Arturia's zip -> DMG into build/arturia/<app>/."""
    pattern = ZIPS[app][0]
    found = sorted(DOWNLOADS.glob(pattern))
    if not found:
        sys.exit(f"missing downloads/{pattern}: download it from "
                 "https://www.arturia.com/products/hybrid-synths/keylab-mk3/resources "
                 "or run: python3 build.py --download")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        with zipfile.ZipFile(found[-1]) as z:
            dmg_name = next(n for n in z.namelist() if n.endswith(".dmg"))
            dmg = Path(z.extract(dmg_name, tmp))
        mnt = tmp / "mnt"
        mnt.mkdir()
        subprocess.run(["hdiutil", "attach", "-nobrowse", "-readonly", "-mountpoint", str(mnt), str(dmg)],
                       check=True, capture_output=True)
        try:
            for size in SIZES:
                src = mnt / f"KeyLab {size} mk3.device" / "config.lua"
                dest = BUILD / "arturia" / app / f"KeyLab {size} mk3.device" / "config.lua"
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(src.read_bytes())
        finally:
            subprocess.run(["hdiutil", "detach", str(mnt), "-quiet"], check=False)
    print(f"extracted {found[-1].name}")


def arturia_script(app: str, size: str) -> str:
    path = BUILD / "arturia" / app / f"KeyLab {size} mk3.device" / "config.lua"
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() != TESTED[(app, size)]:
        print(f"WARNING: {app} script for KeyLab {size} mk3 differs from the tested version; "
              "build it, but retest before relying on it", file=sys.stderr)
    return data.decode("utf-8")


def patch_logic(src: str, model: str) -> str:
    """Fix the Logic script so it also works in GarageBand."""
    def sub(pattern, repl, text, expected):
        new, n = re.subn(pattern, repl, text, flags=re.M)
        if n != expected:
            sys.exit(f"patch {pattern!r}: expected {expected} matches, got {n}")
        return new

    # 1. Use the device's own port name ('DAW'), not the display name.
    src = sub(rf"^MIDI_(IN|OUT) = '{re.escape(model)} DAW'", r"MIDI_\1 = 'DAW'", src, 2)
    # 2. MIDI_IN was reused as an on/off flag, wiping the port name before the
    #    controls table is built (every control ended up with inport = false).
    src = sub(r"\bMIDI_IN (==|=) (true|false)\b", r"MIDI_IN_FLAG \1 \2", src, 5)
    # 3. Name the output port on every message sent to the keyboard.
    src = sub(r"^(\s*)return \{ *midi = msg", r"\1return { midi = msg, outport = MIDI_OUT", src, 5)
    return src


def wrap(name: str, body: str) -> str:
    # _ENV (not _G): look names up in whatever environment the app loads us in.
    return (f"local {name} = setmetatable({{}}, {{__index = _ENV}})\n"
            f"do\n\tlocal _ENV = {name}\n\n{body.rstrip()}\n\nend -- {name}\n")


def build(size: str) -> Path:
    model = f"KeyLab {size} mk3"
    logic = patch_logic(arturia_script("logic", size), model)
    mainstage = arturia_script("mainstage", size)

    patched = BUILD / "logic-patched" / f"{model}.device" / "config.lua"
    patched.parent.mkdir(parents=True, exist_ok=True)
    patched.write_text(logic, encoding="utf-8")

    out = f"""--- Surface:	{model}
--- One script for Logic Pro, GarageBand and MainStage.
--- Built by build.py from Arturia's Logic script 1.1.0 and MainStage profile
--- (Copyright (c) 2023 Farès MEZDOUR / Arturia). Personal use only.
---
--- Logic/GarageBand part: ports fixed to 'DAW' (GarageBand has no Control
--- Surface Setup to choose them). Tap (532) and Back (1366) are Logic-only;
--- GarageBand ignores them.

{wrap("LOGIC", logic)}
{wrap("MAINSTAGE", mainstage)}
-- MainStage doesn't define Logic's track/plug-in parameter names.
IS_MAINSTAGE = (CS_SMARTCONTROL1 == nil and AUVOLUME == nil)
local S = IS_MAINSTAGE and MAINSTAGE or LOGIC

function controller_info() return S.controller_info() end
function controller_initialize(...) return S.controller_initialize(...) end
function controller_finalize(...) return S.controller_finalize(...) end
function controller_midi_in(...) return S.controller_midi_in(...) end

if IS_MAINSTAGE then
\tfunction controller_select_patch(...) return MAINSTAGE.controller_select_patch(...) end
else
\tfunction CSLongLabel(...) return LOGIC.CSLongLabel(...) end
\tfunction CSFeedback(...) return LOGIC.CSFeedback(...) end
\tfunction CSFeedbackText(...) return LOGIC.CSFeedbackText(...) end
end
"""
    dest = BUILD / f"{model}.device" / "config.lua"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(out, encoding="utf-8")
    return dest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("sizes", nargs="*", default=["61"], choices=SIZES, metavar="SIZE",
                        help="keyboard sizes to build: 49, 61, 88 (default 61)")
    parser.add_argument("--download", action="store_true", help="fetch Arturia's zips into downloads/ first")
    args = parser.parse_args()
    if args.download:
        download()
    for app in ZIPS:
        extract(app)
    for size in args.sizes:
        print("built", build(size).relative_to(ROOT))
