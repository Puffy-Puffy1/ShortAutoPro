import unittest
from pathlib import Path

import professional_caption_director as pcd


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
        before = [pcd.visible_text(line.split(",", 9)[9]) for line in source.splitlines() if line.startswith("Dialogue:")]
        transformed, report = pcd.transform(source, "true_crime")
        after = [pcd.visible_text(line.split(",", 9)[9]) for line in transformed.splitlines() if line.startswith("Dialogue:")]
        self.assertEqual(before, after)
        self.assertTrue(report["content_preserved"])
        self.assertLessEqual(report["max_lines"], 2)
        self.assertGreaterEqual(report["balanced_breaks_added"], 1)
        self.assertIn("Style: Dynamic,DejaVu Sans,69,", transformed)
        self.assertIn(",125,125,335,1", transformed)

    def test_transform_is_profile_specific_without_rewriting_text(self):
        source = self.sample_ass()
        transformed, report = pcd.transform(source, "cinepulsar")
        self.assertEqual(report["profile"], "cinepulsar")
        self.assertIn("Style: Dynamic,DejaVu Sans,70,", transformed)
        self.assertIn("O caso mudou completamente", transformed)


class ProfessionalMediaFloorTests(unittest.TestCase):
    def test_professional_floor_is_integrated_in_selector(self):
        source = (ROOT / "midia.py").read_text(encoding="utf-8")
        self.assertIn("def _sap_professional_media_accept_v1", source)
        self.assertIn("SAP_PRO_MEDIA_MIN_PIXELS", source)
        self.assertIn("1280 * 720", source)
        self.assertIn('evidence_class == "CASE_DIRECT"', source)
        self.assertIn("PRO_MEDIA_FLOOR=REJECT", source)
        self.assertIn("os.remove(destino)", source)
        self.assertIn("ok = _sap_professional_media_accept_v1", source)
        compile(source, "midia.py", "exec")

    def test_professional_floor_remains_failover_friendly(self):
        source = (ROOT / "midia.py").read_text(encoding="utf-8")
        helper = source[source.index("def _sap_professional_media_accept_v1"):source.index("def baixar_candidato_5_2")]
        self.assertIn("return False", helper)
        self.assertIn("return True", helper)


class ProfessionalPipelinePolishTests(unittest.TestCase):
    def test_canonical_pipeline_places_caption_director_before_audit(self):
        text = (ROOT / "main.py").read_text(encoding="utf-8")
        self.assertIn("professional_caption_director.py", text)
        self.assertLess(text.index("professional_caption_director.py"), text.index('"caption-audit"'))
        self.assertIn("SAP_PRO_MEDIA_MIN_PIXELS", text)
        self.assertIn("media_acquisition_v3.py", text)
        self.assertIn("render_plan_v2.py", text)
        self.assertNotIn("media_stage_runtime.py", text)
        self.assertNotIn("gerar_short.sh", text)

    def test_professional_quality_scores_media_and_captions(self):
        text = (ROOT / "professional_quality_gate.py").read_text(encoding="utf-8")
        self.assertIn('"media":', text)
        self.assertIn('"captions":', text)
        self.assertIn("pro_caption_", text)
        self.assertIn("media_quality_", text)

    def test_unified_resume_keeps_caption_director(self):
        text = (ROOT / "resume_short_runtime.py").read_text(encoding="utf-8")
        self.assertIn("professional_caption_director.py", text)
        self.assertIn("PROFESSIONAL_CANONICAL", text)
        self.assertIn("import main as canonical", text)
        self.assertNotIn("SAP_PRO_EDIT", text)


if __name__ == "__main__":
    unittest.main()
