"""The HDR layer follows the HDR setting, not each frame (#2419). A frame with no HDR picture (Tears of the Kingdom paused behind
the ability wheel or a quick selector composes none) is drawn into the HDR layer as SDR; switching the CAMetalLayer to SDR and
back for those frames made macOS composite the window again each time, and the screen flashed while L or the D-pad was held.
The HDR copy (fshdr) takes linear input, so only an FP16 picture uses it; an SDR picture into an FP16 drawable goes through fs,
which decodes it."""
import re
import unittest
from pathlib import Path

NVN = Path(__file__).resolve().parents[1] / 'games/totk/third_party/d2r_gfx/gfx/nvn/nvn_mtl.m'


class HdrLayerFollowsSetting(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = NVN.read_text(errors='replace')

    def test_the_layer_mode_is_the_setting(self):
        self.assertNotIn('front_hdr_present_mode(hdrFrame)', self.text)
        self.assertNotIn('want=hdrFrame?', self.text)
        self.assertIn('const BOOL hdrLayer=totk_hdr_active() && !atomic_load(&g_hdr_shader_failed);', self.text)
        self.assertIn('front_hdr_present_mode(hdrLayer)', self.text)

    def test_the_hdr_copy_only_for_an_fp16_picture(self):
        choices = re.findall(r'setRenderPipelineState:g_blit_hdr_pso && ([^?]+)\?', self.text)
        self.assertEqual(len(choices), 2, choices)
        for choice in choices:
            self.assertIn('pixelFormat==MTLPixelFormatRGBA16Float', choice)
            self.assertNotIn('dst.', choice, 'an SDR picture into an FP16 drawable must take fs, not fshdr (#2419)')


if __name__ == '__main__':
    unittest.main()
