import json, os, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probes import P
here = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(f"{here}/out/results.json"))
DBG = "Core/debugger.c"
recs = []
def add(**r): recs.append(r)

add(type="meta", id="meta", format="probe-map/1", target="SameBoy (dwymark/sameboy)", shape="debugger command language over an emulator core (CLI-shaped surface; firmware-shaped internals)",
    title="SameBoy text debugger and core internals", date="2026-11-21",
    purpose="Tell an agent what SameBoy's text debugger accepts and actually does, where it silently does something else, and how the emulator core under it behaves when hosted headlessly, with each claim marked measured/source/unverified.",
    read_order=["meta", "build", "assumption", "caveat", "finding", "recipe", "owed", "control", "probe"],
    record_types={"meta": "this header", "build": "how the library and the probe harness were built and made deterministic",
                  "assumption": "a scoping choice made without asking, with the alternative passed over",
                  "caveat": "a limit on what this map can claim", "finding": "a claim beyond any single record, with the records it rests on",
                  "recipe": "a procedure an agent can follow", "owed": "a probe that could not run here, with its command",
                  "control": "one debugger command, expression-language feature, or core API/mechanism", "probe": "one harness execution with its argv, digest and transcript excerpt"})

add(type="build", id="build", repo="https://github.com/dwymark/sameboy", commit="ea667ad79aa28409f034b1fd6da7304e1844750d", shallow=True, version="1.0.5",
    invocation="make lib CONF=release -j8  (in the repo; outputs build/lib/libsameboy.a, untracked)",
    options={"CONF": "release (-O3 -ffast-math -flto -DNDEBUG)", "debugger": "compiled in", "rewind": "compiled in", "cheat_search": "compiled in", "timekeeping": "compiled in (GB_run sleeps in real time unless turbo)"},
    harness="harness.c in the job dir: cc -O1 -std=gnu11 -D_GNU_SOURCE -I<repo> harness.c <repo>/build/lib/libsameboy.a -lm. Modes: dbg (feeds a script to GB_set_input_callback; '!frames N', '!ticks N', '!state', '!quit' are harness directives), core, core2.",
    fixtures="mkroms.py writes basic.gb (no MBC, 32 KiB), mbc5.gb (MBC5, 4 banks; bank n filled with $B0|n; program maps bank 2), basic.sym, and stub boot ROMs dmg_stub.bin/cgb_stub.bin (ld sp,$fffe; NOPs; ld a,1; ldh ($50),a at $FC).",
    test_rom_layout={"entry": "$0150 init (LCDC=$91, IE=1, EI)", "loop": "$0167 (mbc5: $016C): inc [$c000]; call func1; halt; nop; jr loop", "func1": "$0200: inc [$c001]; call func2; ret", "func2": "$0210: ld b,$42; ld b,b; ld c,7; ret", "vblank": "$0040 -> $0320: inc [$c002]; reti"},
    determinism="Core/random.c:34 seeds the power-on RNG from time(NULL) in a constructor, so states differ across wall-clock seconds. Harness calls GB_random_seed(1) before GB_init (SEED env, default 1 in run_probes.py); GB_set_rtc_mode ACCURATE; joypad bouncing off. Verified: base.a/base.b and seed.a/seed.b byte-identical stdout.",
    gotchas=["`make lib` writes build/include/sameboy/*.h through `cppp` (Makefile:935); with cppp absent every installed header is 0 bytes and make still exits 0. Compile against Core/ instead.",
             "rgbds (rgbasm) is not installed and building it from source was not permitted here, so SameBoy's own boot ROMs were not built; stub boot ROMs stand in.",
             "Without GB_set_input_callback / GB_set_async_input_callback the core reads the host's stdin every vblank (see finding f.stdin)."],
    outputs="job dir out/<probe>.txt (stdout transcript), out/results.json")

