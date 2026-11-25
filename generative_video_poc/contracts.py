"""Shared project/clip contracts for Shorts and long-form video generation."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class Clip:
    index: int
    start_seconds: int
    duration_seconds: int

@dataclass(frozen=True)
class ProjectSpec:
    kind: str
    target_duration_seconds: int
    aspect_ratio: str
    width: int
    height: int
    clip_seconds: int = 10
    prompt_template: str = ""
    clip_prompts: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ProjectSpec":
        if not isinstance(payload, dict):
            raise ValueError("project spec must be an object")
        kind = str(payload.get("kind", "")).strip().lower()
        if kind not in {"shorts", "longform"}:
            raise ValueError("kind must be 'shorts' or 'longform'")
        try:
            duration, width, height = int(payload["target_duration_seconds"]), int(payload["width"]), int(payload["height"])
            clip_seconds = int(payload.get("clip_seconds", 10))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("duration, width, height and clip_seconds must be integers") from exc
        ratio = str(payload.get("aspect_ratio", "")).strip()
        if duration <= 0 or width <= 0 or height <= 0:
            raise ValueError("duration and output dimensions must be positive")
        if duration > 7200:
            raise ValueError("projects are limited to 120 minutes")
        if not 1 <= clip_seconds <= 30:
            raise ValueError("clip_seconds must be between 1 and 30")
        expected = "9:16" if kind == "shorts" else "16:9"
        if ratio != expected:
            raise ValueError(f"{kind} projects require aspect_ratio {expected}")
        if kind == "shorts" and duration > 180:
            raise ValueError("Shorts proof-of-concept projects are limited to 180 seconds")
        if ratio == "9:16" and height <= width:
            raise ValueError("9:16 output must be portrait")
        if ratio == "16:9" and width <= height:
            raise ValueError("16:9 output must be landscape")
        prompt_template = str(payload.get("prompt_template", "")).strip()
        if len(prompt_template) > 4000:
            raise ValueError("prompt_template must not exceed 4000 characters")
        raw_prompts = payload.get("clip_prompts", [])
        if not isinstance(raw_prompts, list):
            raise ValueError("clip_prompts must be a list when provided")
        clip_prompts = tuple(str(item).strip() for item in raw_prompts)
        if any(not item or len(item) > 4000 for item in clip_prompts):
            raise ValueError("each clip prompt must contain 1-4000 characters")
        if sum(len(item) for item in clip_prompts) > 500000:
            raise ValueError("combined clip prompts must not exceed 500000 characters")
        expected_clips = (duration + clip_seconds - 1) // clip_seconds
        if clip_prompts and len(clip_prompts) != expected_clips:
            raise ValueError(f"clip_prompts must contain exactly {expected_clips} entries")
        if clip_prompts and prompt_template:
            raise ValueError("use clip_prompts or prompt_template, not both")
        return cls(kind, duration, ratio, width, height, clip_seconds, prompt_template, clip_prompts)

    def clip_schedule(self) -> list[Clip]:
        clips, start = [], 0
        while start < self.target_duration_seconds:
            duration = min(self.clip_seconds, self.target_duration_seconds - start)
            clips.append(Clip(len(clips) + 1, start, duration))
            start += duration
        return clips

    def summary(self) -> dict[str, Any]:
        clips = self.clip_schedule()
        return {"kind": self.kind, "target_duration_seconds": self.target_duration_seconds,
                "aspect_ratio": self.aspect_ratio, "width": self.width, "height": self.height,
                "clip_seconds": self.clip_seconds, "planned_clip_count": len(clips),
                "planned_duration_seconds": sum(c.duration_seconds for c in clips),
                "generation_status": "NOT_STARTED"}
