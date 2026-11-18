import tempfile
import unittest
from pathlib import Path
from generative_video_poc.termux_runtime import TermuxRuntime, TermuxPreflightError, TERMUX_PREFIX

class TermuxRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.home = Path(self.temp.name)
        self.meminfo = self.home / "meminfo"
        self.meminfo.write_text("MemTotal:       8192000 kB\nMemAvailable:   4096000 kB\n", encoding="utf-8")
        self.env = {"PREFIX": TERMUX_PREFIX, "TERMUX_VERSION": "0.118", "HOME": str(self.home)}
        self.commands = {"python", "ffmpeg", "ffprobe", "git", "sd-cli"}
    def tearDown(self): self.temp.cleanup()
    def which(self, name): return f"/fake/bin/{name}" if name in self.commands else None
    def test_detects_arm64_termux_and_reports_local_backend(self):
        report = TermuxRuntime(environ=self.env, machine="aarch64", meminfo_path=self.meminfo,
                               home=self.home, which=self.which).require_ready()
        self.assertEqual(report["runtime"], "termux"); self.assertTrue(report["is_arm64"])
        self.assertTrue(report["generation_backend_available"]); self.assertEqual(report["total_ram_mb"], 8192)
        self.assertEqual(report["remote_compute"], "disabled_by_default")
    def test_rejects_non_termux_shell(self):
        runtime = TermuxRuntime(environ={"HOME":str(self.home)}, machine="aarch64",
                                meminfo_path=self.meminfo, home=self.home, which=self.which)
        with self.assertRaises(TermuxPreflightError): runtime.require_ready()
    def test_reports_missing_multimedia_tools(self):
        runtime = TermuxRuntime(environ=self.env, machine="aarch64", meminfo_path=self.meminfo,
                                home=self.home, which=lambda name: None)
        with self.assertRaisesRegex(TermuxPreflightError, "ffmpeg"): runtime.require_ready()

if __name__ == "__main__": unittest.main()