for a in [
 ("a.target", "Primary target is the text debugger (Core/debugger.c) as a command language, probed through a headless libsameboy host; the core is mapped as the substrate the debugger reads and steers.", "The request named the text debugger and the emulator's guts; the debugger is the only built-in textual window into the guts, so probing through it exercises both.", "A per-subsystem PPU/APU/timer accuracy map driven by test ROMs (mooneye, blargg).", "the person cares about emulation accuracy rather than tooling"),
 ("a.host", "Drive the debugger through a custom C host linking libsameboy.a, not the SDL frontend.", "SDL2 headers are absent here, and a host gives exact control of input/log callbacks and cycle counting.", "Build SDL frontend and pipe stdin to it.", "frontend-specific behaviour (SDL's reload callback, symbol auto-load, Ctrl-C) matters"),
 ("a.boot", "Use a hand-written stub boot ROM rather than SameBoy's real boot ROMs.", "rgbasm is unavailable; the stub reaches $0100 with SP=$FFFE and all other registers zero.", "Real boot ROMs (post-boot register values, logo check, CGB palette setup, KEY0 write).", "probes depend on post-boot register values or CGB compatibility-mode selection"),
 ("a.roms", "Use two hand-assembled ROMs (no-MBC, MBC5) instead of commercial or test-suite ROMs.", "Fully known code layout lets every breakpoint/watchpoint/backtrace probe have a predicted answer.", "Real games, which exercise more mappers and timing.", "mapper-specific debugger output (MBC1 modes, RTC, HuC3) matters"),
 ("a.models", "Debugger probes run on DMG-B (0x002) unless noted; core probes span DMG-B, MGB, SGB, SGB-noSFC, CGB-0, CGB-E, AGB.", "The debugger is model-agnostic apart from 'palettes'; core metrics are where model differences show.", "Running every debugger probe on every model.", "a debugger command is suspected to misbehave on CGB/SGB only"),
]:
    add(type="assumption", id=a[0], choice=a[1], reason=a[2], alternative=a[3], revisit_if=a[4])

for c in [
 ("c.listen", "No probe here exercises double speed, HDMA, OAM DMA, serial, the APU with sound playing, or any MBC other than none/MBC5. Claims about those come from source only."),
 ("c.stub", "All 'measured' register values at boot reflect the stub boot ROM, not SameBoy's real boot ROMs (a.boot)."),
 ("c.census", "Core control records (ids core.*) were gathered by a read-only subagent; ten of its line cites were spot-checked against the pinned commit and held within two lines. Treat the rest as source-level but less verified than the debugger cites."),
 ("c.release", "The library is a release build: NDEBUG removes asserts and GB_CONTEXT_SAFETY checks, so misuse crashes rather than asserting. Debug-build behaviour was not probed."),
 ("c.digest", "probe.digest is md5 of the harness stdout, which echoes the script; equal digests therefore only arise between identical scripts. Cross-probe state equality is in metrics.final_state_fnv."),
]:
    add(type="caveat", id=c[0], text=c[1])

