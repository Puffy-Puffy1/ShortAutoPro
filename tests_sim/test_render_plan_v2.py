import json
import tempfile
import unittest
from pathlib import Path
from render_plan_v2 import main

class RenderPlanV2Tests(unittest.TestCase):
    def test_plan_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            base=Path(td)
            sid="PLAN_TEST"
            (base/"roteiros").mkdir()
            (base/"roteiros"/f"scene_map_{sid}.json").write_text(json.dumps({"scenes":[{"scene_id":"01"},{"scene_id":"02"}]}))
            import render_plan_v2
            render_plan_v2.BASE=base
            self.assertEqual(main(sid),0)
            first=(base/"roteiros"/f"pro_edit_plan_{sid}.json").read_text()
            self.assertEqual(main(),0)
            second=(base/"roteiros"/f"pro_edit_plan_{sid}.json").read_text()
            self.assertEqual(first,second)
