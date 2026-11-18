"""Safe adapter for a local Android/Termux video-generation executable."""
from __future__ import annotations
import json
import shutil
import subprocess
from pathlib import Path
from string import Formatter
from typing import Sequence

class LocalGenerationError(RuntimeError):
    """Local generation failed or did not produce a valid video clip."""

_ALLOWED_FIELDS = {"prompt", "output", "width", "height", "frames", "seed", "model"}

def validate_template(template: Sequence[str]) -> list[str]:
    if not isinstance(template, (list, tuple)) or not template:
        raise ValueError("command_template must be a non-empty argument list")
    result = []
    for item in template:
        if not isinstance(item, str) or not item:
            raise ValueError("command arguments must be non-empty strings")
        for _, field, _, _ in Formatter().parse(item):
            if field and field not in _ALLOWED_FIELDS:
                raise ValueError(f"unsupported command placeholder: {field}")
        result.append(item)
    return result

class LocalVideoBackend:
    def __init__(self, executable: str, command_template: Sequence[str], *,
                 timeout_seconds: int = 1800, ffprobe: str = "ffprobe"):
        resolved = shutil.which(executable) if "/" not in executable else executable
        if not resolved or not Path(resolved).is_file():
            raise ValueError(f"local generation executable not found: {executable}")
        if not 1 <= int(timeout_seconds) <= 14400:
            raise ValueError("timeout_seconds must be between 1 and 14400")
        self.executable = str(resolved)
        self.command_template = validate_template(command_template)
        self.timeout_seconds = int(timeout_seconds)
        self.ffprobe = shutil.which(ffprobe) if "/" not in ffprobe else ffprobe
        if not self.ffprobe or not Path(self.ffprobe).is_file():
            raise ValueError("ffprobe is required to validate a generated clip")

    def generate_clip(self, *, prompt: str, output: Path, width: int,
                      height: int, frames: int, seed: int, model: str) -> dict:
        if not prompt.strip() or width <= 0 or height <= 0 or frames <= 0:
            raise ValueError("prompt, dimensions and frame count must be valid")
        output = Path(output).expanduser().resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.suffix.lower() not in {".mp4", ".webm", ".mkv", ".mov"}:
            raise ValueError("output must use a supported video extension")
        if output.exists():
            raise LocalGenerationError("refusing to overwrite an existing output")
        values = {"prompt": prompt, "output": str(output), "width": str(width),
                  "height": str(height), "frames": str(frames), "seed": str(seed), "model": model}
        args = [self.executable] + [part.format_map(values) for part in self.command_template]
        try:
            proc = subprocess.run(args, capture_output=True, text=True,
                                  timeout=self.timeout_seconds, check=False)
        except subprocess.TimeoutExpired as exc:
            raise LocalGenerationError("local model generation timed out") from exc
        except OSError as exc:
            raise LocalGenerationError(f"could not start local model: {type(exc).__name__}") from exc
        if proc.returncode != 0:
            tail = (proc.stderr or proc.stdout or "")[-1200:]
            raise LocalGenerationError(f"local model exited with code {proc.returncode}: {tail}")
        if not output.is_file() or output.stat().st_size == 0:
            raise LocalGenerationError("local model reported success but produced no video file")
        try:
            probe = subprocess.run([self.ffprobe, "-v", "error", "-show_entries",
                                    "stream=codec_type,codec_name,width,height", "-show_entries",
                                    "format=duration", "-of", "json", str(output)],
                                   capture_output=True, text=True, timeout=30, check=False)
            data = json.loads(probe.stdout) if probe.returncode == 0 else {}
        except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
            raise LocalGenerationError("FFprobe could not inspect generated clip") from exc
        streams = data.get("streams", []) if isinstance(data, dict) else []
        video = next((s for s in streams if isinstance(s, dict) and s.get("codec_type") == "video"), None)
        duration = float((data.get("format", {}) or {}).get("duration") or 0)
        if not video or duration <= 0:
            raise LocalGenerationError("generated file is not a valid video stream")
        return {"status": "GENERATED_AND_PROBED", "path": str(output),
                "size_bytes": output.stat().st_size, "duration_seconds": duration,
                "video_codec": video.get("codec_name"), "width": video.get("width"),
                "height": video.get("height"), "generation_host": "termux_local"}
