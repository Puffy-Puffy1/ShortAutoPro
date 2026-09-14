import json
import tempfile
import unittest
from pathlib import Path

from hook_runtime import derive_fallback_hook, ensure_hook_artifact


class HookRuntimeTests(unittest.TestCase):
    def test_fallback_uses_only_script_prefix_words(self):
        script = (
            "Um avião desapareceu durante um voo noturno e a busca começou poucas horas depois. "
            "As equipes analisaram os últimos registros disponíveis."
        )
        hook = derive_fallback_hook(script)
        self.assertTrue(hook)
        self.assertTrue(script.startswith(hook))
        self.assertLessEqual(len(hook.split()), 18)

    def test_missing_hook_is_created_atomically_from_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            roteiros = base / "roteiros"
            roteiros.mkdir()
            short_id = "test123"
            script = "Uma investigação começou após o desaparecimento e novas pistas surgiram nos dias seguintes."
            (roteiros / f"short_{short_id}.txt").write_text(script, encoding="utf-8")

            hook = ensure_hook_artifact(base, short_id, "unit_test")
            self.assertTrue(hook)
            self.assertEqual(
                (roteiros / f"hook_{short_id}.txt").read_text(encoding="utf-8"),
                hook,
            )
            payload = json.loads(
                (roteiros / f"hook_{short_id}.json").read_text(encoding="utf-8")
            )
            self.assertTrue(payload["runtime_fallback"])
            self.assertEqual(payload["reason"], "unit_test")
            self.assertEqual(payload["hooks"][0]["text"], hook)

    def test_existing_hook_is_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            roteiros = base / "roteiros"
            roteiros.mkdir()
            short_id = "keep"
            (roteiros / f"short_{short_id}.txt").write_text(
                "Este roteiro possui conteúdo suficiente para o teste do runtime.",
                encoding="utf-8",
            )
            hook_path = roteiros / f"hook_{short_id}.txt"
            hook_path.write_text("Gancho já aprovado.", encoding="utf-8")

            hook = ensure_hook_artifact(base, short_id, "should_not_replace")
            self.assertEqual(hook, "Gancho já aprovado.")
            self.assertEqual(hook_path.read_text(encoding="utf-8"), "Gancho já aprovado.")


if __name__ == "__main__":
    unittest.main()