# ---------------- findings
F = [
 ("f.bank0", "Bank-qualified dereference ignores an explicit bank 0: [0:$4150] reads whatever bank is mapped (returned $B2 with bank 2 mapped), while [1:], [2:], [3:] switch correctly.", "measured", ["ex.bank", "ex.bankx", f"{DBG}:546", f"{DBG}:551"], "The rvalue [] and {} paths test `if (addr.bank)` instead of `addr.has_bank`; the lvalue and examine paths use has_bank, so x 0:$4150 returned bank 0's bytes (f3 31) in ex.bankx while print [0:$4150] returned $b2."),
 ("f.regfall", "Two-letter register names fall through a switch without break: 'ac' reads BC, 'ap' and 'bp' read SP, 'hc' reads PC, 'al' reads HL. Same in lvalue position, so 'ac = 1' writes BC.", "measured", ["ex.regs", f"{DBG}:648", f"{DBG}:470"], "Each case tests string[1] and falls to the next case on mismatch. A typo gives a plausible value, not an error."),
 ("f.shadow", "Symbols are looked up only after registers, so symbols named a..l, af/bc/de/hl/sp/pc, or any fall-through name such as 'ac' are unreachable by name; the disassembler still prints them, producing 'LD hl, a ; =$c001' for an immediate.", "measured", ["ex.syms", "in.dis", f"{DBG}:677"], "print a with symbol a=$c001 printed the A register; disassemble/4 func1 rendered the $c001 immediate as 'a'."),
 ("f.brace", "Curly-brace word dereference is not tracked by the operator scanner's depth counter, so an operator inside a later {...} is chosen as the split point: '{$c000}+{$c000+1}' fails with 'Failed to parse: 1}' while the same expression with [] works and the operands reversed happen to work.", "measured", ["ex.deref", f"{DBG}:584"], "Depth counts only () and []."),
 ("f.prec", "Operator precedence is deliberately not C: + - | || share the lowest arithmetic tier, * / % & && ^ the next, << >> the highest, comparisons below all and = between. '4-1&2' = 4 (C: 2), '1<<2+1' = 5 (C: 8). Same-tier operators associate left.", "measured", ["ex.prec", f"{DBG}:345"], "The source comments 'This is not C-like ... Deal with it.'"),
 ("f.literals", "Bare numbers are decimal and print shows hex: 'print 10' gives =$a. '$' and '0x' alone evaluate to 0, out-of-range literals wrap silently (70000 -> $1170), and there is no unary minus or plus ('-1' -> 'Expected expression.'). Division and modulo by zero give 0.", "measured", ["ex.lit", "ex.unary", "ex.div0", f"{DBG}:700"], ""),
 ("f.condside", "Breakpoint and watchpoint conditions are evaluated once when set, to validate them, with side effects: 'b $200 if a = 9' set A to 9 immediately.", "measured", ["bp.condside", f"{DBG}:1055", f"{DBG}:1231"], "The source carries a Todo noting this."),
 ("f.wpbogus", "watch with an unparseable start but a valid 'to' end creates a watchpoint from $0000: 'watch nosuch to $c010' logs the error and then sets $0000-$c010 (write), covering ROM-area mapper writes and all of VRAM.", "measured", ["wp.bogus", "wp.bogus2", f"{DBG}:1252", f"{DBG}:1259"], "The start's error flag is overwritten by the end's evaluation before it is checked; without 'to' the error is honoured."),
 ("f.rangeshow", "A range whose end is exactly start+1 is stored with length 0, so 'b X to X+1 inclusive' prints and lists as the single address X '(inclusive)' even though it does break on X+1.", "measured", ["bp.range", "bp.rangehit", f"{DBG}:1112", f"{DBG}:1440"], "Display-only: should_break adds `inclusive` to the end check."),
 ("f.jumpto", "Jump-to breakpoints (b/j) predict the next PC from the opcode, so they fire on plain fall-through as well as jumps, calls and interrupts, stopping one instruction early: b/j $40 stopped at $003F, a NOP in the boot area, before any interrupt.", "measured", ["bp.jump", "bp.jumpirq", f"{DBG}:3090"], "For PCs or SPs outside ROM/WRAM/HRAM it snapshots full state every instruction and rewinds on a hit (non-trivial path), which is expensive."),
 ("f.stopsites", "Stop positions differ by mechanism: breakpoints stop before executing the address; watchpoints stop after the accessing instruction (PC shows the next one); softbreak 'ld b,b' stops after it executes; 'next' on HALT stops at the instruction after the HALT once the CPU wakes (an interrupt in this ROM).", "measured", ["bp.hit", "wp.write", "wp.read", "bp.soft", "bp.next"], ""),
 ("f.undo", "undo is a single-slot toggle: undoing an undo redoes it, indefinitely. Any command that changes the save state takes the slot, and a print that reads main-bus memory changes the state (it updates the open-bus latch), so 'print [$c000]' after 'continue' makes 'continue' un-undoable.", "measured", ["un.redo", "un.cont", "un.cont2", "un.printmem2", f"{DBG}:2510", f"{DBG}:2173", "Core/memory.c:816"], "Every command costs two full save-state serialisations plus a memcmp."),
 ("f.stdin", "A host that does not install input callbacks has its stdin consumed: the default async callback polls fd 0 every vblank and executes what it reads as debugger commands ('print 6*7' printed =$2a mid-run). EOF becomes 'c', printing 'Program is running...' into the log; a line starting with byte 0x03 breaks into the debugger.", "measured", ["core.stdin", "core.stdinint", "core.dmg", "Core/gb.c:96", "Core/gb.c:69", "Core/gb.c:81"], "GB_set_input_callback replaces the async default too when the old callback was the default."),
 ("f.seed", "Power-on RAM, palettes and wave RAM come from a process-global RNG seeded with time(NULL) at load, so identical runs differ across a second boundary. GB_random_seed(k) before GB_init makes runs reproducible; GB_random_set_enabled(false) zeroes the noise.", "measured", ["seed.a", "seed.b", "seed.2", "seed.off", "Core/random.c:34"], "Found when base.a and base.b differed in an unseeded rerun."),
 ("f.pace", "GB_run paces to real time unless turbo is on: 60 frames through a GB_run loop took 0.99 s on DMG and CGB. With GB_set_turbo_mode(on, no_frame_skip=false) the wall time stays near 1 s but the core ran about 1358 frames while delivering only 60 vblank callbacks, so frame counting through the vblank callback undercounts in that mode.", "measured", ["pace.60", "pace.60cgb", "pace.60turbo", "Core/timing.c:58"], "Use turbo with no_frame_skip=true, or GB_run_frame, for headless work."),
 ("f.runframe", "GB_run_frame's return is not the frame's duration: it returned a constant 5245 ns per frame on DMG/MGB, 0 on CGB/AGB, 465 on SGB-noSFC, 26539 on SGB, instead of ~16.7 ms.", "measured", ["core.dmg", "core.cgbe", "core.sgb", "core.sgbnosfc", "Core/gb.c:1250", "Core/timing.c:72"], "It forces turbo with cap 0, and GB_timing_sync zeroes cycles_since_last_sync every LCDC_PERIOD/3 in that mode, so only the remainder since the last sync is returned."),
 ("f.units", "Cycle units: GB_run returns 8 MHz ticks (a single-speed NOP = 8); the debugger's 'ticks' reports T-cycles (70224 per frame, the first frame after the stub boot 66836) plus 'absolute 8MHz ticks' at twice that.", "measured", ["core.dmg", "tk.frame", "tk.framecgb", "Core/timing.c:506"], ""),
 ("f.sgbhle", "On HLE SGB the CPU does not run during the intro animation: GB_run returns 228 every call, the execution callback saw 0 instructions in 60 frames, and PC stayed $0000.", "measured", ["core.sgb", "Core/gb.c:1197"], "SGB without SFC behaves like DMG here."),
 ("f.statesize", "Save-state size varies with model: 50692 bytes on DMG/MGB/SGB-noSFC, 83460 on CGB-0/E and AGB, 126341 on HLE SGB.", "measured", ["core.dmg", "core.cgbe", "core.agb", "core.sgb"], ""),
 ("f.modelswap", "Loading a CGB-C state into a CGB-E instance succeeds and silently turns the instance into CGB-C (GB_get_model 0x203). A CGB state is refused by a DMG instance (rc 22).", "measured", ["core2.cgbe", "core2.dmg", "Core/save_state.c:1377"], ""),
 ("f.noboot", "Without a boot ROM, $0000-$00FF (and on CGB $0200-$08FF) keep reading the zero-filled boot area forever: FF50 reads $FE, [$0040] reads $00, and on CGB the cart's own code at $0200 is shadowed, so the test ROM's 'call $0200' slid through NOPs (PC $04D7 after 1000 steps).", "measured", ["core2.dmg", "core2.cgbe", "Core/memory.c:1629"], "Hosts must load a boot ROM or the low pages of the cart are not the cart."),
 ("f.backstep", "backstep needs rewind enabled (GB_set_rewind_length) and at least one vblank of history: before the first frame it reports 'Reached the end of the rewind buffer'; with history it steps back one instruction at a time (0213 -> 0212 -> 0210). Backstepping across a HALT stalled at the instruction after the HALT.", "measured", ["bk.norewind", "bk.step", "bk.step2", "bk.rewind"], "The HALT stall cause is unverified (likely instruction counting while halted)."),
 ("f.cmdprefix", "Commands resolve by the first table entry whose minimum prefix is met, in table order: 'b' breakpoint, 'd' disassemble (not delete), 'de' delete, 'un' undo (not unwatch), 're' registers, 'res' reset, 'us' usage. Abbreviations that look natural can pick an unexpected command.", "measured", ["cmd.b", "cmd.d", "cmd.de", "cmd.un", "cmd.re", "cmd.u", f"{DBG}:2296"], ""),
 ("f.xcomma", "examine in assembler syntax leaves a trailing comma on a partial line: 'x/3s $150' prints 'db $f3, $31, $fe, ; 0150'.", "measured", ["in.x", f"{DBG}:1580"], ""),
 ("f.evalret", "The public GB_debugger_evaluate returns true on error, not on success (ret=1 for an unknown symbol, 0 for [$c000]); the header does not say so.", "measured", ["core.dmg", f"{DBG}:2837"], ""),
 ("f.wpdebug", "Writes made by debugger expressions never trigger watchpoints (watchpoints are disabled during evaluation and while stopped); a watch condition's 'old' reads memory before the write lands, 'new' is the incoming value.", "measured", ["wp.dbgwrite", "wp.cond", f"{DBG}:2460"], ""),
 ("f.bankbp", "Bank-qualified breakpoints are ignored until the boot ROM has been unmapped, and match only when that bank is mapped at hit time.", "source", [f"{DBG}:1436", "bp.bank", "bp.bankmiss"], "bp.bank (bank 0) hit and bp.bankmiss (bank 3, never mapped) did not; the boot-ROM gate itself was not probed."),
]
for f in F:
    add(type="finding", id=f[0], claim=f[1], evidence=f[2], rests_on=f[3], basis=f[4])

