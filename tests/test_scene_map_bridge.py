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
        tree=ast.parse((ROOT/"main.py").read_text(encoding="utf-8"))
        fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="stages_before_render")
        calls=[]
        for node in ast.walk(fn):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=="run":
                if len(node.args)>=2 and isinstance(node.args[0],ast.Constant) and isinstance(node.args[1],ast.Constant):
                    calls.append((str(node.args[0].value),str(node.args[1].value)))
        idx={name:i for i,(name,_) in enumerate(calls)}
        self.assertLess(idx["5F - FREEZE SCENE MAP BRIDGE"],idx["MEDIA ACQUISITION V3 - ACQUIRE + VALIDATE + FREEZE MANIFEST"])
        self.assertLess(idx["MEDIA ACQUISITION V3 - ACQUIRE + VALIDATE + FREEZE MANIFEST"],idx["7 - VOZ PIPER"])
        self.assertLess(idx["8A1 - CAPTION SAFE-ZONE GUARD"],idx["8B1 - RENDER PLAN V2 - DETERMINISTIC TIMELINE INPUT"])

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
