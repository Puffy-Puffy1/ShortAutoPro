import ast
import re
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class SceneMapBridgeTests(unittest.TestCase):
    def test_consumers_use_frozen_scene_map(self):
        # The canonical workspace can be named BASE, base, or root depending on
        # whether a module uses the process default or an injected engine root.
        frozen_path = r'(?:BASE|base|root)\s*/\s*"manifests"\s*/\s*f"scene_map_\{(?:sid|short_id|SID)\}\.json"'
        mutable_path = r'(?:BASE|base|root)\s*/\s*"roteiros"\s*/\s*f"scene_map_\{(?:sid|short_id|SID)\}\.json"'
        for name in ("media_acquisition_v3.py","render_plan_v2.py","render_preflight.py","render_engine_v2.py","caption_layout_guard.py","resume_short_runtime.py"):
            text=(ROOT/name).read_text(encoding="utf-8")
            self.assertRegex(text, frozen_path, name)
            self.assertNotRegex(text, mutable_path, name)

    def test_downstream_consumers_do_not_reference_mutable_scene_map(self):
        downstream = (
            "media_acquisition_v3.py",
            "caption_layout_guard.py",
            "render_preflight.py",
            "render_plan_v2.py",
            "render_engine_v2.py",
        )
        forbidden = r'(?:BASE|base|root)\s*/\s*"roteiros"\s*/\s*f"scene_map_\{(?:sid|short_id|SID)\}\.json"'
        for name in downstream:
            source = (ROOT/name).read_text(encoding="utf-8")
            self.assertNotRegex(source, forbidden, name)

    def test_media_manifest_has_single_canonical_writer(self):
        source = (ROOT/"media_acquisition_v3.py").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r'(?:BASE|base)\s*/\s*"manifests"\s*/\s*f"media_\{sid\}\.json"', source)), 1)
        self.assertRegex(source, r'"immutable"\s*:\s*True')
        self.assertIn('"integrity_sha256"', source)

    def test_render_plan_is_single_frozen_writer(self):
        source=(ROOT/"render_plan_v2.py").read_text(encoding="utf-8")
        self.assertEqual(len(re.findall(r'BASE\s*/\s*"roteiros"\s*/\s*f"pro_edit_plan_\{sid\}\.json"', source)), 1)
        self.assertRegex(source, r'"immutable"\s*:\s*True')
        self.assertIn('"integrity_sha256"',source)
        self.assertIn('media_manifest_missing',source)

    def test_render_preflight_uses_media_manifest_as_canonical_source(self):
        source=(ROOT/"render_preflight.py").read_text(encoding="utf-8")
        self.assertIn('BASE / "manifests" / f"media_{short_id}.json"',source)
        self.assertIn('schema_version") != "media-manifest-v2"',source)
        self.assertIn('asset.get("validated") is not True',source)
        self.assertNotIn('for path in sorted(media_dir.glob("scene_*"))',source)

    def test_render_engine_is_acquisition_free_and_freezes_render_plan(self):
        source=(ROOT/"render_engine_v2.py").read_text(encoding="utf-8")
        self.assertIn('plan.get("schema_version") != "render-plan-v2"',source)
        self.assertIn('plan.get("immutable") is not True',source)
        self.assertIn('render_plan_integrity',source)
        self.assertNotIn("ProviderRegistry",source)
        self.assertNotIn("media_acquisition_v3",source)
        self.assertNotIn("PexelsAdapter",source)

    def test_first_video_has_real_output_qa(self):
        source=(ROOT/"first_video.py").read_text(encoding="utf-8")
        for token in ("ffprobe", "technical_qa", "resolution", "video_codec", "audio_codec"):
            self.assertIn(token,source)

    def test_render_engine_requires_frozen_scene_contract(self):
        text=(ROOT/"render_engine_v2.py").read_text(encoding="utf-8")
        self.assertIn("SCENE_MAP_FROZEN_1.0", text)
        self.assertIn("mutable_upstream_closed", text)

    def test_resume_freezes_before_media(self):
        text=(ROOT/"resume_short_runtime.py").read_text(encoding="utf-8")
        self.assertLess(text.index("FREEZE SCENE MAP BRIDGE"), text.index("MEDIA ACQUISITION V3 - ACQUIRE + VALIDATE + FREEZE MANIFEST"))

    def test_main_freezes_before_media_and_builds_plan_after_captions(self):
        text=(ROOT/"main.py").read_text(encoding="utf-8")
        marks=[
            "5F - FREEZE SCENE MAP BRIDGE",
            "MEDIA ACQUISITION V3 - ACQUIRE + VALIDATE + FREEZE MANIFEST",
            "7 - VOZ PIPER",
            "8A1 - CAPTION SAFE-ZONE GUARD",
            "8B1 - RENDER PLAN V2 - DETERMINISTIC TIMELINE INPUT",
        ]
        positions=[text.index(mark) for mark in marks]
        self.assertEqual(positions,sorted(positions))

    def test_first_video_freezes_before_media(self):
        tree=ast.parse((ROOT/"first_video.py").read_text(encoding="utf-8"))
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="main")
        labels=[]
        for node in ast.walk(fn):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Name) and node.func.id=="run_stage":
                if len(node.args)>=3 and isinstance(node.args[2],ast.Constant):
                    labels.append(str(node.args[2].value))
        self.assertLess(labels.index("SCENE_FREEZE"),labels.index("MEDIA"))

if __name__=="__main__": unittest.main()