for r in [
 ("r.host", "Host libsameboy headlessly with the debugger scripted", ["GB_random_seed(k) before GB_init for reproducibility", "GB_init(GB_alloc(), model); GB_set_boot_rom_load_callback(gb, cb) (fires immediately and on every reset)", "GB_set_pixels_output + GB_set_rgb_encode_callback (or GB_set_rendering_disabled)", "GB_set_log_callback to capture debugger output", "GB_set_input_callback(gb, cb) returning the next command, or NULL to resume; this also removes the stdin-polling async default", "GB_load_rom, GB_reset, GB_debugger_break(gb) to stop at the first instruction", "loop GB_run(gb); break back in from the vblank callback with GB_debugger_break"], "harness.c in the job directory"),
 ("r.condbreak", "Break when a variable reaches a value", ["watch $c000 if new == 3   (stops after the writing instruction)", "or b <addr> if [$c000] == 3 (stops before addr)", "avoid '=' in conditions: it assigns, once at set time and at every evaluation"], "wp.cond, bp.cond"),
 ("r.bank", "Read a specific ROM bank", ["x 1:$4000 or print [1:$4000] for banks >= 1", "for bank 0 at $4000 on MBC5 use x 0:$4000 (examine honours has_bank), not print [0:$4000]"], "ex.bankx"),
 ("r.ticks", "Measure cycles between two points", ["stop at the first point; 'ticks' (resets)", "continue to the second point; 'ticks keep' to read without resetting", "T-cycles single speed: 70224 per frame"], "tk.frame"),
]:
    add(type="recipe", id=r[0], goal=r[1], steps=r[2], example=r[3])

