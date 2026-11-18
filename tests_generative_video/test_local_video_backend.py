import tempfile
import unittest
from pathlib import Path
from generative_video_poc.local_video_backend import LocalVideoBackend, LocalGenerationError, validate_template

class LocalBackendTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        self.generator = self.root / "fake-generator"
        self.generator.write_text("#!/usr/bin/env python3\nimport pathlib,sys\npathlib.Path(sys.argv[1]).write_bytes(b'fake video bytes')\n", encoding="utf-8")
        self.generator.chmod(0o755)
        self.ffprobe = self.root / "fake-ffprobe"
        self.ffprobe.write_text("#!/usr/bin/env python3\nimport json\nprint(json.dumps({'streams':[{'codec_type':'video','codec_name':'h264','width':360,'height':640}],'format':{'duration':'1.0'}}))\n", encoding="utf-8")
        self.ffprobe.chmod(0o755)
    def tearDown(self): self.temp.cleanup()
    def test_generates_and_probes_video_via_local_process_without_shell(self):
        out = self.root / "sample.mp4"
        backend = LocalVideoBackend(str(self.generator), ["{output}"], ffprobe=str(self.ffprobe))
        result = backend.generate_clip(prompt="A fox runs", output=out, width=360, height=640,
                                       frames=25, seed=7, model="test-model")
        self.assertEqual(result["status"], "GENERATED_AND_PROBED")
        self.assertEqual(result["generation_host"], "termux_local")
        self.assertEqual(out.read_bytes(), b"fake video bytes")
    def test_rejects_unknown_template_placeholder(self):
        self.assertEqual(validate_template(["--prompt", "{prompt}"]), ["--prompt", "{prompt}"])
        with self.assertRaisesRegex(ValueError, "unsupported command placeholder"):
            validate_template(["{shell}"])
    def test_refuses_existing_output(self):
        out=self.root/"sample.mp4"; out.write_bytes(b"already here")
        backend=LocalVideoBackend(str(self.generator), ["{output}"], ffprobe=str(self.ffprobe))
        with self.assertRaisesRegex(LocalGenerationError, "overwrite"):
            backend.generate_clip(prompt="x", output=out, width=2, height=2, frames=1, seed=1, model="m")

if __name__ == "__main__": unittest.main()
