"""The HID stick fallback (shared/runtime/switch_left_fallback.h, used when GameController leaves a Switch pad's sticks at zero)
is scaled by the stick's reach, as the HID path scales a Switch Pro Controller's (gamepad_hid_reach). #2417: a Pro Controller's
sticks stop at about 338..3621 of the 12-bit range, so the fallback alone gave 64-79 % of a full push and Link walked where he
should run. Measured on the reporter's log; the numbers below are its ranges."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHARED = ROOT / 'shared/runtime'

PROBE = r'''
#include <stdio.h>
#include <math.h>
#include <stdint.h>
#include "switch_left_fallback.h"
#include "gamepad_layout.h"
int main(void) {
    GamepadHidReach r[2] = {{0, 0}, {0, 0}};
    /* the reporter's right-up extreme and left-down extreme (HID LX 452..3531, LY 436..3621) */
    float up = switch_left_axis(3621), down = switch_left_axis(436), right = switch_left_axis(3531), left = switch_left_axis(452);
    printf("raw %.3f %.3f %.3f %.3f\n", up, down, right, left);
    float fy_up = gamepad_hid_reach(&r[1], up), fy_down = gamepad_hid_reach(&r[1], down);
    float fx_right = gamepad_hid_reach(&r[0], right), fx_left = gamepad_hid_reach(&r[0], left);
    float half = gamepad_hid_reach(&r[1], up / 2);
    printf("full %.3f %.3f %.3f %.3f half %.3f\n", fy_up, fy_down, fx_right, fx_left, half);
    int ok = fy_up > 0.999f && fy_down < -0.999f && fx_right > 0.999f && fx_left < -0.999f && fabsf(half - 0.5f / 0.85f) < 0.01f;
    puts(ok ? "PASS" : "FAIL");
    return !ok;
}
'''


@unittest.skipUnless(shutil.which('xcrun'), 'needs Apple command line tools')
class SwitchFallbackReach(unittest.TestCase):
    def test_a_full_push_reads_full(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, exe = Path(tmp) / 'probe.c', Path(tmp) / 'probe'
            src.write_text(PROBE)
            build = subprocess.run(['xcrun', 'clang', '-std=c11', '-Wall', '-Wextra', '-Werror', f'-I{SHARED}', str(src), '-o', str(exe)],
                                   capture_output=True, text=True)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertIn('PASS', run.stdout, run.stdout)

    def test_every_game_s_fallback_goes_through_the_reach(self):
        """Every game's gamepad.m with the fallback scales what it reads, and resets the reach with the fallback (2026-11-28:
        the fix went to all eleven copies; a game that copies an older gamepad.m fails here)."""
        found = 0
        for pad in sorted(ROOT.glob('games/*/runtime/gamepad.m')) + [SHARED / 'gamepad.m']:
            if pad.is_symlink():
                continue
            text = pad.read_text()
            core = pad.with_name('gamepad_core.h')
            resets = text + (core.read_text() if core.exists() else '')
            for side, slot in (('rawLeft', 'rawLeftReach'), ('rawRight', 'rawRightReach')):
                if f'switch_left_get(&{side},' not in text:
                    continue
                found += 1
                where = pad.relative_to(ROOT)
                self.assertIn(f'gamepad_hid_reach(&{slot}[0],', text, f'{where}: the {side} fallback is not scaled by its reach (#2417)')
                self.assertIn(f'gamepad_hid_reach(&{slot}[1],', text, f'{where}: the {side} fallback is not scaled by its reach (#2417)')
                self.assertIn(f'memset({slot}, 0, sizeof {slot})', resets, f'{where}: {slot} is not reset with the fallback')
        self.assertGreaterEqual(found, 21, 'the shared copy and ten games, both sticks (mvdk only the left)')

if __name__ == '__main__':
    unittest.main()
