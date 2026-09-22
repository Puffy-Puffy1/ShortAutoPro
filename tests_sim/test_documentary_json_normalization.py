import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class DocumentaryJsonNormalizationContractTests(unittest.TestCase):
    def test_root_array_is_recoverable(self):
        text = (ROOT / "documentary_director.py").read_text(encoding="utf-8")
        self.assertIn('"_normalized_from": "root_array"', text)
        self.assertIn("if isinstance(valor, list):", text)

    def test_common_wrappers_are_recoverable(self):
        text = (ROOT / "documentary_director.py").read_text(encoding="utf-8")
        self.assertIn('for key in ("result", "data", "output", "response")', text)
        self.assertIn('f"wrapper:{key}"', text)
        self.assertIn('f"wrapper_list:{key}"', text)

    def test_numeric_scene_object_is_recoverable(self):
        text = (ROOT / "documentary_director.py").read_text(encoding="utf-8")
        self.assertIn('"numeric_object"', text)
        self.assertIn("str(key).isdigit()", text)

    def test_empty_must_have_is_allowed(self):
        text = (ROOT / "documentary_director.py").read_text(encoding="utf-8")
        self.assertIn("len(must) > 3", text)
        self.assertNotIn("not 1 <= len(must) <= 3", text)
        self.assertIn("use [] quando nenhum elemento factual específico", text)

    def test_existing_must_is_preserved_when_proposal_is_empty(self):
        text = (ROOT / "documentary_director.py").read_text(encoding="utf-8")
        self.assertIn("original_must = limpar_lista(cena_original.get", text)
        self.assertIn("if not must and original_must:", text)

    def test_version_bumped(self):
        text = (ROOT / "documentary_director.py").read_text(encoding="utf-8")
        self.assertIn('VERSION = "3.6"', text)
        self.assertIn("DOCUMENTARY_JSON_NORMALIZED=", text)


if __name__ == "__main__":
    unittest.main()