for o in [
 ("o.realboot", "Rerun the dbg probes with SameBoy's real boot ROMs", "make bootroms (needs rgbasm) && BOOTDIR=build/bin/BootROMs python3 run_probes.py  (harness boot_cb reads dmg_stub/cgb_stub names; point it at dmg_boot.bin/cgb_boot.bin)", ["a.boot", "boot-time register values"]),
 ("o.sdl", "Probe the SDL frontend's debugger integration (reload callback, symbol auto-load, Ctrl-C)", "make sdl && build/bin/SDL/sameboy rom.gb  (needs SDL2 dev headers)", ["'reset reload' behaviour beyond 'not supported in this frontend'"]),
 ("o.doublespeed", "Confirm GB_run returns 4 per NOP in CGB double speed and how 'ticks' reports it", "ROM: ld a,1; ldh ($4d),a; stop; then NOP loop; harness core mode on 205", ["f.units in double speed"]),
 ("o.mbcs", "cartridge/bank-expression output on MBC1 (mode switching), MBC3+RTC, HuC3", "extend mkroms.py header byte 0x147 and add ex.bank variants", ["mapper-specific debugger output"]),
]:
    add(type="owed", id=o[0], what=o[1], command=o[2], blocks=o[3])

# ---------------- controls: debugger commands
cmds = [
 ("continue", "c[ontinue]", "Resume until the next stop; stopped-only; takes no arguments.", 2236, ["bp.hit", "cmd.state"]),
 ("interrupt", "i[nterrupt]", "Break a running program; 'Program already stopped.' when stopped. Only useful from an async input callback.", 2237, ["cmd.state"]),
 ("reset", "res[et] [quick|reload]", "GB_reset; quick keeps RAM ([$c000] survived); reload needs a frontend reload callback.", 2238, ["in.reset", "cmd.re"]),
 ("next", "n[ext]", "Step over calls (stops when call depth <= 0 and not halted; on HALT runs through the interrupt).", 2242, ["bp.next"]),
 ("step", "s[tep]", "Execute one instruction, entering calls.", 2243, ["bp.step"]),
 ("finish", "f[inish]", "Run until the current function returns (call depth -1).", 2244, ["bp.finish"]),
 ("backstep", "backs[tep] | bs", "Step one instruction backward via the rewind buffer; needs GB_set_rewind_length > 0 and one vblank of history.", 2246, ["bk.norewind", "bk.step2", "bk.rewind"]),
 ("undo", "u[ndo]", "Revert the last state-changing command; single slot, toggles.", 2249, ["un.redo", "un.cont", "un.cont2"]),
 ("registers", "r[egisters]", "AF with flags, BC, DE, HL, SP, PC (symbolised), IME.", 2250, ["cmd.re", "bp.hit"]),
 ("backtrace", "ba[cktrace] | bt", "Call stack from the call/ret hooks; lists the call-instruction sites.", 2251, ["bp.hit", "cmd.alias"]),
 ("print", "p[rint][/a|d|x|o|b] <expr> | eval", "Evaluate and print; default hex with $, banked values as $bb:$aaaa.", 2253, ["ex.fmt", "ex.lit"]),
 ("examine", "x[/[$]count[s]] <expr> | examine", "Hex dump (default 32 bytes, 16 per line) or 'db' assembler lines (8 per line).", 2258, ["in.x", "cmd.alias"]),
 ("disassemble", "d[isassemble][/count] [expr]", "Disassemble count (default 5, decimal only) instructions, default at pc, with symbols.", 2260, ["in.dis", "cmd.d"]),
 ("breakpoint", "b[reakpoint][/j] <expr> [to <end> [inclusive]] [if <cond>]", "Address/range breakpoint, optional condition; /j stops before control reaches the target.", 2261, ["bp.hit", "bp.range", "bp.jump", "bp.cond"]),
 ("delete", "de[lete] [id]", "Delete one breakpoint by id, or all. Ids are never reused within a list.", 2267, ["bp.delete", "cmd.de"]),
 ("watch", "w[atch][/r|w|rw] <expr> [to <end> [inclusive]] [if <cond>]", "Memory watchpoint, default write; conditions may use old/new.", 2268, ["wp.write", "wp.read", "wp.cond", "wp.mods"]),
 ("unwatch", "unw[atch] [id]", "Delete one watchpoint or all.", 2274, ["wp.mods", "cmd.u"]),
 ("softbreak", "so[ftbreak] [on|off]", "Treat 'ld b,b' as a breakpoint; default off; no argument means on.", 2275, ["bp.soft", "bp.softoff", "base.idsoft"]),
 ("list", "l[ist]", "List breakpoints and watchpoints with ranges, flags, conditions.", 2276, ["bp.range", "wp.mods"]),
 ("ticks", "ti[cks] [keep]", "T-cycles, M-cycles and absolute 8 MHz ticks since last reset of the counter.", 2277, ["tk.frame", "tk.framecgb"]),
 ("usage", "us[age]", "CPU busy/idle share for the last frame and last 60 frames (N/A until available).", 2280, ["tk.usage"]),
 ("cartridge", "ca[rtridge] | mbc", "Mapper, RAM size/battery, mapped banks, RTC/rumble.", 2281, ["in.cart", "in.cart5"]),
 ("apu", "apu [1-5]", "APU state, per channel; 5 is NR5x.", 2283, ["in.apu"]),
 ("wave", "wav[e][/f|c|l]", "Wave RAM full, compact, or one-line.", 2285, ["in.apu"]),
 ("lcd", "lcd", "LCDC/STAT decode, LY/LYC, PPU coroutine state and cycles to next event, fetcher state.", 2288, ["in.lcd"]),
 ("palettes", "pal[ettes]", "CGB palette RAM; 'Not available on a DMG.' otherwise.", 2289, ["in.pal", "in.palcgb"]),
 ("dma", "dma", "OAM DMA status.", 2290, ["in.dma"]),
 ("help", "h[elp] [command]", "Command list or one command's help, usage and aliases.", 2292, ["cmd.help", "cmd.helpb"]),
]
for name, syn, eff, line, pr in cmds:
    add(type="control", id=f"dbg.{name}", name=name, syntax=syn, effect=eff, scope="debugger command", evidence="measured", cites=[f"{DBG}:{line}"] + pr, probes=pr)

