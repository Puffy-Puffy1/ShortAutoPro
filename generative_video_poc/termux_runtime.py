"""Termux-first Android device discovery and safe preflight."""
from __future__ import annotations
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Mapping

TERMUX_PREFIX = "/data/data/com.termux/files/usr"
ANDROID_PROPERTY_ALLOWLIST = {
    "ro.product.manufacturer", "ro.product.model", "ro.product.device",
    "ro.board.platform", "ro.hardware", "ro.soc.model",
    "ro.build.version.release", "ro.build.version.sdk",
    "ro.product.cpu.abi", "ro.hardware.egl",
}

class TermuxPreflightError(RuntimeError):
    """The current shell does not satisfy the Termux runtime contract."""

def _memory_mb(meminfo: str, key: str) -> int | None:
    match = re.search(rf"^{re.escape(key)}: +([0-9]+) +kB", meminfo, re.MULTILINE)
    return int(match.group(1)) // 1024 if match else None

class TermuxRuntime:
    REQUIRED_BINARIES = ("python", "ffmpeg", "ffprobe", "git")
    OPTIONAL_BINARIES = (
        "llama-cli", "llama-server", "sd-cli", "sd-server",
        "termux-wake-lock", "termux-info", "vulkaninfo", "getprop",
    )

    def __init__(
        self, *, environ: Mapping[str, str] | None = None, machine: str | None = None,
        meminfo_path: Path = Path("/proc/meminfo"), home: Path | None = None,
        which: Callable[[str], str | None] = shutil.which,
        command_runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    ):
        self.environ = dict(os.environ if environ is None else environ)
        self.machine = (machine or platform.machine()).lower()
        self.meminfo_path = Path(meminfo_path)
        self.home = Path(home or self.environ.get("HOME", str(Path.home())))
        self.which = which
        self.command_runner = command_runner

    def is_termux(self) -> bool:
        prefix = self.environ.get("PREFIX", "").rstrip("/")
        return bool(self.environ.get("TERMUX_VERSION")) and prefix == TERMUX_PREFIX

    def _android_properties(self, executable: str | None) -> dict[str, str]:
        if not executable:
            return {}
        try:
            proc = self.command_runner([executable], capture_output=True, text=True, timeout=3, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return {}
        if proc.returncode != 0:
            return {}
        values = {}
        for line in (proc.stdout or "").splitlines():
            match = re.match(r"^\[([^]]+)\]: \[(.*)\]$", line.strip())
            if match and match.group(1) in ANDROID_PROPERTY_ALLOWLIST:
                values[match.group(1)] = match.group(2)
        return values

    def _vulkan_report(self, executable: str | None) -> dict:
        result = {"tool_available": bool(executable), "runtime_detected": False,
                  "device_name": None, "api_version": None}
        if not executable:
            return result
        try:
            proc = self.command_runner(
                [executable, "--summary"], capture_output=True, text=True, timeout=6, check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return result
        output = (proc.stdout or "") + "\n" + (proc.stderr or "")
        result["runtime_detected"] = proc.returncode == 0
        device = re.search(r"deviceName\s*=\s*(.+)", output)
        api = re.search(r"apiVersion\s*=\s*([0-9.]+)", output)
        if device:
            result["device_name"] = device.group(1).strip()[:120]
        if api:
            result["api_version"] = api.group(1).strip()
        return result

    def inspect(self) -> dict:
        try:
            meminfo = self.meminfo_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            meminfo = ""
        binaries = {name: self.which(name) for name in self.REQUIRED_BINARIES + self.OPTIONAL_BINARIES}
        try:
            free_storage = shutil.disk_usage(self.home).free
        except OSError:
            free_storage = None
        is_arm64 = self.machine in {"aarch64", "arm64", "arm64-v8a"}
        properties = self._android_properties(binaries.get("getprop"))
        video_binary = bool(binaries.get("sd-cli") or binaries.get("sd-server"))
        return {
            "runtime": "termux" if self.is_termux() else "unsupported_shell",
            "android_abi": self.machine,
            "is_arm64": is_arm64,
            "termux_prefix": self.environ.get("PREFIX", ""),
            "termux_version": self.environ.get("TERMUX_VERSION", ""),
            "android_version": self.environ.get("ANDROID_VERSION", ""),
            "android_device": {
                "manufacturer": properties.get("ro.product.manufacturer"),
                "model": properties.get("ro.product.model"),
                "device": properties.get("ro.product.device"),
                "soc_platform": properties.get("ro.board.platform") or properties.get("ro.soc.model"),
                "hardware": properties.get("ro.hardware"),
                "cpu_abi": properties.get("ro.product.cpu.abi"),
                "android_release": properties.get("ro.build.version.release"),
                "android_sdk": properties.get("ro.build.version.sdk"),
                "egl_driver": properties.get("ro.hardware.egl"),
            },
            "total_ram_mb": _memory_mb(meminfo, "MemTotal"),
            "available_ram_mb": _memory_mb(meminfo, "MemAvailable"),
            "free_storage_bytes": free_storage,
            "home": str(self.home),
            "model_dir": str(self.home / ".shortautopro" / "models"),
            "state_dir": str(self.home / ".shortautopro" / "state"),
            "project_dir": str(self.home / ".shortautopro" / "projects"),
            "shared_storage": str(self.home / "storage" / "shared"),
            "binaries": binaries,
            "local_text_director_available": bool(binaries.get("llama-cli")),
            "local_text_server_available": bool(binaries.get("llama-server")),
            "local_video_inference_binary_present": video_binary,
            "arm64_video_inference_candidate": bool(is_arm64 and binaries.get("sd-cli")),
            "vulkan": self._vulkan_report(binaries.get("vulkaninfo")),
            "remote_compute": "disabled_by_default",
        }

    def require_ready(self) -> dict:
        report = self.inspect()
        errors = []
        if not self.is_termux():
            errors.append("run this from Termux (not PRoot/Linux desktop or GitHub Actions)")
        for name in self.REQUIRED_BINARIES:
            if not report["binaries"].get(name):
                errors.append(f"required command not found: {name}")
        if errors:
            raise TermuxPreflightError("; ".join(errors))
        return report

def main() -> int:
    import json
    runtime = TermuxRuntime()
    try:
        report = runtime.require_ready()
        status = "TERMUX_PREFLIGHT=PASS"
    except TermuxPreflightError as exc:
        report = runtime.inspect()
        report["preflight_error"] = str(exc)
        status = "TERMUX_PREFLIGHT=FAIL"
    print(status)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if status.endswith("PASS") else 2

if __name__ == "__main__":
    raise SystemExit(main())
