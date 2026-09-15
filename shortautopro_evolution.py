#!/usr/bin/env python3
"""ShortAutoPro Evolution compatibility facade.

The historical Evolution implementation is preserved byte-for-byte in
``shortautopro_evolution_core.py``. This small facade fixes two production bugs
without duplicating the scoring engine:

1. an explicit ``short_id`` can never fall back to another video's latest file;
2. profile-aware audits recover the Short profile from its own artifacts/client
   job when the original shell environment is no longer present.

All public names remain available for existing imports.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import shortautopro_evolution_core as _core

# Re-export the established public surface for modules that import this file as
# ``import shortautopro_evolution as evo``.
for _name in dir(_core):
    if not _name.startswith("__"):
        globals()[_name] = getattr(_core, _name)

_ORIGINAL_LATEST_VIDEO = _core.latest_video
_ORIGINAL_CAPTION_AUDIT = _core.caption_audit
_ORIGINAL_QUALITY_SCORE = _core.quality_score


def _artifact_profile(sid: str) -> str | None:
    """Resolve the profile that actually belongs to ``sid``.

    Resolution order intentionally prefers the current explicit environment,
    then per-Short artifacts, then the client job that owns the item. This
    keeps manual post-run audits faithful to the generation profile.
    """
    env_profile = os.getenv("SAP_CHANNEL_PROFILE", "").strip()
    if env_profile:
        return env_profile

    candidates = (
        _core.BASE / "roteiros" / f"pro_edit_plan_{sid}.json",
        _core.BASE / "manifests" / f"{sid}_professional.json",
    )
    for path in candidates:
        data = _core.read_json(path, {})
        if isinstance(data, dict):
            profile = str(data.get("profile", "") or "").strip()
            if profile:
                return profile

    jobs_dir = _core.REPORT_DIR / "client_jobs"
    if jobs_dir.is_dir():
        try:
            jobs = sorted(jobs_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        except OSError:
            jobs = []
        for path in jobs:
            data = _core.read_json(path, {})
            if not isinstance(data, dict):
                continue
            job_id = str(data.get("job_id", "") or "").strip()
            items = data.get("items", [])
            owns_sid = bool(job_id and sid.startswith(f"client_{job_id}_"))
            if isinstance(items, list):
                owns_sid = owns_sid or any(
                    isinstance(item, dict) and str(item.get("short_id", "") or "") == sid
                    for item in items
                )
            if owns_sid:
                profile = str(data.get("profile", "") or "").strip()
                if profile:
                    return profile
    return None


def latest_video(sid: str | None = None) -> Path | None:
    """Return only the requested Short when ``sid`` is explicit.

    The previous implementation fell back to the newest unrelated V6 file when
    an explicit Short had no render yet, which could make a failed production
    look technically healthy. Latest-file fallback remains valid only when no
    Short ID was requested.
    """
    if sid:
        candidate = _core.BASE / "videos" / f"short_v6_{sid}.mp4"
        return candidate if candidate.is_file() else None
    return _ORIGINAL_LATEST_VIDEO(None)


def _with_profile(sid: str, call):
    inferred = _artifact_profile(sid)
    previous = os.environ.get("SAP_CHANNEL_PROFILE")
    if inferred:
        os.environ["SAP_CHANNEL_PROFILE"] = inferred
    try:
        return call()
    finally:
        if previous is None:
            os.environ.pop("SAP_CHANNEL_PROFILE", None)
        else:
            os.environ["SAP_CHANNEL_PROFILE"] = previous


def caption_audit(sid: str | None = None, profile_name: str | None = None) -> dict[str, Any]:
    sid = sid or _core.short_id()
    if profile_name:
        return _ORIGINAL_CAPTION_AUDIT(sid, profile_name)
    return _with_profile(sid, lambda: _ORIGINAL_CAPTION_AUDIT(sid, None))


def quality_score(sid: str | None = None) -> dict[str, Any]:
    sid = sid or _core.short_id()
    return _with_profile(sid, lambda: _ORIGINAL_QUALITY_SCORE(sid))


# Patch the core module's global lookups so its existing CLI/main and scoring
# functions use the corrected semantics above.
_core.latest_video = latest_video
_core.caption_audit = caption_audit
_core.quality_score = quality_score

# Keep wrapper-level imports consistent with the patched core.
globals()["latest_video"] = latest_video
globals()["caption_audit"] = caption_audit
globals()["quality_score"] = quality_score


def main(argv: list[str] | None = None) -> int:
    return _core.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
