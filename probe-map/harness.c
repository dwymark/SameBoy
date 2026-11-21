/* probe-map harness: drives SameBoy's text debugger headlessly, plus core metrics.
   usage: harness MODE MODELHEX ROM [SCRIPT]
   MODE dbg   : stop at first instruction, feed SCRIPT lines to the debugger input callback.
                Lines starting with '!' are harness directives:
                  !frames N   continue, re-break after N vblanks
                  !ticks N    continue, re-break after N 8MHz ticks of GB_run
                  !state      print md5-able hex of save state size and a digest line
                  !quit       stop
   MODE core  : print core metrics (state sizes, GB_run return histogram, cycles/frame). */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include "Core/gb.h"
#include "Core/random.h"

static uint32_t pixels[256 * 224];
static char **lines; static int nlines, li;
static long frames_left = -1, ticks_left = -1, vblanks;
static bool done;
static const char *bootdir;
static uint64_t execs;

static uint32_t rgb(GB_gameboy_t *gb, uint8_t r, uint8_t g, uint8_t b) { return (r << 16) | (g << 8) | b; }
static void logcb(GB_gameboy_t *gb, const char *s, GB_log_attributes_t a) { fputs(s, stdout); }
static void vblank(GB_gameboy_t *gb, GB_vblank_type_t t) {
    vblanks++;
    if (frames_left > 0 && --frames_left == 0) { frames_left = -1; GB_debugger_break(gb); }
}
static void exec_cb(GB_gameboy_t *gb, uint16_t a, uint8_t op) { execs++; }
static void boot_cb(GB_gameboy_t *gb, GB_boot_rom_t type) {
    char p[4096];
    bool cgb = type == GB_BOOT_ROM_CGB || type == GB_BOOT_ROM_CGB_0 || type == GB_BOOT_ROM_AGB || type == GB_BOOT_ROM_CGB_E;
    snprintf(p, sizeof p, "%s/%s", bootdir, cgb ? "cgb_stub.bin" : "dmg_stub.bin");
    GB_load_boot_rom(gb, p);
}
static uint32_t fnv(const uint8_t *d, size_t n) { uint32_t h = 2166136261u; while (n--) { h ^= *d++; h *= 16777619u; } return h; }
static void state_line(GB_gameboy_t *gb) {
    size_t n = GB_get_save_state_size(gb); uint8_t *b = malloc(n);
    GB_save_state_to_buffer(gb, b);
    if (getenv("DUMPSTATE")) { FILE *o = fopen(getenv("DUMPSTATE"), "wb"); fwrite(b, 1, n, o); fclose(o); }
    GB_registers_t *r = GB_get_registers(gb);
    printf("@@state size=%zu fnv=%08x pc=%04x af=%04x bc=%04x de=%04x hl=%04x sp=%04x vblanks=%ld\n",
           n, fnv(b, n), r->pc, r->af, r->bc, r->de, r->hl, r->sp, vblanks);
    free(b);
}
static char *input(GB_gameboy_t *gb) {
    while (li < nlines) {
        char *l = lines[li++];
        printf("@@> %s\n", l);
        if (l[0] != '!') return strdup(l);
        if (!strncmp(l, "!frames ", 8)) { frames_left = atol(l + 8); return strdup("continue"); }
        if (!strncmp(l, "!ticks ", 7)) { ticks_left = atol(l + 7); return strdup("continue"); }
        if (!strcmp(l, "!state")) { state_line(gb); continue; }
        if (!strcmp(l, "!quit")) break;
    }
    done = true;
    return NULL;
}


static unsigned boot_calls; static uint64_t samples;
static void boot_count(GB_gameboy_t *gb, GB_boot_rom_t t) { boot_calls++; boot_cb(gb, t); }
static void sample_cb(GB_gameboy_t *gb, GB_sample_t *s) { samples++; }
static int core2(GB_model_t model, const char *rom) {
    /* (1) no boot ROM at all */
    GB_gameboy_t *g = GB_init(GB_alloc(), model);
    GB_set_pixels_output(g, pixels); GB_set_rgb_encode_callback(g, rgb); GB_set_log_callback(g, logcb);
    GB_set_async_input_callback(g, NULL);
    GB_load_rom(g, rom);
    for (int i = 0; i < 1000; i++) GB_run(g);
    printf("@@noboot ff50=%02x mem0040=%02x pc=%04x af=%04x\n", GB_read_memory(g, 0xff50), GB_read_memory(g, 0x40), GB_get_registers(g)->pc, GB_get_registers(g)->af);
    /* (2) boot callback call count */
    GB_set_boot_rom_load_callback(g, boot_count); unsigned a = boot_calls;
    GB_reset(g); unsigned b = boot_calls; GB_reset(g);
    printf("@@bootcb after_set=%u after_reset1=%u after_reset2=%u\n", a, b, boot_calls);
    /* (3) sample callback rate over 60 frames */
    GB_apu_set_sample_callback(g, sample_cb); GB_set_sample_rate(g, 48000);
    GB_set_turbo_mode(g, true, true); uint64_t ticks = 0; long v0 = vblanks;
    GB_set_vblank_callback(g, vblank);
    while (vblanks - v0 < 60) ticks += GB_run(g);
    printf("@@samples60 samples=%llu ticks=%llu clock_rate=%u\n", (unsigned long long)samples, (unsigned long long)ticks, GB_get_clock_rate(g));
    /* (4) state saved on CGB-C loaded into CGB-E */
    GB_gameboy_t *c = GB_init(GB_alloc(), GB_MODEL_CGB_C), *e = GB_init(GB_alloc(), GB_MODEL_CGB_E);
    GB_set_async_input_callback(c, NULL); GB_set_async_input_callback(e, NULL);
    GB_load_rom(c, rom); GB_load_rom(e, rom);
    size_t n = GB_get_save_state_size(c); uint8_t *buf = malloc(n); GB_save_state_to_buffer(c, buf);
    int rc = GB_load_state_from_buffer(e, buf, n);
    printf("@@modelswap rc=%d model_after=%03x\n", rc, GB_get_model(e));
    GB_gameboy_t *d = GB_init(GB_alloc(), GB_MODEL_DMG_B); GB_set_async_input_callback(d, NULL); GB_load_rom(d, rom);
    rc = GB_load_state_from_buffer(d, buf, n);
    printf("@@cgb_into_dmg rc=%d model_after=%03x\n", rc, GB_get_model(d));
    return 0;
}

