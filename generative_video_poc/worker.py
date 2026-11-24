"""One-clip-at-a-time local generation worker for the durable Termux queue."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable

from generative_video_poc.local_video_backend import LocalGenerationError, LocalVideoBackend
from generative_video_poc.state_store import LeaseError, ProjectStore


class WorkerConfigError(ValueError):
    """The local generator configuration is incomplete or unsafe."""


def load_backend_config(path: Path | str) -> tuple[LocalVideoBackend, dict[str, Any]]:
    config_path = Path(path).expanduser().resolve()
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkerConfigError(f"cannot read backend config: {type(exc).__name__}") from exc
    if not isinstance(data, dict):
        raise WorkerConfigError("backend config root must be an object")

    executable = str(data.get("executable") or "").strip()
    template = data.get("command_template")
    if not executable or not isinstance(template, list) or not template:
        raise WorkerConfigError("backend config requires executable and command_template")
    try:
        timeout = int(data.get("timeout_seconds", 1800))
        fps = int(data.get("fps", 12))
        seed = int(data.get("seed", 1))
        model = str(data.get("model") or "local-default").strip()
        backend = LocalVideoBackend(
            executable,
            template,
            timeout_seconds=timeout,
            ffprobe=str(data.get("ffprobe") or "ffprobe"),
        )
    except (TypeError, ValueError) as exc:
        raise WorkerConfigError(str(exc)) from exc
    if not 1 <= fps <= 60:
        raise WorkerConfigError("fps must be between 1 and 60")
    if not model or len(model) > 200:
        raise WorkerConfigError("model must contain 1-200 characters")
    return backend, {"timeout_seconds": timeout, "fps": fps, "seed": seed, "model": model}


class LocalQueueWorker:
    """Claims and generates one clip, then commits only an FFprobe-validated result."""

    def __init__(
        self,
        store: ProjectStore,
        backend: LocalVideoBackend,
        *,
        fps: int = 12,
        seed: int = 1,
        model: str = "local-default",
        worker_id: str = "termux-local-worker",
        timeout_seconds: int = 1800,
        backend_call: Callable[..., dict[str, Any]] | None = None,
    ):
        if not 1 <= int(fps) <= 60:
            raise ValueError("fps must be between 1 and 60")
        if not 1 <= int(timeout_seconds) <= 14400:
            raise ValueError("timeout_seconds must be between 1 and 14400")
        self.store = store
        self.backend = backend
        self.fps = int(fps)
        self.seed = int(seed)
        self.model = str(model)
        self.worker_id = str(worker_id).strip()
        self.timeout_seconds = int(timeout_seconds)
        if not self.worker_id or len(self.worker_id) > 100:
            raise ValueError("worker_id must contain 1-100 characters")
        self.backend_call = backend_call or backend.generate_clip

    @staticmethod
    def _prompt(template: str, claim: dict[str, Any]) -> str:
        allowed = {"clip_index", "start_seconds", "duration_seconds"}
        fields = set(re.findall(r"{([a-zA-Z_][a-zA-Z0-9_]*)}", template))
        unknown = fields - allowed
        if unknown:
            raise WorkerConfigError(f"unsupported prompt placeholders: {', '.join(sorted(unknown))}")
        try:
            prompt = template.format_map({
                "clip_index": claim["clip_index"],
                "start_seconds": claim["start_seconds"],
                "duration_seconds": claim["duration_seconds"],
            }).strip()
        except (KeyError, ValueError) as exc:
            raise WorkerConfigError("invalid prompt_template") from exc
        if not prompt:
            raise WorkerConfigError("project prompt_template is required before generation")
        return prompt

    def run_one(self, project_id: str | None = None) -> dict[str, Any]:
        if project_id:
            project = self.store.get_project(project_id)
            spec = project["spec"]
            prompt_template = str(spec.get("prompt_template") or "").strip()
            clip_prompts = spec.get("clip_prompts") if isinstance(spec.get("clip_prompts"), list) else []
            if not prompt_template and not clip_prompts:
                raise WorkerConfigError("project has no prompt_template or clip_prompts; refusing generic clips")
            # Validate prompt source before claiming work.
            self._prompt(
                str(clip_prompts[0]) if clip_prompts else prompt_template,
                {"clip_index": 1, "start_seconds": 0, "duration_seconds": 1},
            )

        lease_seconds = min(86400, self.timeout_seconds + 180)
        claim = self.store.claim_next_clip(
            self.worker_id, project_id=project_id, lease_seconds=lease_seconds,
        )
        if claim is None:
            return {"status": "QUEUE_EMPTY", "project_id": project_id}

        project = self.store.get_project(claim["project_id"])
        spec = project["spec"]
        try:
            clip_prompts = spec.get("clip_prompts") if isinstance(spec.get("clip_prompts"), list) else []
            prompt_source = (
                str(clip_prompts[int(claim["clip_index"]) - 1])
                if clip_prompts else str(spec.get("prompt_template") or "")
            )
            prompt = self._prompt(prompt_source, claim)
            duration = int(claim["duration_seconds"])
            result = self.backend_call(
                prompt=prompt,
                output=Path(claim["output_path"]),
                width=int(spec["width"]),
                height=int(spec["height"]),
                frames=max(1, duration * self.fps),
                seed=self.seed + int(claim["clip_index"]),
                model=self.model,
            )
            if result.get("status") != "GENERATED_AND_PROBED":
                raise LocalGenerationError("backend did not return FFprobe validation")
            if int(result.get("width") or 0) != int(spec["width"]):
                raise LocalGenerationError("generated clip width does not match project")
            if int(result.get("height") or 0) != int(spec["height"]):
                raise LocalGenerationError("generated clip height does not match project")
            actual_duration = float(result.get("duration_seconds") or 0)
            if actual_duration < duration * 0.95 or actual_duration > duration * 1.10:
                raise LocalGenerationError("generated clip duration is outside the allowed tolerance")

            completed = self.store.complete_clip(
                claim["project_id"], claim["clip_index"], self.worker_id,
                claim["lease_token"], result["path"], result,
            )
            return {
                "status": "CLIP_READY",
                "project_id": claim["project_id"],
                "clip_index": claim["clip_index"],
                "clip": result,
                "project_status": completed["status"],
                "progress": completed["progress"],
            }
        except Exception as exc:
            output = Path(claim["output_path"])
            try:
                if output.is_file():
                    output.unlink()
            except OSError:
                pass
            retryable = isinstance(exc, (LocalGenerationError, TimeoutError, OSError))
            error_code = "WORKER_INVALID_CONFIG" if isinstance(exc, (WorkerConfigError, ValueError)) else f"WORKER_{type(exc).__name__}".upper()
            try:
                retry_status = self.store.fail_clip(
                    claim["project_id"], claim["clip_index"], self.worker_id,
                    claim["lease_token"], error_code, retryable=retryable,
                )
            except LeaseError:
                retry_status = "LEASE_LOST"
            return {
                "status": "CLIP_FAILED",
                "project_id": claim["project_id"],
                "clip_index": claim["clip_index"],
                "error": type(exc).__name__,
                "retry_status": retry_status,
            }


    def run_until_idle(self, project_id: str) -> dict[str, Any]:
        """Process queued clips until completion, exhaustion or a terminal failure."""
        project = self.store.get_project(project_id)
        total = int(project["progress"]["total"])
        max_attempts = max(
            (int(item.get("max_attempts") or 1) for item in project["clips"]),
            default=1,
        )
        safety_limit = max(1, total * max_attempts)
        generated = 0
        attempts = 0

        while attempts < safety_limit:
            result = self.run_one(project_id)
            attempts += 1
            if result["status"] == "QUEUE_EMPTY":
                current = self.store.get_project(project_id)
                status = "PROJECT_COMPLETE" if current["status"] == "COMPLETE" else "PROJECT_INCOMPLETE"
                return {
                    "status": status,
                    "project_id": project_id,
                    "generated_clips": generated,
                    "worker_attempts": attempts,
                    "progress": current["progress"],
                }
            if result["status"] == "CLIP_READY":
                generated += 1
                continue
            if result["status"] == "CLIP_FAILED":
                if result.get("retry_status") == "PENDING":
                    continue
                return {
                    "status": "PROJECT_FAILED",
                    "project_id": project_id,
                    "generated_clips": generated,
                    "worker_attempts": attempts,
                    "failure": result,
                    "progress": self.store.get_project(project_id)["progress"],
                }

        current = self.store.get_project(project_id)
        return {
            "status": "WORKER_SAFETY_LIMIT",
            "project_id": project_id,
            "generated_clips": generated,
            "worker_attempts": attempts,
            "progress": current["progress"],
        }
