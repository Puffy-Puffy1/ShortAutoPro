#!/usr/bin/env python3
"""Unified ShortAutoPro confidence score and fail-closed release decision."""
from __future__ import annotations

import argparse
import json
import math
import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
R = BASE / "roteiros"
M = BASE / "manifests"
E = BASE / "reports" / "evolution"
OUT = M / f"{SID}_release.json"


def load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def num(value: Any, default: float = 0.0) -> float:
    try:
        parsed = float(value)
        return parsed if math.isfinite(parsed) else default
    except (TypeError, ValueError):
        return default


def atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def clamp(value: float) -> float:
    return round(max(0, min(100, value)), 1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--enforce", action="store_true")
    args = parser.parse_args()

    paths = {
        "retention": R / f"retention_{SID}.json",
        "visual_continuity": R / f"visual_continuity_{SID}.json",
        "visual_score": R / f"visual_score_{SID}.json",
        "visual_qa": E / f"visual_qa_{SID}.json",
        "final_audio": E / f"final_audio_{SID}.json",
        "professional_quality": M / f"{SID}_professional.json",
        "final_quality": M / f"{SID}_quality.json",
        "media_quality": R / f"media_quality_{SID}.json",
        "professional_caption": R / f"pro_caption_{SID}.json",
        "caption_layout": R / f"caption_layout_{SID}.json",
        "visual_director": R / f"visual_director_{SID}.json",
    }
    reports = {name: load(path) for name, path in paths.items()}

    retention = reports["retention"]
    continuity = reports["visual_continuity"]
    vscore = reports["visual_score"]
    vqa = reports["visual_qa"]
    audio = reports["final_audio"]
    pro = reports["professional_quality"]
    legacy = reports["final_quality"]
    media = reports["media_quality"]
    caption = reports["professional_caption"]
    caption_layout = reports["caption_layout"]
    vd = reports["visual_director"]

    critical: list[str] = []
    missing = [name for name, path in paths.items() if not path.is_file() or not reports[name]]
    critical.extend(f"required_report_missing:{name}" for name in missing)

    factual_ok = legacy.get("approved") is True
    if not factual_ok:
        critical.append("legacy_final_quality_not_approved")

    vqa_status = str(vqa.get("status", "MISSING")).upper()
    if vqa_status == "BLOCK":
        critical.append("visual_qa_block")
    elif vqa and vqa_status not in {"PASS", "REVIEW"}:
        critical.append(f"visual_qa_invalid_status:{vqa_status}")

    audio_status = str(audio.get("status", "MISSING")).upper()
    if audio and audio_status != "PASS":
        critical.append(f"audio_master_not_pass:{audio_status}")

    media_status = str(media.get("status", "MISSING")).upper()
    if media and (media_status != "PASS" or bool(media.get("critical"))):
        critical.append(f"media_quality_not_pass:{media_status}")

    caption_layout_status = str(caption_layout.get("status", "PASS")).upper()
    if caption_layout and caption_layout_status == "BLOCK":
        critical.append("caption_layout_block")

    components_data = retention.get("components", {}) if isinstance(retention.get("components"), dict) else {}
    script = clamp(
        (
            num(components_data.get("hook"), 0)
            + num(components_data.get("language"), 0)
            + num(components_data.get("payoff"), 0)
        ) / 3
    )
    media_score = num(pro.get("components", {}).get("media"), num(media.get("score"), 0)) if isinstance(pro.get("components"), dict) else num(media.get("score"), 0)
    visual = clamp(
        0.18 * num(vd.get("visual_director_score"), 0)
        + 0.20 * num(continuity.get("visual_continuity_score"), 0)
        + 0.37 * num(vscore.get("visual_score"), 0)
        + 0.25 * num(vqa.get("visual_qa_score"), 0)
    )

    if audio:
        after = audio.get("after", {}) if isinstance(audio.get("after"), dict) else {}
        target = audio.get("target", {}) if isinstance(audio.get("target"), dict) else {}
        loudness_error = abs(num(after.get("lufs"), -99) - num(target.get("lufs"), -14))
        true_peak_over = max(0, num(after.get("true_peak_db"), 99) - num(target.get("true_peak_db"), -1.5))
        audio_score = clamp(100 - loudness_error * 12 - true_peak_over * 18)
    else:
        audio_score = 0.0

    pro_components = pro.get("components", {}) if isinstance(pro.get("components"), dict) else {}
    subtitle_base = num(caption.get("score"), num(pro_components.get("captions"), 0))
    layout_score = num(caption_layout.get("score"), 0)
    subtitle = clamp(0.75 * subtitle_base + 0.25 * layout_score)
    retention_score = clamp(num(retention.get("retention_score"), 0))
    technical = clamp(num(pro_components.get("technical"), 0))

    components = {
        "script_score": script,
        "media_score": clamp(media_score),
        "visual_score": visual,
        "audio_score": audio_score,
        "subtitle_score": subtitle,
        "retention_score": retention_score,
        "technical_score": technical,
    }
    weights = {
        "script_score": 0.14,
        "media_score": 0.16,
        "visual_score": 0.18,
        "audio_score": 0.12,
        "subtitle_score": 0.10,
        "retention_score": 0.15,
        "technical_score": 0.15,
    }
    score = round(sum(components[key] * weights[key] for key in weights), 1)

    if critical:
        decision = "BLOCK"
    elif score >= 90:
        decision = "PUBLISH"
    elif score >= 80:
        decision = "ACCEPTABLE"
    elif score >= 70:
        decision = "REPAIR"
    else:
        decision = "BLOCK"

    actions: list[str] = []
    weak_scenes = vscore.get("weak_scenes", []) if isinstance(vscore.get("weak_scenes"), list) else []
    if components["media_score"] < 80 or components["visual_score"] < 80:
        actions.append("replace_weak_or_generic_media" + (":" + ",".join(map(str, weak_scenes)) if weak_scenes else ""))
    if components["retention_score"] < 80:
        actions.append("repair_pacing")
    if components["audio_score"] < 90:
        actions.append("remaster_audio")
    if components["subtitle_score"] < 85:
        actions.append("repair_caption_layout")

    payload = {
        "short_id": SID,
        "version": "RELEASE_GATE_3_1",
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "shortautopro_score": score,
        "decision": decision,
        "components": components,
        "weights": weights,
        "critical": critical,
        "required_reports": {name: str(path.relative_to(BASE)) for name, path in paths.items()},
        "missing_reports": missing,
        "repair_actions": actions,
        "visual_multiscore": vscore,
    }
    atomic(OUT, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))

    if args.enforce and decision == "BLOCK":
        return 1
    if args.enforce and decision == "REPAIR":
        return 20
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
