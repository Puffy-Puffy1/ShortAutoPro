import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_script(name, home, short_id="gate_test", extra_env=None):
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    env["SHORT_ID"] = short_id
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(ROOT / name)],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def make_words(count):
    return [f"palavra{i:03d}" for i in range(count)]


class SemanticGateTests(unittest.TestCase):
    def test_lossless_report_is_read_with_short_id_and_allows_verified_overlap(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            base = home / "ShortAutoPro"
            roteiros = base / "roteiros"
            roteiros.mkdir(parents=True)

            words = make_words(105)
            script = " ".join(words)
            (roteiros / "short_gate_test.txt").write_text(script, encoding="utf-8")

            scenes = []
            for i in range(6):
                segment = " ".join(words[i * 18:(i + 1) * 18])
                if i == 0:
                    segment = segment + " " + " ".join(words[:20])
                scenes.append({
                    "scene": i + 1,
                    "segment": segment,
                    "query": f"query scene {i + 1}",
                    "must_have": [f"anchor{i + 1}"],
                })

            (roteiros / "scene_map_gate_test.json").write_text(
                json.dumps({"scenes": scenes}),
                encoding="utf-8",
            )
            (roteiros / "scene_lossless_gate_test.json").write_text(
                json.dumps({
                    "status": "PASS",
                    "coverage_after": 1.0,
                    "missing_after": [],
                    "changed_scenes": [{"source_text": " ".join(words[:20])}],
                }),
                encoding="utf-8",
            )

            proc = run_script(
                "semantic_integrity_gate.py",
                home,
                extra_env={"SHORT_QTD_CENAS": "6"},
            )
            output = proc.stdout + proc.stderr
            self.assertEqual(proc.returncode, 0, output)
            self.assertIn("Lossless overlap verificado: True", output)
            self.assertIn("SEMANTIC INTEGRITY: PASS", output)


class LosslessRepairTests(unittest.TestCase):
    def test_lossless_repair_respects_configured_scene_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            base = home / "ShortAutoPro"
            roteiros = base / "roteiros"
            roteiros.mkdir(parents=True)

            words = make_words(108)
            script = " ".join(words)
            (roteiros / "short_gate_test.txt").write_text(script, encoding="utf-8")

            scenes = []
            for i in range(6):
                scenes.append({
                    "scene": i + 1,
                    "segment": " ".join(words[i * 18:(i + 1) * 18]),
                    "query": f"query {i + 1}",
                    "must_have": [f"anchor{i + 1}"],
                })

            (roteiros / "scene_map_gate_test.json").write_text(
                json.dumps({"scenes": scenes}),
                encoding="utf-8",
            )

            proc = run_script(
                "scene_lossless_repair.py",
                home,
                extra_env={"SHORT_QTD_CENAS": "6"},
            )
            output = proc.stdout + proc.stderr
            self.assertEqual(proc.returncode, 0, output)
            self.assertIn("LOSSLESS REPAIR: NÃO NECESSÁRIO", output)


class FinalQualityGateTests(unittest.TestCase):
    def test_weak_production_returns_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "ShortAutoPro" / "roteiros").mkdir(parents=True)
            proc = run_script("final_quality.py", home)
            output = proc.stdout + proc.stderr
            self.assertNotEqual(proc.returncode, 0, output)
            self.assertIn("FINAL QUALITY SCORE: BLOCK", output)


class RegisterTopicTests(unittest.TestCase):
    def test_missing_topic_file_is_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            (home / "ShortAutoPro" / "roteiros").mkdir(parents=True)
            proc = run_script("register_topic.py", home)
            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_duplicate_topic_does_not_append_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            base = home / "ShortAutoPro"
            roteiros = base / "roteiros"
            roteiros.mkdir(parents=True)
            (roteiros / "used_topic_gate_test.txt").write_text(
                "Caso Elisa Lam",
                encoding="utf-8",
            )
            history = base / "historico_assuntos.json"
            history.write_text(
                json.dumps([{"topic": "Morte de Elisa Lam", "short_id": "old"}]),
                encoding="utf-8",
            )

            proc = run_script("register_topic.py", home)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            data = json.loads(history.read_text(encoding="utf-8"))
            self.assertEqual(len(data), 1)


class UsedTopicTests(unittest.TestCase):
    def test_used_topic_accepts_case_insensitive_header_and_normalizes_spaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            roteiros = home / "ShortAutoPro" / "roteiros"
            roteiros.mkdir(parents=True)
            (roteiros / "fonte_gate_test.txt").write_text(
                "  assunto :   Caso   Dyatlov Pass   \nFONTE: Wikipedia — Dyatlov Pass incident\n",
                encoding="utf-8",
            )

            proc = run_script("used_topic.py", home)
            output = proc.stdout + proc.stderr
            self.assertEqual(proc.returncode, 0, output)
            self.assertEqual(
                (roteiros / "used_topic_gate_test.txt").read_text(encoding="utf-8"),
                "Caso Dyatlov Pass",
            )

    def test_invalid_source_does_not_overwrite_existing_used_topic(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            roteiros = home / "ShortAutoPro" / "roteiros"
            roteiros.mkdir(parents=True)
            target = roteiros / "used_topic_gate_test.txt"
            target.write_text("Tema preservado", encoding="utf-8")
            (roteiros / "fonte_gate_test.txt").write_text(
                "FONTE: Wikipedia — artigo sem assunto\n",
                encoding="utf-8",
            )

            proc = run_script("used_topic.py", home)
            self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertEqual(target.read_text(encoding="utf-8"), "Tema preservado")


if __name__ == "__main__":
    unittest.main()
