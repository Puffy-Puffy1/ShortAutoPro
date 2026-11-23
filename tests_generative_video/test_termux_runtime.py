import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from generative_video_poc.termux_runtime import TermuxRuntime, TermuxPreflightError, TERMUX_PREFIX


class TermuxRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.home = Path(self.temp.name)
        self.meminfo = self.home / "meminfo"
        self.meminfo.write_text("MemTotal:       8192000 kB\nMemAvailable:   4096000 kB\n", encoding="utf-8")
        self.env = {"PREFIX": TERMUX_PREFIX, "TERMUX_VERSION": "0.118", "HOME": str(self.home)}
        self.commands = {"python", "ffmpeg", "ffprobe", "git", "sd-cli"}

    def tearDown(self):
        self.temp.cleanup()

    def which(self, name):
        return f"/fake/bin/{name}" if name in self.commands else None

    def test_detects_termux_and_separates_controller_from_inference(self):
        report = TermuxRuntime(environ=self.env, machine="aarch64", meminfo_path=self.meminfo,
                               home=self.home, which=self.which).require_ready()
        self.assertEqual(report["runtime"], "termux")
        self.assertTrue(report["is_arm64"])
        self.assertTrue(report["native_inference_binary_present"])
        self.assertTrue(report["arm64_native_inference_candidate"])
        self.assertEqual(report["total_ram_mb"], 8000)
        self.assertEqual(report["remote_compute"], "disabled_by_default")

    def test_controller_preflight_does_not_reject_other_android_abis(self):
        report = TermuxRuntime(environ=self.env, machine="x86_64", meminfo_path=self.meminfo,
                               home=self.home, which=self.which).require_ready()
        self.assertFalse(report["is_arm64"])
        self.assertFalse(report["arm64_native_inference_candidate"])

    def test_rejects_non_termux_shell(self):
        runtime = TermuxRuntime(environ={"HOME": str(self.home)}, machine="aarch64",
                                meminfo_path=self.meminfo, home=self.home, which=self.which)
        with self.assertRaises(TermuxPreflightError):
            runtime.require_ready()

    def test_reports_missing_multimedia_tools(self):
        runtime = TermuxRuntime(environ=self.env, machine="aarch64", meminfo_path=self.meminfo,
                                home=self.home, which=lambda name: None)
        with self.assertRaisesRegex(TermuxPreflightError, "ffmpeg"):
            runtime.require_ready()

    def test_reads_only_allowlisted_android_properties_and_vulkan_summary(self):
        allowed = self.commands | {"getprop", "vulkaninfo"}
        def which(name):
            return f"/fake/bin/{name}" if name in allowed else None
        def runner(args, **_kwargs):
            if args[0].endswith("getprop"):
                return SimpleNamespace(
                    returncode=0,
                    stdout=("[ro.product.model]: [Phone X]\n"
                            "[ro.product.manufacturer]: [Example]\n"
                            "[ro.board.platform]: [soc123]\n"
                            "[ro.serialno]: [DO_NOT_REPORT]\n"),
                    stderr="",
                )
            return SimpleNamespace(returncode=0,
                                   stdout="deviceName = Example GPU\napiVersion = 1.3.0\n", stderr="")
        report = TermuxRuntime(environ=self.env, machine="aarch64", meminfo_path=self.meminfo,
                               home=self.home, which=which, command_runner=runner).inspect()
        self.assertEqual(report["android_device"]["model"], "Phone X")
        self.assertEqual(report["android_device"]["soc_platform"], "soc123")
        self.assertNotIn("DO_NOT_REPORT", str(report))
        self.assertEqual(report["vulkan"]["device_name"], "Example GPU")
        self.assertTrue(report["vulkan"]["runtime_detected"])


if __name__ == "__main__":
    unittest.main()
