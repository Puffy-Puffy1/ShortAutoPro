"""Termux-first device discovery and preflight for ShortAutoPro."""
from __future__ import annotations
import os
import platform
import re
import shutil
from pathlib import Path
from typing import Callable, Mapping

TERMUX_PREFIX = "/data/data/com.termux/files/usr"
class TermuxPreflightError(RuntimeError):
    """The current shell does not satisfy the Termux runtime contract."""

def _memory_mb(meminfo: str, key: str) -> int | None:
    match = re.search(rf"^{re.escape(key)}: +([0-9]+) +kB", meminfo, re.MULTILINE)
    return int(match.group(1)) // 1024 if match else None

class TermuxRuntime:
    REQUIRED_BINARIES = ("python", "ffmpeg", "ffprobe", "git")
    OPTIONAL_BINARIES = ("sd-cli", "sd-server", "termux-wake-lock", "termux-info", "vulkaninfo")
    def __init__(self, *, environ: Mapping[str, str] | None = None,
                 machine: str | None = None, meminfo_path: Path = Path("/proc/meminfo"),
                 home: Path | None = None, which: Callable[[str], str | None] = shutil.which):
        self.environ = dict(os.environ if environ is None else environ)
        self.machine = (machine or platform.machine()).lower()
        self.meminfo_path = Path(meminfo_path)
        self.home = Path(home or self.environ.get("HOME", str(Path.home())))
        self.which = which
    def is_termux(self) -> bool:
        prefix = self.environ.get("PREFIX", "").rstrip("/")
        return bool(self.environ.get("TERMUX_VERSION")) and prefix == TERMUX_PREFIX
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
        return {
            "runtime": "termux" if self.is_termux() else "unsupported_shell",
            "android_abi": self.machine,
            "is_arm64": self.machine in {"aarch64", "arm64", "arm64-v8a"},
            "termux_prefix": self.environ.get("PREFIX", ""),
            "termux_version": self.environ.get("TERMUX_VERSION", ""),
            "android_version": self.environ.get("ANDROID_VERSION", ""),
            "total_ram_mb": _memory_mb(meminfo, "MemTotal"),
            "available_ram_mb": _memory_mb(meminfo, "MemAvailable"),
            "free_storage_bytes": free_storage,
            "home": str(self.home),
            "model_dir": str(self.home / ".shortautopro" / "models"),
            "run_dir": str(self.home / ".shortautopro" / "runs"),
            "shared_storage": str(self.home / "storage" / "shared"),
            "binaries": binaries,
            "generation_backend_available": bool(binaries.get("sd-cli") or binaries.get("sd-server")),
            "remote_compute": "disabled_by_default",
        }
    def require_ready(self) -> dict:
        report = self.inspect()
        errors = []
        if not self.is_termux():
            errors.append("run this from Termux (not PRoot/Linux desktop or GitHub Actions)")
        if not report["is_arm64"]:
            errors.append(f"unsupported Android ABI: {self.machine}; arm64 is required")
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
        report = runtime.require_ready(); status = "TERMUX_PREFLIGHT=PASS"
    except TermuxPreflightError as exc:
        report = runtime.inspect(); report["preflight_error"] = str(exc); status = "TERMUX_PREFLIGHT=FAIL"
    print(status); print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if status.endswith("PASS") else 2
if __name__ == "__main__": raise SystemExit(main())
