#!/usr/bin/env python3
"""Check the wake erase uses one black/white cycle and hold, and propagates faults."""
from pathlib import Path
import subprocess
import tempfile
source = (Path(__file__).resolve().parents[2] / "src/render.c").read_text()
start = source.index("enum EpdDrawError epd_clear_once_checked(")
end = source.index("void epd_renderer_init(", start)
code = r"""
#include <cassert>
enum EpdDrawError { EPD_DRAW_SUCCESS, FAILED };
struct { EpdDrawError error; } render_context;
static int calls, failAt, blacks, whites, holds;
static constexpr int clear_cycle_time=10;
using EpdRect = int;
void epd_clear_area_cycles(EpdRect, int, int);
static int epd_full_screen() { return 0; }
static void epd_push_pixels(int, int time, int color) {
    assert(time==clear_cycle_time);
    assert(color>=0 && color<=2);
    if (color==0) { assert(whites==0 && holds==0); blacks++; }
    else if (color==1) { assert(blacks==10 && holds==0); whites++; }
    else { assert(blacks==10 && whites==10); holds++; }
    if (++calls==failAt) render_context.error=FAILED;
}
""" + source[start:end] + r"""
int main() {
    assert(epd_clear_once_checked()==EPD_DRAW_SUCCESS);
    assert(blacks==10 && whites==10 && holds==3);
    for (int fault=1; fault<=23; fault++) {
        calls=blacks=whites=holds=0; failAt=fault;
        assert(epd_clear_once_checked()==FAILED);
        assert(calls==fault);
    }
}
"""
with tempfile.TemporaryDirectory() as tmp:
    cpp=Path(tmp)/"test.cpp"
    cpp.write_text(code)
    binary=Path(tmp)/"test"
    subprocess.run(["c++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "-fsanitize=address,undefined", str(cpp), "-o", str(binary)], check=True)
    subprocess.run([str(binary)], check=True)
print("Single erase: black/white/hold sequence and every scan failure passed")
