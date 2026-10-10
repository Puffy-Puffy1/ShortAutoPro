import ast
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "first_video.py"


class FirstVideoContractTests(unittest.TestCase):
    def test_first_video_uses_canonical_artifact_paths(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn('BASE/"manifests"/f"media_{sid}.json"', text)
        self.assertIn('BASE/"roteiros"/f"pro_edit_plan_{sid}.json"', text)
        self.assertNotIn('BASE/"roteiros"/f"media_manifest_{sid}.json"', text)
        self.assertNotIn('BASE/"roteiros"/f"render_plan_{sid}.json"', text)

    def test_render_plan_is_after_audio_and_captions(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        main = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main")
        calls = []
        for node in ast.walk(main):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "run_stage":
                if len(node.args) >= 3 and isinstance(node.args[2], ast.Constant):
                    calls.append(str(node.args[2].value))
        self.assertLess(calls.index("AUDIO"), calls.index("RENDER_PLAN"))
        self.assertLess(calls.index("CAPTION_GUARD"), calls.index("RENDER_PLAN"))
        self.assertLess(calls.index("RENDER_PLAN"), calls.index("RENDER_PREFLIGHT"))
        self.assertLess(calls.index("RENDER_PREFLIGHT"), calls.index("RENDER"))

    def test_manifest_writer_uses_real_newline_not_literal_backslash_n(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        writer = next(
            n for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name == "write_manifest"
        )
        write_call = next(
            n for n in ast.walk(writer)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "write_text"
        )
        serialized = write_call.args[0]
        self.assertIsInstance(serialized, ast.BinOp)
        self.assertIsInstance(serialized.op, ast.Add)
        self.assertIsInstance(serialized.right, ast.Constant)
        self.assertEqual(serialized.right.value, "\n")


if __name__ == "__main__":
    unittest.main()
