#!/usr/bin/env python3
"""Measured visual QA for selected assets and final video.

The final-video diagnostics share one FFmpeg decode pass on mobile instead of
decoding the same Short three times for blackdetect, cropdetect and blurdetect.
"""

from __future__ import annotations

import collections
import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import date
from pathlib import Path
from typing import Any

from runtime_config import env_float, env_int
from subprocess_guard import check_output_group, run_group

BASE = Path(
    os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))
).resolve()
SID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
MEDIA = BASE / "imagens" / f"short_{SID}"
VIDEO = BASE / "videos" / f"short_v6_{SID}.mp4"
MAP = BASE / "roteiros" / f"scene_map_{SID}.json"
VSCORE = BASE / "roteiros" / f"visual_score_{SID}.json"
RUNTIME = BASE / "roteiros" / f"pro_edit_runtime_{SID}.json"
OUT = BASE / "reports" / "evolution" / f"visual_qa_{SID}.json"


def atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        tmp = ""
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def probe(path: Path) -> dict[str, Any]:
    try:
        result = run_group(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,codec_name,avg_frame_rate",
                "-of", "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=20,
        )
    except Exception:
        return {}
    if result.returncode:
        return {}
    try:
        streams = json.loads(result.stdout).get("streams", [])
        return streams[0] if streams else {}
    except Exception:
        return {}


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


_FILTERS_CACHE: set[str] | None = None


def available_filters() -> set[str]:
    global _FILTERS_CACHE
    if _FILTERS_CACHE is not None:
        return _FILTERS_CACHE
    try:
        raw = check_output_group(
            ["ffmpeg", "-hide_banner", "-filters"],
            text=True,
            stderr=subprocess.STDOUT,
            timeout=20,
        )
        _FILTERS_CACHE = {
            line.split()[1]
            for line in raw.splitlines()
            if len(line.split()) >= 2 and line.startswith(" ")
        }
    except Exception:
        _FILTERS_CACHE = set()
    return _FILTERS_CACHE


def analyze_final_video(path: Path) -> dict[str, Any]:
    measurements = {
        "black_seconds": 0.0,
        "cropdetect": None,
        "blur_metric": None,
        "blur_detector_available": "blurdetect" in available_filters(),
        "crop_detector_available": "cropdetect" in available_filters(),
        "single_pass": True,
    }
    if not path.is_file():
        return measurements

    branches: list[tuple[str, str]] = [
        (
            "black",
            "scale=360:-2,blackdetect=d=0.12:pix_th=0.02",
        )
    ]
    if measurements["crop_detector_available"]:
        branches.append(
            (
                "crop",
                "trim=duration=12,fps=1,cropdetect=24:16:0",
            )
        )
    if measurements["blur_detector_available"]:
        branches.append(
            (
                "blur",
                "trim=duration=12,fps=1,scale=360:-2,"
                "blurdetect=block_width=32:block_height=32:block_pct=80",
            )
        )

    count = len(branches)
    if count == 1:
        graph = f"[0:v]{branches[0][1]}[{branches[0][0]}]"
    else:
        inputs = "".join(f"[q{i}]" for i in range(count))
        parts = [f"[0:v]split={count}{inputs}"]
        for index, (label, chain) in enumerate(branches):
            parts.append(f"[q{index}]{chain}[{label}]")
        graph = ";".join(parts)

    cmd = [
        "ffmpeg", "-hide_banner", "-nostats",
        "-i", str(path),
        "-filter_complex", graph,
    ]
    for label, _ in branches:
        cmd.extend(["-map", f"[{label}]"])
    cmd.extend(["-an", "-f", "null", "-"])

    timeout = env_int("SAP_VISUAL_QA_VIDEO_SCAN_TIMEOUT", 120, 45, 300)
    try:
        result = run_group(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
        )
        stderr = result.stderr or ""
    except Exception as exc:
        print(
            "VISUAL_QA_VIDEO_SCAN=FAIL_OPEN "
            f"{type(exc).__name__}:{str(exc)[:160]}"
        )
        measurements["single_pass"] = False
        return measurements

    measurements["black_seconds"] = round(
        sum(
            float(value)
            for value in re.findall(
                r"black_duration:([0-9.]+)",
                stderr,
            )
        ),
        3,
    )

    crops = re.findall(
        r"crop=(\d+):(\d+):(\d+):(\d+)",
        stderr,
    )
    if crops:
        common = collections.Counter(crops).most_common(1)[0][0]
        width, height, x, y = map(int, common)
        measurements["cropdetect"] = {
            "width": width,
            "height": height,
            "x": x,
            "y": y,
        }

    values = [
        float(value)
        for value in re.findall(
            r"blur(?:mean)?:\s*([0-9.]+)",
            stderr,
            re.I,
        )
    ]
    if values:
        measurements["blur_metric"] = round(
            sum(values) / len(values),
            3,
        )

    return measurements



