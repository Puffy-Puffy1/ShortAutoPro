"""Immutable manifest export for FFprobe-validated locally generated clips."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from generative_video_poc.state_store import ProjectStore


SCHEMA_VERSION = "shortautopro-generated-clips-v1"


def _canonical(payload: dict[str, Any]) -> bytes:
    value = dict(payload)
    value.pop("integrity_sha256", None)
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _prompt_for(spec: dict[str, Any], clip: dict[str, Any]) -> str:
    prompts = spec.get("clip_prompts") if isinstance(spec.get("clip_prompts"), list) else []
    template = str(spec.get("prompt_template") or "")
    if prompts:
        prompt = str(prompts[int(clip["clip_index"]) - 1])
    else:
        prompt = template.format_map({
            "clip_index": clip["clip_index"],
            "start_seconds": clip["start_seconds"],
            "duration_seconds": clip["duration_seconds"],
        })
    if not prompt.strip():
        raise ValueError(f"clip {clip['clip_index']} has no recorded prompt")
    return prompt.strip()


def build_ready_manifest(store: ProjectStore, project_id: str) -> dict[str, Any]:
    project = store.get_project(project_id)
    if project["status"] != "COMPLETE":
        raise ValueError("only a COMPLETE project can be exported")
    clips = project["clips"]
    if not clips or any(item["status"] != "READY" for item in clips):
        raise ValueError("all scheduled clips must be READY before manifest export")

    project_root = store.project_dir(project_id).resolve()
    entries = []
    for clip in clips:
        output = Path(str(clip.get("output_path") or "")).expanduser().resolve()
        if not output.is_relative_to(project_root):
            raise ValueError("clip output escapes its project workspace")
        if not output.is_file() or output.stat().st_size <= 0:
            raise ValueError(f"clip {clip['clip_index']} output is missing or empty")
        metadata = clip.get("metadata")
        if not isinstance(metadata, dict) or metadata.get("status") != "GENERATED_AND_PROBED":
            raise ValueError(f"clip {clip['clip_index']} lacks FFprobe metadata")
        if not metadata.get("video_codec") or float(metadata.get("duration_seconds") or 0) <= 0:
            raise ValueError(f"clip {clip['clip_index']} has invalid FFprobe metadata")
        entries.append({
            "clip_index": int(clip["clip_index"]),
            "start_seconds": int(clip["start_seconds"]),
            "duration_seconds": int(clip["duration_seconds"]),
            "prompt": _prompt_for(project["spec"], clip),
            "path": str(output),
            "sha256": _sha256(output),
            "size_bytes": output.stat().st_size,
            "ffprobe": metadata,
        })

    payload = {
        "schema_version": SCHEMA_VERSION,
        "project_id": project_id,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "project": project["spec"],
        "clip_count": len(entries),
        "clips": entries,
    }
    payload["integrity_sha256"] = hashlib.sha256(_canonical(payload)).hexdigest()
    destination = project_root / "generated_manifest.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".generated_manifest.", suffix=".tmp", dir=str(destination.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return {**payload, "manifest_path": str(destination)}


def verify_ready_manifest(path: Path | str) -> dict[str, Any]:
    manifest_path = Path(path).expanduser().resolve()
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported generated clip manifest")
    expected = hashlib.sha256(_canonical(payload)).hexdigest()
    if payload.get("integrity_sha256") != expected:
        raise ValueError("generated clip manifest integrity check failed")
    project_id = ProjectStore.validate_project_id(str(payload.get("project_id") or ""))
    project_root = manifest_path.parent.resolve()
    if project_root.name != project_id:
        raise ValueError(f"manifest workspace mismatch: parent={project_root.name!r} project_id={project_id!r}")
    clips = payload.get("clips")
    if not isinstance(clips, list) or len(clips) != int(payload.get("clip_count") or -1):
        raise ValueError("manifest clip count is inconsistent")
    seen = set()
    for item in clips:
        index = int(item["clip_index"])
        if index in seen:
            raise ValueError("manifest contains duplicate clip indices")
        seen.add(index)
        media = Path(str(item["path"])).expanduser().resolve()
        if not media.is_relative_to(project_root) or not media.is_file():
            raise ValueError(f"clip {index} path is missing or outside the project")
        if _sha256(media) != item.get("sha256"):
            raise ValueError(f"clip {index} checksum mismatch")
    if seen != set(range(1, len(clips) + 1)):
        raise ValueError("manifest clip indices are not contiguous")
    return payload
