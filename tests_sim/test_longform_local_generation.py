import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import longform_runtime as longform


class LongFormLocalGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.worker = self.root / "generative_video_poc" / "brain.py"
        self.worker.parent.mkdir(parents=True)
        self.worker.write_text("# shared worker entrypoint fixture\n", encoding="utf-8")
        self.backend = self.root / "backend.json"
        self.backend.write_text('{"executable":"/local/generator"}\n', encoding="utf-8")
        self.run_dir = self.root / "runs" / "longform-test"
        self.run_dir.mkdir(parents=True)
        self.outline = [
            {"chapter": 1, "title": "A origem", "objective": "Apresentar o contexto histórico"},
            {"chapter": 2, "title": "As consequências", "objective": "Explicar os efeitos documentados"},
        ]

    def tearDown(self):
        self.temp.cleanup()

    def _worker_responses(self, status="PROJECT_COMPLETE", returncode=0):
        manifest_path = self.root / "projects" / "project" / "generated_manifest.json"
        complete_payload = {
            "status": status,
            "manifest": {"manifest_path": str(manifest_path)},
        }
        return [
            subprocess.CompletedProcess(["create"], 0, stdout='{"status":"CREATED"}', stderr=""),
            subprocess.CompletedProcess(
                ["work"], returncode,
                stdout=json.dumps(complete_payload),
                stderr="worker failure" if returncode else "",
            ),
        ]

    def test_builds_one_documentary_prompt_per_clip(self):
        prompts = longform._build_local_longform_prompts(
            "História documentada", self.outline, 300, clip_seconds=10,
        )
        self.assertEqual(len(prompts), 30)
        self.assertTrue(any("A origem" in prompt for prompt in prompts))
        self.assertTrue(any("As consequências" in prompt for prompt in prompts))
        self.assertGreater(len({prompt.split("Camera direction: ", 1)[1] for prompt in prompts}), 1)
        self.assertTrue(all("No captions" in prompt for prompt in prompts))

    def test_runs_the_shared_queue_and_pins_manifest_and_backend(self):
        state = {}
        verified = {
            "project": {"target_duration_seconds": 300},
            "integrity_sha256": "manifest-sha",
            "project_id": "long_longform_test_abcdef123456",
        }
        with mock.patch.object(longform, "BASE", self.root), \
             mock.patch.object(longform, "verify_generated_manifest", return_value=verified) as verify, \
             mock.patch.object(longform.subprocess, "run", side_effect=self._worker_responses()) as runner:
            result = longform._generate_local_longform_manifest(
                "longform-test", "História documentada", 5, self.outline,
                self.backend, state, self.run_dir,
            )

        self.assertEqual(result, verified)
        self.assertEqual(runner.call_count, 2)
        create_args = runner.call_args_list[0].args[0]
        work_args = runner.call_args_list[1].args[0]
        self.assertIn("generative_video_poc.brain", create_args)
        self.assertIn("create", create_args)
        self.assertIn("work", work_args)
        self.assertIn("--drain", work_args)
        self.assertEqual(state["generated_manifest_integrity"], "manifest-sha")
        self.assertEqual(state["local_ai_backend_config_sha256"], longform._file_sha256(self.backend))
        self.assertEqual(state["generated_media_source"], "shared_local_queue")
        self.assertTrue((self.run_dir / "generated_media_spec.json").is_file())
        spec = json.loads((self.run_dir / "generated_media_spec.json").read_text(encoding="utf-8"))
        self.assertEqual(spec["kind"], "longform")
        self.assertEqual(spec["aspect_ratio"], "16:9")
        self.assertEqual(spec["target_duration_seconds"], 300)
        self.assertEqual(len(spec["clip_prompts"]), 30)
        verify.assert_called_once_with(str(self.root / "projects" / "project" / "generated_manifest.json"))

    def test_project_identity_is_deterministic_for_resume(self):
        state_a = {}
        state_b = {}
        verified = {
            "project": {"target_duration_seconds": 300},
            "integrity_sha256": "manifest-sha",
            "project_id": "fixture",
        }
        with mock.patch.object(longform, "BASE", self.root), \
             mock.patch.object(longform, "verify_generated_manifest", return_value=verified), \
             mock.patch.object(longform.subprocess, "run", side_effect=self._worker_responses() * 2) as runner:
            longform._generate_local_longform_manifest(
                "longform-test", "História documentada", 5, self.outline,
                self.backend, state_a, self.run_dir,
            )
            longform._generate_local_longform_manifest(
                "longform-test", "História documentada", 5, self.outline,
                self.backend, state_b, self.run_dir,
            )
        first_create = runner.call_args_list[0].args[0]
        second_create = runner.call_args_list[2].args[0]
        self.assertEqual(first_create[first_create.index("create") + 1], second_create[second_create.index("create") + 1])
        self.assertEqual(state_a["local_ai_project_id"], state_b["local_ai_project_id"])

    def test_changed_backend_config_is_rejected_before_worker_starts(self):
        state = {"local_ai_backend_config_sha256": "not-the-current-hash"}
        with mock.patch.object(longform, "BASE", self.root), \
             mock.patch.object(longform.subprocess, "run") as runner:
            with self.assertRaisesRegex(RuntimeError, "BACKEND_CONFIG_CHANGED"):
                longform._generate_local_longform_manifest(
                    "longform-test", "História documentada", 5, self.outline,
                    self.backend, state, self.run_dir,
                )
        runner.assert_not_called()

    def test_incomplete_local_queue_fails_closed_without_manifest(self):
        state = {}
        responses = self._worker_responses(status="PROJECT_INCOMPLETE", returncode=0)
        verified = {"project": {"target_duration_seconds": 300}, "integrity_sha256": "unused"}
        with mock.patch.object(longform, "BASE", self.root), \
             mock.patch.object(longform, "verify_generated_manifest", return_value=verified) as verify, \
             mock.patch.object(longform.subprocess, "run", side_effect=responses):
            with self.assertRaisesRegex(RuntimeError, "GENERATION_INCOMPLETE"):
                longform._generate_local_longform_manifest(
                    "longform-test", "História documentada", 5, self.outline,
                    self.backend, state, self.run_dir,
                )
        self.assertNotIn("generated_manifest", state)
        verify.assert_not_called()

    def test_longform_cli_forwards_local_backend_config(self):
        config = "/tmp/local_video_backend.json"
        with mock.patch.object(longform, "execute") as execute, \
             mock.patch("sys.argv", [
                 "longform_runtime.py", "run", "--topic", "Tema",
                 "--local-ai-backend-config", config,
             ]):
            result = longform.main()
        self.assertEqual(result, 0)
        self.assertEqual(execute.call_args.kwargs["local_ai_backend_config"], config)

    def test_execute_rejects_two_media_sources(self):
        with self.assertRaisesRegex(ValueError, "não ambos"):
            longform.execute(
                "Tema", 5, 3, "default",
                generated_manifest="/tmp/manifest.json",
                local_ai_backend_config="/tmp/backend.json",
            )


if __name__ == "__main__":
    unittest.main()