def _frame_sample(path: Path, timestamp: float) -> bytes:
    """Sample the background-dominant upper frame area for diversity checks."""
    return check_output_group(
        [
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-ss", f"{max(0.0, timestamp):.3f}", "-i", str(path),
            "-frames:v", "1",
            "-vf", "crop=iw:ih*0.62:0:0,scale=24:24:flags=area,format=rgb24",
            "-f", "rawvideo", "-",
        ],
        timeout=25,
        stderr=subprocess.DEVNULL,
    )


def _frame_mad(a: bytes, b: bytes) -> float:
    if not a or not b or len(a) != len(b):
        return 1.0
    return sum(abs(x - y) for x, y in zip(a, b)) / (255.0 * len(a))


def analyze_scene_diversity(path: Path) -> dict[str, Any]:
    runtime = load(RUNTIME)
    raw_durations = runtime.get("durations", []) if isinstance(runtime.get("durations"), list) else []
    durations: list[float] = []
    for value in raw_durations:
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = 0.0
        if number > 0:
            durations.append(number)
    expected = env_int("SHORT_QTD_CENAS", 12, 6, 20)
    if len(durations) != expected or not path.is_file():
        return {
            "available": False,
            "reason": "runtime_durations_missing_or_invalid",
            "expected_scenes": expected,
            "sampled_scenes": 0,
        }

    timestamps: list[float] = []
    cursor = 0.0
    for duration_value in durations:
        timestamps.append(cursor + max(0.15, duration_value * 0.50))
        cursor += duration_value

    frames: list[bytes] = []
    try:
        for timestamp in timestamps:
            raw = _frame_sample(path, timestamp)
            if not isinstance(raw, (bytes, bytearray)) or len(raw) < 24 * 24 * 3:
                raise ValueError("short_frame")
            frames.append(bytes(raw[:24 * 24 * 3]))
    except Exception as exc:
        return {
            "available": False,
            "reason": f"sampling_failed:{type(exc).__name__}",
            "expected_scenes": expected,
            "sampled_scenes": len(frames),
        }

    threshold = env_float("SAP_VISUAL_CHANGE_MAD_MIN", 0.045, 0.015, 0.18)
    consecutive = [
        round(_frame_mad(frames[i - 1], frames[i]), 4)
        for i in range(1, len(frames))
    ]
    changes = sum(1 for value in consecutive if value >= threshold)

    representatives: list[bytes] = []
    cluster_ids: list[int] = []
    for frame in frames:
        cluster = None
        for index, rep in enumerate(representatives):
            if _frame_mad(frame, rep) < threshold:
                cluster = index
                break
        if cluster is None:
            representatives.append(frame)
            cluster = len(representatives) - 1
        cluster_ids.append(cluster)

    unique = len(representatives)
    unique_ratio = unique / max(1, expected)
    change_ratio = changes / max(1, expected - 1)
    minimum_unique = max(4, int(round(expected * 0.58)))
    minimum_change_ratio = env_float("SAP_VISUAL_CHANGE_RATIO_MIN", 0.55, 0.25, 0.90)

    if unique < minimum_unique or change_ratio < minimum_change_ratio:
        status = "REVIEW"
    else:
        status = "PASS"

    return {
        "available": True,
        "status": status,
        "expected_scenes": expected,
        "sampled_scenes": len(frames),
        "unique_visual_clusters": unique,
        "unique_ratio": round(unique_ratio, 3),
        "scene_changes": changes,
        "change_ratio": round(change_ratio, 3),
        "minimum_unique_clusters": minimum_unique,
        "minimum_change_ratio": minimum_change_ratio,
        "mad_threshold": threshold,
        "consecutive_mad": consecutive,
        "cluster_ids": cluster_ids,
        "timestamps": [round(x, 3) for x in timestamps],
    }


