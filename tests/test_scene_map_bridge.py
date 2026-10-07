import ast
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class SceneMapBridgeTests(unittest.TestCase):
    def test_consumers_use_frozen_scene_map(self):
        for name in ("media_acquisition_v3.py","render_plan_v2.py"):
            text=(ROOT/name).read_text(encoding="utf-8")
            self.assertIn('BASE/"manifests"/f"scene_map_{sid}.json"',text,name)
            self.assertNotIn('BASE/"roteiros"/f"scene_map_{sid}.json"',text,name)

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

if __name__=="__main__":
    unittest.main()
