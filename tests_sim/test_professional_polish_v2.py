import unittest
from pathlib import Path

import midia_runtime as mr
import professional_caption_director as pcd
import professional_pipeline_runtime as ppr


ROOT = Path(__file__).resolve().parents[1]


class ProfessionalCaptionDirectorTests(unittest.TestCase):
    def sample_ass(self):
        return """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Dynamic,DejaVu Sans,66,&H00FFFFFF,&H00D9E7FF,&H00000000,&H90000000,-1,0,0,0,100,100,0,0,1,4,0,2,110,110,285,1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
Dialogue: 0,0:00:00.00,0:00:00.80,Dynamic,,0,0,0,,Uma {\\c&H00D9E7FF&\\b1}investigação{\\c&HFFFFFF&\\b1} extraordinariamente complexa começou
Dialogue: 0,0:00:00.80,0:00:01.60,Dynamic,,0,0,0,,O caso mudou completamente
"""

    def test_transform_preserves_visible_words_and_caps_lines(self):
        source = self.sample_ass()
        before = [
            pcd.visible_text(line.split(",", 9)[9])
            for line in source.splitlines()
            if line.startswith("Dialogue:")
        ]
        transformed, report = pcd.transform(source, "true_crime")
        after = [
            pcd.visible_text(line.split(",", 9)[9])
            for line in transformed.splitlines()
            if line.startswith("Dialogue:")
        ]
        self.assertEqual(before, after)
        self.assertTrue(report["content_preserved"])
        self.assertLessEqual(report["max_lines"], 2)
        self.assertGreaterEqual(report["balanced_breaks_added"], 1)
        self.assertIn("Style: Dynamic,DejaVu Sans,62,", transformed)
        self.assertIn(",125,125,305,1", transformed)

    def test_transform_is_profile_specific_without_rewriting_text(self):
        source = self.sample_ass()
        transformed, report = pcd.transform(source, "cinepulsar")
        self.assertEqual(report["profile"], "cinepulsar")
        self.assertIn("Style: Dynamic,DejaVu Sans,64,", transformed)
        self.assertIn("O caso mudou completamente", transformed)


class ProfessionalMediaFloorTests(unittest.TestCase):
    def synthetic_selector(self):
        return '''\ndef baixar_candidato_5_2(\n    candidato,\n    numero,\n    rotulo\n):\n    destino = "scene.jpg"\n    ok = baixar(\n        candidato.get(\n            "url",\n            ""\n        ),\n        destino\n    )\n    return ok, destino\n'''

    def test_professional_floor_is_candidate_aware_and_failover_friendly(self):
        patched, applied = mr.harden_professional_media_floor(self.synthetic_selector())
        self.assertTrue(applied)
        self.assertIn("SAP_PRO_MEDIA_MIN_PIXELS", patched)
        self.assertIn("1280 * 720", patched)
        self.assertIn('evidence_class == "CASE_DIRECT"', patched)
        self.assertIn("PRO_MEDIA_FLOOR=REJECT", patched)
        self.assertIn("os.remove(destino)", patched)
        self.assertIn("ok = _sap_professional_media_accept_v1", patched)
        compile(patched, "synthetic_midia.py", "exec")

    def test_professional_floor_is_idempotent(self):
        patched, applied = mr.harden_professional_media_floor(self.synthetic_selector())
        self.assertTrue(applied)
        same, applied_again = mr.harden_professional_media_floor(patched)
        self.assertFalse(applied_again)
        self.assertEqual(same, patched)

    def test_current_selector_accepts_all_runtime_hardenings_and_compiles(self):
        source = (ROOT / "midia.py").read_text(encoding="utf-8")
        fixed, _ = mr.fix_source(source)
        fixed, _ = mr.harden_cleanup(fixed)
        fixed, _ = mr.harden_download_resolution(fixed)
        fixed, _ = mr.harden_professional_media_floor(fixed)
        self.assertIn("_sap_professional_media_accept_v1", fixed)
        compile(fixed, "midia.py", "exec")


class ProfessionalPipelinePolishTests(unittest.TestCase):
    def test_professional_runtime_inserts_caption_director(self):
        source = (ROOT / "gerar_short.sh").read_text(encoding="utf-8")
        patched = ppr.build(source)
        self.assertIn("professional_caption_director.py", patched)
        self.assertLess(
            patched.index("professional_caption_director.py"),
            patched.index("caption-audit"),
        )
        self.assertIn("SAP_PRO_MEDIA_MIN_PIXELS", patched)

    def test_professional_quality_scores_media_and_captions(self):
        text = (ROOT / "professional_quality_gate.py").read_text(encoding="utf-8")
        self.assertIn('"media":', text)
        self.assertIn('"captions":', text)
        self.assertIn("pro_caption_", text)
        self.assertIn("media_quality_", text)

    def test_professional_resume_keeps_caption_director(self):
        text = (ROOT / "resume_short_professional_runtime.py").read_text(encoding="utf-8")
        self.assertIn("professional_caption_director.py", text)


if __name__ == "__main__":
    unittest.main()