int main(int argc, char **argv) {
    if (argc < 4) return 2;
    const char *mode = argv[1]; GB_model_t model = strtol(argv[2], NULL, 16);
    char *slash = strrchr(argv[0], '/'); static char dir[4096];
    snprintf(dir, sizeof dir, "%.*s", slash ? (int)(slash - argv[0]) : 1, slash ? argv[0] : ".");
    bootdir = getenv("BOOTDIR") ? getenv("BOOTDIR") : dir;
    if (getenv("SEED")) GB_random_seed(strtoull(getenv("SEED"), NULL, 0));
    if (getenv("NORANDOM")) GB_random_set_enabled(false);
    GB_gameboy_t *gb = GB_init(GB_alloc(), model);
    GB_set_boot_rom_load_callback(gb, boot_cb);
    GB_set_pixels_output(gb, pixels);
    GB_set_rgb_encode_callback(gb, rgb);
    GB_set_log_callback(gb, logcb);
    GB_set_vblank_callback(gb, vblank);
    GB_set_rtc_mode(gb, GB_RTC_MODE_ACCURATE);
    GB_set_emulate_joypad_bouncing(gb, false);
    if (GB_load_rom(gb, argv[3])) { fprintf(stderr, "rom load failed\n"); return 3; }
    GB_reset(gb);
    if (getenv("SYMS")) GB_debugger_load_symbol_file(gb, getenv("SYMS"));
    if (getenv("TURBO")) GB_set_turbo_mode(gb, true, false);
    if (getenv("REWIND")) GB_set_rewind_length(gb, atof(getenv("REWIND")));
    setvbuf(stdout, NULL, _IOLBF, 0);

    if (!strcmp(mode, "dbg")) {
        FILE *f = fopen(argv[4], "r"); char buf[1024];
        while (fgets(buf, sizeof buf, f)) { buf[strcspn(buf, "\n")] = 0; lines = realloc(lines, ++nlines * sizeof *lines); lines[nlines - 1] = strdup(buf); }
        GB_set_input_callback(gb, input);
        GB_debugger_break(gb);
        uint64_t total = 0, guard = 0;
        while (!done && guard++ < 50000000) {
            unsigned t = GB_run(gb); total += t;
            if (ticks_left > 0) { ticks_left -= t; if (ticks_left <= 0) { ticks_left = -1; GB_debugger_break(gb); } }
        }
        printf("@@end total_ticks=%llu done=%d\n", (unsigned long long)total, done);
        state_line(gb);
        return 0;
    }
    if (!strcmp(mode, "core2")) return core2(model, argv[3]);
    if (!strcmp(mode, "core")) {
        printf("@@model=%03x cgb=%d sgb=%d state_size=%zu alloc=%zu\n", model, GB_is_cgb(gb), GB_is_sgb(gb), GB_get_save_state_size(gb), GB_allocation_size());
        /* GB_run return-value histogram for first 2000 calls */
        unsigned hist[64] = {0}; uint64_t total = 0;
        for (int i = 0; i < 2000; i++) { unsigned t = GB_run(gb); total += t; hist[t < 63 ? t : 63]++; }
        printf("@@run2000 total=%llu hist=", (unsigned long long)total);
        for (int i = 0; i < 64; i++) if (hist[i]) printf("%d:%u,", i, hist[i]);
        printf("\n");
        GB_set_execution_callback(gb, exec_cb);
        long v0 = vblanks; uint64_t ns = 0, e0 = execs;
        printf("@@run_frame_ns=");
        for (int i = 0; i < 60; i++) { uint64_t x = GB_run_frame(gb); ns += x; if (i < 6) printf("%llu,", (unsigned long long)x); }
        printf("\n");
        printf("@@frames60 vblanks=%ld ns_sum=%llu execs=%llu\n", vblanks - v0, (unsigned long long)ns, (unsigned long long)(execs - e0));
        printf("@@pixels fnv=%08x\n", fnv((uint8_t *)pixels, sizeof pixels));
        state_line(gb);
        uint16_t res, bank; bool err = GB_debugger_evaluate(gb, "[$c000]", &res, &bank);
        printf("@@eval [$c000] ret=%d value=%u bank=%04x\n", err, res, bank);
        err = GB_debugger_evaluate(gb, "nosuchsym", &res, &bank);
        printf("@@eval nosuchsym ret=%d value=%u bank=%04x\n", err, res, bank);
        return 0;
    }
    return 2;
}
