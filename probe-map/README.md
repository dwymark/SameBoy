# SameBoy debugger and core probe map

This directory holds a `probe-map/1` map of SameBoy's text debugger (`Core/debugger.c`) and the emulator core under it, together with the headless harness and probe list that produced it. It is a delivery vehicle for the map, not a change meant to merge into SameBoy.

## Contents

| File | Role |
|------|------|
| `sameboy-debugger.probe-map.jsonl` | The map: one JSON record per line, `meta` first. Every claim is `measured` (a probe ran it), `source` (code at `ea667ad`), or `unverified`. Read `meta.read_order` top-down; findings come before the raw probes. |
| `harness.c` | Headless libsameboy host. Mode `dbg` feeds a script to the debugger's input callback; `core` and `core2` print core metrics. |
| `mkroms.py` | Writes the fixtures: `basic.gb` (no MBC), `mbc5.gb` (4 banks, bank n filled with `$B0|n`), `basic.sym`, and stub DMG/CGB boot ROMs. |
| `probes.py` | The probe list as data. |
| `run_probes.py` | Runs every probe with `SEED=1` and writes `out/<id>.txt` plus `out/results.json`. |
| `build_map.py` | Renders the JSONL from the probe list, the transcripts, and the hand-written findings. |
| `gate.py` | The probe-map validator; must print `GO`. |
| `out/` | The transcripts and scripts of the committed run. |

## Reproduce

From the repository root:

```sh
make lib CONF=release -j8
cd probe-map
python3 mkroms.py .
cc -O1 -std=gnu11 -D_GNU_SOURCE -I.. harness.c ../build/lib/libsameboy.a -lm -o harness
python3 run_probes.py && python3 build_map.py && python3 gate.py sameboy-debugger.probe-map.jsonl
```

`make lib` installs empty headers under `build/include` when `cppp` is missing, so the harness compiles against `Core/` directly. The probe `seconds` metrics and the turbo-pacing probe depend on wall-clock time; everything else is reproducible with the fixed seed.

## Limits

The boot ROMs are stubs because `rgbasm` was unavailable, so boot-time register values are not SameBoy's real post-boot values. Double speed, HDMA, OAM DMA, serial, audio with sound playing, and mappers other than none and MBC5 were not probed. The `caveat` and `owed` records in the map list these with the commands that would close them.