lang = [
 ("expr.literals", "decimal default; $hex; 0xhex", "Literals parse with strtol, truncate to 16 bits.", [f"{DBG}:700", "ex.lit"]),
 ("expr.operators", "+ - | || ; * / % & && ^ ; << >> ; = ; == != < <= > >= ; :", "Lowest-priority, rightmost operator splits first; ':' builds a banked address; '=' assigns to an lvalue.", [f"{DBG}:345", "ex.prec"]),
 ("expr.deref", "[addr] byte, {addr} little-endian word, optional bank prefix b:addr", "Memory read/write through GB_read_memory/GB_write_memory (with bus side effects).", [f"{DBG}:529", "ex.deref", "ex.bank", "ex.assign"]),
 ("expr.registers", "a f b c d e h l af bc de hl sp pc", "pc evaluates as a banked address; others as plain 16-bit values.", [f"{DBG}:640", "ex.regs"]),
 ("expr.symbols", "symbol names from GB_debugger_load_symbol_file ('bank:addr name' lines, hex, ';' comments)", "Resolve to banked addresses after register names fail.", [f"{DBG}:677", f"{DBG}:2764", "ex.syms"]),
 ("expr.oldnew", "old, new (watch conditions and cheat-search filters only)", "old = value before write (memory read) or read value; new = value being written.", [f"{DBG}:657", "wp.cond"]),
 ("expr.ranges", "<start> to <end> [inclusive]", "Exclusive by default; end must be greater; banks must match.", [f"{DBG}:1012", "bp.range", "bp.rangebad"]),
]
for i, syn, eff, cites in lang:
    add(type="control", id=i, name=i.split(".")[1], syntax=syn, effect=eff, scope="expression language", evidence="measured", cites=cites, probes=[c for c in cites if ":" not in c])

