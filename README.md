# KeyLab mk3: one script for Logic Pro, GarageBand and MainStage

> This repository contains no Arturia code. `build.py` takes Arturia's scripts
> from their official downloads (Copyright © 2023 Farès MEZDOUR / Arturia) and
> builds the merged file locally into `build/`, which git ignores. Don't share
> the built file: it contains Arturia's code.

Arturia ships separate DAW integration scripts for Logic Pro and MainStage and
none for GarageBand. This project fixes Arturia's Logic script so it works in
GarageBand, and merges it with the MainStage profile into a single file for all
three apps.

## Why Arturia's Logic script fails in GarageBand

All three apps run the same Lua 5.2 engine and read controller scripts from the
same folder, `~/Music/Audio Music Apps/MIDI Device Profiles/`. Other makers
(Novation Launchkey MK4, Korg Keystage) ship one script for Logic and GarageBand.

The Logic script (v1.1.0) has a bug:

```lua
9:    MIDI_IN = 'KeyLab 61 mk3 DAW'   -- port name
135:  MIDI_IN = false                 -- same variable reused as an on/off flag
1008: controls = { ... inport = MIDI_IN ... }
```

Line 135 runs before the controls table is built, so all 67 controls get
`inport = false` (confirmed by running the script under Lua 5.2). Logic hides
the bug because you choose the port by hand in Control Surfaces → Setup.
GarageBand has no such window, so it never listens to the KeyLab's DAW port.

Two smaller problems:

- The ports are named by their display name (`KeyLab 61 mk3 DAW`). The device's
  own name for the port is `DAW`, which is what Novation and Korg use.
- The messages the script sends to the keyboard (connect, screen updates) name
  no output port.

A further conflict: Arturia's Logic and MainStage installers write the same
file, so installing one overwrites the other.

## The fix

`build.py` makes three changes to the Logic script:

1. Ports set to `'DAW'`.
2. The flag renamed to `MIDI_IN_FLAG`.
3. `outport = MIDI_OUT` added to every message sent to the keyboard.

Each change must match an exact number of places, so the build stops if a
future Arturia version no longer fits. `build.py` also checks each Arturia file
against the SHA-256 of the tested version, and warns if Arturia has changed it.

To merge, each Arturia script runs in its own Lua `_ENV` namespace, because they
share about 45 global names. The file then exposes the right script's callbacks:

- **MainStage**, detected because it doesn't define `CS_SMARTCONTROL1`/`AUVOLUME`:
  Arturia's MainStage profile, unchanged.
- **Logic and GarageBand**: the fixed Logic script, unchanged otherwise.

## Results (KeyLab 61 mk3, GarageBand 10.4.14, MainStage 4.3.1, 2026-10-12)

| App | Status |
|---|---|
| GarageBand | Transport, track select, faders/encoders (Mixer and Device modes), Mute/Solo/Arm, Smart Controls, Save, Quantize work. **Tap** and **Back** do nothing (Logic-only commands). |
| MainStage | Works as with Arturia's MainStage profile. |
| Logic Pro | Not tested on real Logic (not installed). The harness shows it gets the same controls as Arturia's script, with the port bug fixed. |

GarageBand findings:

- **Tap** (Logic command 532): GarageBand has no tap tempo.
- **Back**:
  - Logic's close-plug-in-window command (1366) does nothing.
  - The generic close-window command (529) can close the project as well as the
    plug-in window on one press.
  - The undocumented `CS_INSTOPEN` parameter is unreliable.

  Back is therefore left as 1366: correct in Logic, ignored in GarageBand.
- **Device-mode faders** control the instrument's raw parameters 9–16, which is
  Arturia's design, also in Logic.
- **Arturia plug-ins** (Analog Lab, Mini V…) take over the KeyLab's screen and
  capture Back themselves.
- GarageBand doesn't write the scripts' Lua messages to the system log.

The single-app test versions used during these tests (Back as 529,
`CS_INSTOPEN`, unassigned) were removed with the other Arturia-derived files.

## Layout

| Path | Contents |
|---|---|
| `build.py` | Extracts Arturia's scripts from their downloads, fixes the Logic one, builds the merged script |
| `test/harness.lua` | Loads a script as Logic/GarageBand or MainStage and compares it with a reference |
| `tools/` | MIDI port lister, DAW-port listener, Lua 5.2.4 build script |
| `downloads/` | Arturia's two zips (not tracked) |
| `build/` | Everything `build.py` writes (not tracked) |

`build/` contains:

- `KeyLab <size> mk3.device/config.lua`: the merged script to install.
- `arturia/logic/` and `arturia/mainstage/`: Arturia's scripts, exactly as extracted.
- `logic-patched/`: the fixed Logic script on its own.

## Usage

Get Arturia's two zips into `downloads/`. Either let `build.py` fetch them:

```sh
python3 build.py --download
```

or download them from the
[KeyLab mk3 resources page](https://www.arturia.com/products/hybrid-synths/keylab-mk3/resources)
(Logic Pro Script and MainStage Script) and put them in `downloads/` unchanged.

Build:

```sh
python3 build.py          # KeyLab 61 (default)
python3 build.py 49 88
```

Verify (builds Lua 5.2.4 locally the first time):

```sh
tools/build-lua.sh
L=tools/lua-5.2.4/src/lua; M="build/KeyLab 61 mk3.device/config.lua"
${L}c -p "$M"
$L test/harness.lua logic "$M" "build/logic-patched/KeyLab 61 mk3.device/config.lua"
$L test/harness.lua mainstage "$M" "build/arturia/mainstage/KeyLab 61 mk3.device/config.lua"
$L test/harness.lua logic "build/arturia/logic/KeyLab 61 mk3.device/config.lua"   # shows the original bug: inport=false
```

Install (quit GarageBand, MainStage and Logic first). Re-running Arturia's
installers overwrites this file, so run it again afterwards:

```sh
cp "build/KeyLab 61 mk3.device/config.lua" \
   ~/Music/Audio\ Music\ Apps/MIDI\ Device\ Profiles/Arturia/KeyLab\ 61\ mk3.device/config.lua
```

Restore Arturia's MainStage profile:

```sh
cp "build/arturia/mainstage/KeyLab 61 mk3.device/config.lua" \
   ~/Music/Audio\ Music\ Apps/MIDI\ Device\ Profiles/Arturia/KeyLab\ 61\ mk3.device/config.lua
```

In GarageBand, keep the KeyLab on its **DAW** program. If no Auto Assign prompt
appears, choose the KeyLab under Settings → Audio/MIDI → MIDI Controller.

Tools:

```sh
swift tools/list-keylab-ports.swift          # port names
swift tools/listen-daw-port.swift 120        # print DAW-port messages for 120 s
```

## Status

The `MIDI_IN` bug is being reported to Arturia (October 2026).
