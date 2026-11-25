import tempfile
import unittest
from pathlib import Path
from generative_video_poc.local_video_backend import LocalVideoBackend, LocalGenerationError, validate_template


VALID_PROBE = """#!/usr/bin/env python3
import json
print(json.dumps({"streams":[{"codec_type":"video","codec_name":"h264","width":360,"height":640}],"format":{"duration":"1.0"}}))
"""


class LocalBackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.generator = self.root / "fake-generator"
        self.generator.write_text(
            "#!/usr/bin/env python3\nimport pathlib,sys\npathlib.Path(sys.argv[1]).write_bytes(b'fake video bytes')\n",
            encoding="utf-8",
        )
        self.generator.chmod(0o755)
        self.ffprobe = self.root / "fake-ffprobe"
        self.ffprobe.write_text(VALID_PROBE, encoding="utf-8")
        self.ffprobe.chmod(0o755)

    def tearDown(self):
        self.temp.cleanup()

    def backend(self, **kwargs):
        return LocalVideoBackend(str(self.generator), ["{output}"], ffprobe=str(self.ffprobe), **kwargs)

    def generate(self, backend, output):
        return backend.generate_clip(prompt="A fox runs", output=output, width=360, height=640,
                                      frames=25, seed=7, model="test-model")

    def test_generates_and_probes_video_without_shell(self):
        out = self.root / "sample.mp4"
        result = self.generate(self.backend(), out)
        self.assertEqual(result["status"], "GENERATED_AND_PROBED")
        self.assertEqual(result["generation_host"], "termux_local")
        self.assertEqual(out.read_bytes(), b"fake video bytes")
        self.assertTrue(Path(result["log_path"]).is_file())

    def test_requires_executable_generator_and_ffprobe(self):
        non_executable = self.root / "not-executable"
        non_executable.write_text("not executable", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "not executable"):
            LocalVideoBackend(str(non_executable), ["{output}"], ffprobe=str(self.ffprobe))

        non_executable_probe = self.root / "not-executable-ffprobe"
        non_executable_probe.write_text("not executable", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "executable ffprobe"):
            LocalVideoBackend(str(self.generator), ["{output}"], ffprobe=str(non_executable_probe))

    def test_refuses_existing_output(self):
        out = self.root / "sample.mp4"
        out.write_bytes(b"already here")
        with self.assertRaisesRegex(LocalGenerationError, "overwrite"):
            self.generate(self.backend(), out)

    def test_rejects_unknown_template_placeholder(self):
        self.assertEqual(validate_template(["--prompt", "{prompt}"]), ["--prompt", "{prompt}"])
        with self.assertRaisesRegex(ValueError, "unsupported command placeholder"):
            validate_template(["{shell}"])

    def test_process_failure_keeps_small_log_for_diagnosis(self):
        failed = self.root / "failed-generator"
        failed.write_text("#!/usr/bin/env python3\nimport sys\nprint('synthetic failure')\nsys.exit(17)\n", encoding="utf-8")
        failed.chmod(0o755)
        backend = LocalVideoBackend(str(failed), ["{output}"], ffprobe=str(self.ffprobe))
        with self.assertRaisesRegex(LocalGenerationError, "code 17"):
            self.generate(backend, self.root / "failed.mp4")
        self.assertTrue((self.root / "failed.mp4.generation.log").is_file())

    def test_invalid_probe_removes_bad_clip(self):
        self.ffprobe.write_text(
            "#!/usr/bin/env python3\nprint('{\\\"streams\\\":[],\\\"format\\\":{\\\"duration\\\":\\\"0\\\"}}')\n",
            encoding="utf-8",
        )
        self.ffprobe.chmod(0o755)
        out = self.root / "bad.mp4"
        with self.assertRaisesRegex(LocalGenerationError, "not a valid video"):
            self.generate(self.backend(), out)
        self.assertFalse(out.exists())

    def test_timeout_is_bounded_and_reported(self):
        slow = self.root / "slow-generator"
        slow.write_text("#!/usr/bin/env python3\nimport time\ntime.sleep(5)\n", encoding="utf-8")
        slow.chmod(0o755)
        backend = LocalVideoBackend(str(slow), ["{output}"], ffprobe=str(self.ffprobe), timeout_seconds=1)
        with self.assertRaisesRegex(LocalGenerationError, "timed out"):
            self.generate(backend, self.root / "timeout.mp4")


if __name__ == "__main__":
    unittest.main()