core = [
 ("core.GB_run", "unsigned GB_run(gb)", "One CPU step (instruction, interrupt dispatch or HALT tick); returns 8 MHz ticks; calls the debugger before the step and async debugger input/rewind push on vblank.", ["Core/gb.c:1192", "core.dmg"]),
 ("core.GB_run_frame", "uint64_t GB_run_frame(gb)", "GB_run until vblank under forced turbo; return value is time since the last internal sync, not the frame time.", ["Core/gb.c:1230", "core.dmg"]),
 ("core.turbo", "GB_set_turbo_mode(gb, on, no_frame_skip); GB_set_turbo_cap", "Turbo stops wall-clock sleeping; without no_frame_skip vblank callbacks are dropped to ~60/s of wall time.", ["Core/gb.c:1428", "Core/display.c:199", "pace.60turbo"]),
 ("core.timing_sync", "GB_timing_sync (internal)", "Sleeps to real time at most every LCDC_PERIOD/3 ticks unless turbo.", ["Core/timing.c:58", "pace.60"]),
 ("core.advance_cycles", "GB_advance_cycles(gb, T) (internal)", "Central tick: timers, speed switch, debugger tick counters, PPU, APU, DMA, RTC; doubles cycles to 8 MHz units in single speed.", ["Core/timing.c:472"]),
 ("core.state_machine", "GB_STATE_MACHINE / GB_SLEEP / GB_STATE macros", "Hand-rolled coroutines with a cycle credit balance, used by DIV and the PPU.", ["Core/timing.h:25"]),
 ("core.ppu", "GB_display_run(gb, cycles, force); GB_display_sync", "PPU as one coroutine: LCD-off loop, modes 2/3/0 per line, vblank at LY 144, line-153 quirk; the debugger syncs it before every command.", ["Core/display.c:1533", f"{DBG}:2483", "in.lcd"]),
 ("core.div_tima", "div_counter, TAC falling-edge, tima_reload_state", "TIMA ticks on the falling edge of a selected DIV bit; reload delay and DIV/TAC write glitches emulated.", ["Core/timing.c:195"]),
 ("core.interrupts", "IE & IF & 0x1F, ime, ime_toggle", "5 M-cycle dispatch with IE re-read after the high push; EI delayed one instruction.", ["Core/sm83_cpu.c:1653", "bp.hit"]),
 ("core.halt", "halt(), halt_bug", "HALT with pending interrupt and IME=0 triggers the halt bug; halted GB_run steps advance 4 T-cycles.", ["Core/sm83_cpu.c:1032", "Core/sm83_cpu.c:1625"]),
 ("core.stop", "stop(), KEY1", "STOP resets DIV, performs CGB speed switch when armed.", ["Core/sm83_cpu.c:385"]),
 ("core.memory_map", "read_map[addr>>12] / write_map; GB_read_memory, GB_safe_read_memory", "Dispatch by 4 KiB page; public reads update the open-bus latch and can trigger watchpoints and OAM-bug paths.", ["Core/memory.c:776", "Core/memory.c:816", "un.printmem2"]),
 ("core.boot_unmap", "FF50 bit 0 -> boot_rom_finished (sticky)", "Boot ROM overlays $0000-$00FF (CGB also $0200-$08FF) until written.", ["Core/memory.c:1629", "core2.cgbe"]),
 ("core.boot_rom", "GB_load_boot_rom[_from_buffer]; GB_set_boot_rom_load_callback", "Buffer pads with $FF to 0x900; callback runs at set time and every reset.", ["Core/gb.c:267", "Core/gb.c:1990", "core2.dmg"]),
 ("core.mbc", "GB_configure_cart via header 0x147 -> GB_cart_defs", "Selects mapper and cart RAM; unknown types fall back to ROM-only; MBC1M/MBC30/MMM01 heuristics.", ["Core/mbc.c:160", "in.cart5"]),
 ("core.save_state", "GB_get_save_state_size / GB_save_state_to_buffer / GB_load_state_from_buffer", "Native sections plus BESS trailer; model-dependent size; load only checks family and sizes.", ["Core/save_state.c:250", "Core/save_state.c:1377", "core2.cgbe", "core.sgb"]),
 ("core.rewind", "GB_set_rewind_length(gb, seconds)", "Pushes a delta-compressed state each vblank; backstep and jump-to breakpoints rely on it.", ["Core/rewind.c:115", "bk.step2"]),
 ("core.random", "GB_random_seed / GB_random_set_enabled", "Process-global LCG seeded from time(NULL); fills RAM, palettes, wave RAM at reset.", ["Core/random.c:34", "seed.2", "seed.off"]),
 ("core.default_input", "default_input_callback / default_async_input_callback", "stdin-backed debugger input installed by GB_init.", ["Core/gb.c:51", "Core/gb.c:178", "core.stdin"]),
 ("core.callbacks", "vblank, execution, read/write memory, lcd line/status, log callbacks", "Execution callback fires after the opcode fetch, not for interrupt dispatch or HALT ticks (1298 calls in 60 mostly-halted frames).", ["Core/sm83_cpu.c:1702", "core.dmg"]),
 ("core.sgb_hle", "sgb->intro_animation < 96", "GB_run returns 228 without running the CPU during the SGB intro.", ["Core/gb.c:1197", "core.sgb"]),
 ("core.apu_sample", "GB_set_sample_rate + GB_apu_set_sample_callback", "48180 samples per 60 frames at 48 kHz; setting a rate without a callback is a NULL call in release builds.", ["Core/apu.c:445", "core2.dmg"]),
 ("core.models", "GB_model_t", "DMG-B 0x002, SGB 0x004 (|0x40 PAL, |0x80 no SFC), MGB 0x100, SGB2 0x101, CGB-0..E 0x200-0x205, AGB 0x207.", ["Core/model.h:11", "core.dmg", "core.cgb0", "core.agb"]),
]
for i, syn, eff, cites in core:
    pr = [c for c in cites if ":" not in c]
    add(type="control", id=i, name=i.split(".", 1)[1], syntax=syn, effect=eff, scope="emulator core", evidence="measured" if pr else "source", cites=cites, probes=pr)