def main() -> int:
    issues: list[str] = []
    warnings: list[str] = []
    assets: list[dict[str, Any]] = []
    hashes: dict[str, str] = {}

    scene_map = load(MAP)
    scenes = (
        scene_map.get("scenes", [])
        if isinstance(scene_map.get("scenes"), list)
        else []
    )
    vscore = load(VSCORE)
    score_rows = (
        vscore.get("scenes", [])
        if isinstance(vscore.get("scenes"), list)
        else []
    )

    if not MEDIA.is_dir():
        issues.append("media_directory_missing")
    else:
        files = sorted(
            path
            for path in MEDIA.iterdir()
            if path.is_file()
            and path.suffix.lower()
            in {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm"}
        )
        expected = env_int("SHORT_QTD_CENAS", 12, 6, 20)
        primary = [
            path
            for path in files
            if re.fullmatch(
                r"scene_\d{2}\.(?:jpg|jpeg|png|webp|mp4|mov|webm)",
                path.name,
                re.I,
            )
        ]
        if len(primary) != expected:
            issues.append(f"primary_scene_count:{len(primary)}/{expected}")

        for path in primary:
            meta = probe(path)
            width = int(meta.get("width", 0) or 0)
            height = int(meta.get("height", 0) or 0)
            digest = sha(path)
            duplicate = hashes.get(digest)
            hashes[digest] = path.name
            scene_no = int(re.search(r"(\d{2})", path.name).group(1))
            scene = (
                scenes[scene_no - 1]
                if scene_no <= len(scenes)
                and isinstance(scenes[scene_no - 1], dict)
                else {}
            )
            score_row = (
                score_rows[scene_no - 1]
                if scene_no <= len(score_rows)
                and isinstance(score_rows[scene_no - 1], dict)
                else {}
            )
            provider = str(score_row.get("provider", "") or "")

            item = {
                "scene": scene_no,
                "file": path.name,
                "width": width,
                "height": height,
                "pixels": width * height,
                "duplicate_of": duplicate,
                "protected_zone": scene.get("protected_zone"),
                "main_subject": scene.get("main_subject"),
                "provider": provider or None,
            }

            if width * height < 320 * 180:
                issues.append(f"critical_resolution:{path.name}")
            elif width * height < 1280 * 720:
                warnings.append(f"low_resolution:{path.name}")

            if duplicate:
                issues.append(f"exact_duplicate:{path.name}:{duplicate}")

            if height > 0 and width / height > 2.2:
                warnings.append(f"extreme_horizontal_crop_risk:{path.name}")

            if (
                str(scene.get("protected_zone", "")) == "center"
                and str(scene.get("shot_type", "")) in {"portrait", "close_up"}
                and width > height
            ):
                warnings.append(f"face_crop_risk:{path.name}")

            if not provider:
                warnings.append(f"watermark_provenance_unknown:{path.name}")

            item["watermark_risk"] = (
                "LOW"
                if provider
                in {
                    "Pexels",
                    "Pixabay",
                    "Wikimedia",
                    "Wikimedia Commons",
                    "Coverr",
                }
                else "UNKNOWN"
            )
            assets.append(item)

    if not VIDEO.is_file():
        issues.append("final_video_missing")

    measurements = analyze_final_video(VIDEO)
    diversity = analyze_scene_diversity(VIDEO)
    measurements["scene_diversity"] = diversity
    black = float(measurements["black_seconds"] or 0.0)
    crop = measurements["cropdetect"]
    blur = measurements["blur_metric"]

    diversity_penalty = 0.0
    if diversity.get("available"):
        unique_ratio = float(diversity.get("unique_ratio", 0.0) or 0.0)
        change_ratio = float(diversity.get("change_ratio", 0.0) or 0.0)
        if str(diversity.get("status", "")).upper() == "REVIEW":
            warnings.append(
                "visual_diversity_low:"
                f"unique={diversity.get('unique_visual_clusters')}/{diversity.get('expected_scenes')}:"
                f"change_ratio={change_ratio:.3f}"
            )
            diversity_penalty = min(
                42.0,
                max(0.0, (0.70 - unique_ratio) * 55.0)
                + max(0.0, (0.65 - change_ratio) * 45.0),
            )
    else:
        warnings.append("visual_diversity_measurement_unavailable")

    if black > 0.22:
        issues.append(f"black_frames_seconds:{black:.3f}")

    if crop and (
        int(crop["width"]) < 1060
        or int(crop["height"]) < 1880
    ):
        warnings.append(
            "black_bar_or_border_risk:"
            f"{crop['width']}x{crop['height']}+{crop['x']}+{crop['y']}"
        )

    score = round(
        max(
            0,
            min(
                100,
                100.0 - len(issues) * 18.0 - len(warnings) * 2.5 - diversity_penalty,
            ),
        ),
        1,
    )
    status = (
        "PASS"
        if not issues and score >= 85
        else "REVIEW"
        if not issues
        else "BLOCK"
    )

    payload = {
        "short_id": SID,
        "version": "1.3_VISUAL_DIVERSITY",
        "visual_qa_score": score,
        "status": status,
        "issues": issues,
        "warnings": warnings,
        "measurements": measurements,
        "assets": assets,
        "limitations": {
            "watermark": (
                "provider/provenance risk only; "
                "no OCR/CV watermark classifier installed"
            ),
            "face_crop": (
                "storyboard/framing risk heuristic; "
                "no face detector installed"
            ),
        },
    }
    atomic(OUT, payload)
    print(
        f"VISUAL QA: {status} | score={score}/100 "
        f"| issues={len(issues)} warnings={len(warnings)} "
        "| video_scan=SINGLE_PASS"
    )
    return 0 if status != "BLOCK" else 1


if __name__ == "__main__":
    raise SystemExit(main())
