# Probe list as data. run_probes.py executes it; build_map.py renders JSONL from it.
F3 = ["!frames 3"]
def D(id, axis, label, script, rom="basic.gb", model="002", env=None, stdin=None):
    return dict(id=id, axis=axis, label=label, mode="dbg", model=model, rom=rom, script=script, env=env or {}, stdin=stdin)
def C(id, axis, label, model, rom="basic.gb", stdin=None):
    return dict(id=id, axis=axis, label=label, mode="core", model=model, rom=rom, script=None, env={}, stdin=stdin)
SYM = {"SYMS": "basic.sym"}
P = [
 # --- baseline / determinism / identity
 D("base.a", "baseline", "3 frames then state, run 1", F3 + ["!state"]),
 D("base.b", "baseline", "3 frames then state, run 2 (determinism)", F3 + ["!state"]),
 D("base.idsoft", "baseline", "identity: 'softbreak off' (the default) before running", ["softbreak off"] + F3 + ["!state"]),
 D("base.idprint", "baseline", "identity: side-effect-free print before running", ["print $0"] + F3 + ["!state"]),
 # --- command resolution
 D("cmd.b", "command-resolution", "'b $200' resolves to breakpoint", ["b $200", "list"]),
 D("cmd.d", "command-resolution", "'d' resolves to disassemble, not delete", ["d $150"]),
 D("cmd.de", "command-resolution", "'de' resolves to delete", ["b $200", "de", "list"]),
 D("cmd.un", "command-resolution", "'un' resolves to undo, not unwatch", ["un"]),
 D("cmd.re", "command-resolution", "'re' resolves to registers; 'res' to reset", ["re", "res"]),
 D("cmd.u", "command-resolution", "'us' usage, 'unw' unwatch", ["us", "unw"]),
 D("cmd.alias", "command-resolution", "aliases eval, x, bt, mbc, bs", ["eval 1+1", "x/4 $100", "bt", "mbc", "bs"]),
 D("cmd.unknown", "command-resolution", "unknown command", ["zz", "breakpointx $100"]),
 D("cmd.help", "command-resolution", "help listing", ["help"]),
 D("cmd.helpb", "command-resolution", "help for an abbreviated command", ["help b", "help x"]),
 D("cmd.ws", "command-resolution", "leading spaces and empty line", ["   print 7", "", "print 8"]),
 # --- expression evaluator
 D("ex.lit", "expression", "literal bases", ["print 10", "print $10", "print 0x10", "print $", "print 0x", "print 70000", "print 1 2"]),
 D("ex.prec", "expression", "precedence vs C", ["print 4-1&2", "print 1<<2+1", "print 2+3*4", "print 1+1==2", "print 10-3-2"]),
 D("ex.unary", "expression", "unary minus and plus", ["print -1", "print 0-1", "print +5"]),
 D("ex.div0", "expression", "division and modulo by zero", ["print 5/0", "print 5%0"]),
 D("ex.fmt", "expression", "print format modifiers", ["print/x 255", "print/d $ff", "print/o 8", "print/b 5", "print/b 0", "print/a $c000", "print/xx 1", "print/q 1"]),
 D("ex.regs", "expression", "two-letter register names, including invalid ones", F3 + ["registers", "print bc", "print ac", "print sp", "print ap", "print bp", "print pc", "print hc", "print hl", "print al"]),
 D("ex.syms", "expression", "symbols, and symbols that collide with registers", ["print func1", "print counter", "print a", "print ac", "print bank2_start", "print nosuch"], env=SYM),
 D("ex.deref", "expression", "[] byte and {} word dereference", F3 + ["print [$c000]", "print {$c000}", "print [$c000]+[$c000+1]", "print {$c000}+{$c000+1}", "print {$c000+1}+{$c000}"]),
 D("ex.bank", "expression", "bank-qualified dereference on MBC5 (bank 2 mapped)", F3 + ["cartridge", "print [$4150]", "print [1:$4150]", "print [2:$4150]", "print [3:$4150]", "print [0:$4150]", "print [$0150]", "print 1:$4000", "print 1:$4000+1", "print 1:$4000-1:$3000"], rom="mbc5.gb"),
 D("ex.assign", "expression", "assignment to registers and memory", ["print a = 5", "print bc = $1234", "print h = $c0", "print [$c010] = 7", "print {$c012} = $abcd", "x/4 $c010", "registers", "print 1 = 2", "print a == 5"]),
 # --- breakpoints and stepping
 D("bp.hit", "breakpoints", "breakpoint at func2, backtrace there", ["b $210", "c", "bt", "registers"]),
 D("bp.finish", "breakpoints", "finish out of func2 then out of func1", ["b $210", "c", "delete", "finish", "finish"]),
 D("bp.next", "breakpoints", "next over the call at loop", ["b $16e", "c", "delete", "next", "next"]),
 D("bp.step", "breakpoints", "step into the call at loop", ["b $16e", "c", "delete", "step", "step"]),
 D("bp.cond", "breakpoints", "conditional breakpoint on counter", ["b $200 if [$c000] == 3", "c", "print [$c000]"]),
 D("bp.condside", "breakpoints", "condition with assignment is evaluated when the breakpoint is set", ["b $200 if a = 9", "registers"]),
 D("bp.range", "breakpoints", "exclusive and inclusive ranges, list output", ["b $210 to $212", "b $167 to $168 inclusive", "b $300 to $305 inclusive", "list"]),
 D("bp.rangehit", "breakpoints", "inclusive single-gap range $211 to $212 breaks at $212", ["b $211 to $212 inclusive", "c", "registers"]),
 D("bp.rangebad", "breakpoints", "range errors", ["b $200 to $100", "b 1:$4000 to 2:$4010"]),
 D("bp.delete", "breakpoints", "delete by id and ids after deletion", ["b $200", "b $210", "delete 1", "b $167", "list", "delete 9", "delete x"]),
 D("bp.jump", "breakpoints", "jump-to breakpoint stops before the call executes", ["b/j $200", "c", "registers", "list"]),
 D("bp.jumpirq", "breakpoints", "jump-to breakpoint on the vblank vector", ["b/j $40", "c", "registers"]),
 D("bp.soft", "breakpoints", "softbreak on: ld b,b stops", ["softbreak on", "c", "registers"]),
 D("bp.softoff", "breakpoints", "softbreak default: ld b,b does not stop within 3 frames", ["!frames 3", "registers"]),
 D("bp.bank", "breakpoints", "bank-qualified breakpoint in bank 0 hit", ["b 0:$200", "c", "registers"], rom="mbc5.gb"),
 D("bp.bankmiss", "breakpoints", "bank-qualified breakpoint for an unmapped bank", ["b 3:$4000", "!frames 3", "registers"], rom="mbc5.gb"),
 # --- watchpoints
 D("wp.write", "watchpoints", "default write watchpoint on $c001", ["watch $c001", "c", "registers", "c"]),
 D("wp.read", "watchpoints", "read watchpoint on $c000", ["watch/r $c000", "c", "registers"]),
 D("wp.cond", "watchpoints", "write watchpoint with new/old condition", ["watch $c000 if new == 3", "c", "print [$c000]", "watch $c001 if old == 1", "c", "print [$c001]"]),
 D("wp.bogus", "watchpoints", "unknown start symbol with a valid range end", ["watch nosuch to $c010", "list"]),
 D("wp.bogus2", "watchpoints", "unknown start symbol without range", ["watch nosuch", "list"]),
 D("wp.dbgwrite", "watchpoints", "debugger writes do not trigger watchpoints", ["watch $c000", "print [$c000] = 1", "list", "!frames 1", "registers"]),
 D("wp.mods", "watchpoints", "modifier validation", ["watch/x $c000", "watch/rw $c000", "watch/wr $c001", "list", "unwatch 1", "unwatch", "list"]),
 # --- undo / ticks / usage / backstep
 D("un.redo", "undo-ticks", "undo twice after an assignment", ["print a = 5", "registers", "undo", "registers", "undo", "registers", "undo"]),
 D("un.cont", "undo-ticks", "undo a continue", ["!frames 3", "print [$c000]", "undo", "print [$c000]", "registers"]),
 D("tk.frame", "undo-ticks", "ticks over one frame", ["ticks", "!frames 1", "ticks", "!frames 1", "ticks keep", "ticks"]),
 D("tk.framecgb", "undo-ticks", "ticks over one frame on CGB-E", ["ticks", "!frames 1", "ticks", "!frames 1", "ticks"], model="205"),
 D("tk.usage", "undo-ticks", "usage after a few frames", ["usage", "!frames 5", "usage"]),
 D("bk.norewind", "undo-ticks", "backstep without rewind", ["!frames 2", "backstep"]),
 D("bk.rewind", "undo-ticks", "backstep with rewind enabled", ["!frames 2", "registers", "backstep", "registers", "backstep", "registers"], env={"REWIND": "10"}),
 # --- inspection
 D("in.x", "inspection", "examine counts and syntax", ["x/4 $150", "x/$12 $150", "x/3s $150", "x/8s $150", "x $150"]),
 D("in.dis", "inspection", "disassemble with symbols", ["disassemble/4 func1", "disassemble/3 $150"], env=SYM),
 D("in.cart", "inspection", "cartridge on no-MBC and MBC5", ["cartridge"]),
 D("in.cart5", "inspection", "cartridge on MBC5", F3 + ["cartridge"], rom="mbc5.gb"),
 D("in.lcd", "inspection", "lcd after 3 frames", F3 + ["lcd"]),
 D("in.apu", "inspection", "apu overview and channel", ["apu", "apu 1", "apu 9", "wave/l"]),
 D("in.pal", "inspection", "palettes on DMG and CGB", ["palettes"]),
 D("in.palcgb", "inspection", "palettes on CGB-E", ["palettes"], model="205"),
 D("in.dma", "inspection", "dma", ["dma"]),
 D("in.reset", "inspection", "reset variants", F3 + ["reset quick", "print [$c000]", "reset", "reset reload", "reset bogus"]),
 # --- host / core
 C("core.dmg", "core", "DMG-B core metrics", "002"),
 C("core.mgb", "core", "MGB core metrics", "100"),
 C("core.sgb", "core", "SGB (HLE) core metrics", "004"),
 C("core.sgbnosfc", "core", "SGB without SFC core metrics", "084"),
 C("core.cgb0", "core", "CGB-0 core metrics", "200"),
 C("core.cgbe", "core", "CGB-E core metrics", "205"),
 C("core.agb", "core", "AGB core metrics", "207"),
 C("core.stdin", "core", "default async input callback reads host stdin", "002", stdin="print 6*7\n"),
 C("core.stdinint", "core", "default callback: a lone ^C byte breaks", "002", stdin="\x03\nprint 5\n"),
]
P += [
 D("un.cont2", "undo-ticks", "undo after a register-only print reverts the continue", ["!frames 3", "print 1", "undo", "registers"]),
 D("un.printmem", "undo-ticks", "does a memory-reading print change the save state?", ["!frames 3", "!state", "print 1", "!state", "print [$c000]", "!state", "print [$c000]", "!state"]),
 D("bk.step", "undo-ticks", "backstep twice from inside func2", ["b $213", "c", "delete", "registers", "backstep", "registers", "backstep", "registers"], env={"REWIND": "10"}),
 D("in.palcgb2", "inspection", "palettes on CGB-E, second run (determinism of power-on noise)", ["palettes"], model="205"),
 D("ex.io", "expression", "reading IO through the evaluator", F3 + ["print [$ff44]", "print [$ff04]", "print [$ff04]", "print [$ff0f]", "print [$ffff]"]),
 D("cmd.state", "command-resolution", "stopped-state guards", ["interrupt", "continue 5", "next now", "ticks bogus"]),
 D("pace.60", "pacing", "60 frames through plain GB_run: wall time", ["!frames 60", "!state"]),
 D("pace.60turbo", "pacing", "60 frames with GB_set_turbo_mode(on): wall time", ["!frames 60", "!state"], env={"TURBO": "1"}),
 D("pace.60cgb", "pacing", "60 frames on CGB-E through plain GB_run: wall time", ["!frames 60", "!state"], model="205"),
]
P += [
 D("un.printmem2", "undo-ticks", "two register-only prints: state change comes from the first command's display/APU sync", ["!frames 3", "print 1", "!state", "print 1", "!state", "print [$c000]", "!state"]),
 D("bk.step2", "undo-ticks", "backstep twice inside func2 after two frames of rewind history", ["!frames 2", "b $213", "c", "delete", "registers", "backstep", "registers", "backstep", "registers"], env={"REWIND": "10"}),
 D("seed.a", "baseline", "fixed seed 1: state digest, run A", F3 + ["!state", "x/4 $c010"]),
 D("seed.b", "baseline", "fixed seed 1: state digest, run B", F3 + ["!state", "x/4 $c010"]),
 D("seed.2", "baseline", "seed 2: power-on noise differs", F3 + ["!state", "x/4 $c010"], env={"SEED": "2"}),
 D("seed.off", "baseline", "GB_random_set_enabled(false): power-on RAM", F3 + ["!state", "x/4 $c010"], env={"NORANDOM": "1"}),
]
P += [
 dict(id="core2.dmg", axis="core", label="no boot ROM, boot-callback count, sample rate, cross-model state load (DMG host)", mode="core2", model="002", rom="basic.gb", script=None, env={}, stdin=None),
 dict(id="core2.cgbe", axis="core", label="same, CGB-E host", mode="core2", model="205", rom="basic.gb", script=None, env={}, stdin=None),
]
P += [D("ex.bankx", "expression", "examine and assignment with explicit bank 0 vs current bank on MBC5", F3 + ["x/2 0:$4150", "x/2 2:$4150", "x/2 $4150", "print [0:$4150]"], rom="mbc5.gb")]