# ---------------- probes
def excerpt(txt):
    out = []
    for l in txt.splitlines():
        if re.match(r"^    [0-9a-f]{4}:", l) or "Type 'help'" in l: continue
        out.append(l)
    s = "\n".join(out)
    return s if len(s) <= 1500 else s[:1500] + "\n...[truncated]"
fnv_of = {}
for p in P:
    r = R[p["id"]]; txt = open(f"{here}/out/{p['id']}.txt", errors="replace").read()
    states = re.findall(r"@@state size=(\d+) fnv=(\w+)", txt)
    m = dict(exit=r["exit"], stdout_bytes=r["bytes"], seconds=r["seconds"])
    if states: m["final_state_fnv"] = states[-1][1]; m["state_size"] = int(states[-1][0])
    tt = re.search(r"total_ticks=(\d+)", txt)
    if tt: m["total_8mhz_ticks"] = int(tt.group(1))
    for k in ("run2000", "run_frame_ns", "frames60", "noboot", "modelswap", "samples60", "bootcb"):
        mm = re.search(rf"@@{k}[ =](.*)", txt)
        if mm: m[k] = mm.group(1).strip()
    if states: fnv_of[p["id"]] = states[-1][1]
    add(type="probe", id=p["id"], axis=p["axis"], label=p["label"], model=p["model"], rom=p["rom"],
        argv=r["argv"], env=dict({"SEED": "1"}, **p["env"]), stdin=p["stdin"], script=p["script"],
        digest=r["md5"], evidence="measured", metrics=m, transcript=excerpt(txt), files=[f"out/{p['id']}.txt"])
# identical_to by digest; same_final_state_as by fnv
by_d = collections.defaultdict(list); by_f = collections.defaultdict(list)
for x in recs:
    if x["type"] == "probe":
        by_d[x["digest"]].append(x["id"])
        if x["id"] in fnv_of: by_f[fnv_of[x["id"]]].append(x["id"])
for x in recs:
    if x["type"] == "probe":
        x["identical_to"] = [i for i in by_d[x["digest"]] if i != x["id"]]
        if x["id"] in fnv_of: x["same_final_state_as"] = [i for i in by_f[fnv_of[x["id"]]] if i != x["id"]]

order = {t: i for i, t in enumerate(recs[0]["read_order"])}
recs = [recs[0]] + sorted(recs[1:], key=lambda r: order[r["type"]])
with open(f"{here}/sameboy-debugger.probe-map.jsonl", "w") as f:
    for r in recs: f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(collections.Counter(r["type"] for r in recs))
