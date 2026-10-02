#!/usr/bin/env python3
"""Canonical Stage 6 multi-round recovery controller.

Runs midia.py incrementally. The selector itself remains authoritative and
fail-closed. Successful scenes are preserved by midia.py's existing incremental
checkpoint; only missing scenes are retried. Search budgets increase gradually
without relaxing MUST verification.
"""
from __future__ import annotations

import json
import os
import subprocess
from subprocess_guard import run_group
from runtime_config import env_int
from runtime_config import env_float
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

from media_emergency_fallback import (
    create_editorial_reuse,
    neutral_slate_scene_numbers,
)
from media_provenance_capture_v1 import write_provenance
import visual_engine_unified

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
REPORT = BASE / "reports" / "media" / f"acquisition_missing_{SID}.json"
MIDIA = BASE / "midia.py"


def read_report() -> dict[str, Any]:
    try:
        data = json.loads(REPORT.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def missing_numbers(report: dict[str, Any]) -> list[int]:
    out = []
    for item in report.get("missing_scenes", []) if isinstance(report.get("missing_scenes"), list) else []:
        if not isinstance(item, dict):
            continue
        try:
            out.append(int(item.get("scene")))
        except Exception:
            pass
    for item in report.get("pending_scenes", []) if isinstance(report.get("pending_scenes"), list) else []:
        try:
            out.append(int(item))
        except Exception:
            pass
    return sorted(set(out))


def total_from(report: dict[str, Any]) -> int:
    try:
        return int(report.get("total", 0) or 0)
    except Exception:
        return 0


def expected_from(report: dict[str, Any]) -> int:
    try:
        return int(report.get("expected", 0) or 0)
    except Exception:
        return 0


def round_env(round_index: int) -> dict[str, str]:
    env = os.environ.copy()
    env["SHORT_ID"] = SID
    env["SAP_MEDIA_INCREMENTAL"] = "1"

    # Increasing retrieval effort only. MUST acceptance rules are untouched.
    rescue_budget = (1, 1, 2)[min(round_index, 2)]
    # The controller deadline must exceed the provider's own bounded
    # request/search budget. The previous 5/6/8s values could terminate the
    # concurrent future while Wikimedia was still inside its legitimate retry
    # window, producing controller timeouts and avoidable scene starvation.
    # Keep the budget bounded on mobile, but give the provider layer enough
    # time to complete one bounded search before the orchestration deadline.
    provider_timeout = (10, 12, 12)[min(round_index, 2)]
    wiki_deadline = (8, 10, 12)[min(round_index, 2)]

    env["SAP_STOCK_RESCUE_MAX_QUERIES"] = str(rescue_budget)
    env["SAP_MUST_RESCUE_MAX_QUERIES"] = str(rescue_budget)
    env["SAP_MEDIA_PROVIDER_RESULT_TIMEOUT"] = str(provider_timeout)
    env["SAP_WIKIMEDIA_SEARCH_DEADLINE"] = str(wiki_deadline)
    # One bounded semantic rescue for unresolved scenes. This broadens
    # retrieval queries only; MUST acceptance remains unchanged and strict.
    # Simplified scene retries remain governed by midia.py scene budgets;
    # do not override their certified recovery contract from the controller.
    env["SAP_VSE4_QUERY_EXPANSION"] = "1"
    env["SAP_VSE4_QUERY_ONLY_ON_EMPTY"] = "1"
    env["SAP_VSE4_QUERY_EXTRA"] = "1"
    env["SAP_MEDIA_RECOVERY_ROUND"] = str(round_index + 1)
    return env


def scene_count_hint() -> int:
    scene_map = BASE / "roteiros" / f"scene_map_{SID}.json"
    try:
        data = json.loads(scene_map.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return len(data)
        if isinstance(data, dict):
            for key in ("scenes", "cenas", "items"):
                value = data.get(key)
                if isinstance(value, list):
                    return len(value)
    except Exception:
        pass
    return env_int("SHORT_QTD_CENAS", 12, 6, 20)


def current_completed_hint() -> int:
    media_dir = BASE / "imagens" / f"short_{SID}"
    expected = scene_count_hint()
    seen: set[int] = set()
    try:
        for path in media_dir.iterdir():
            if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm", ".mkv"}:
                continue
            if not path.stem.startswith("scene_"):
                continue
            try:
                number = int(path.stem.split("_", 1)[1])
                if 1 <= number <= expected and path.is_file() and path.stat().st_size > 1000:
                    seen.add(number)
            except (OSError, ValueError):
                continue
    except OSError:
        return 0
    return len(seen)


def scene_contract() -> tuple[int, list[str]]:
    """Validate the Stage 5 -> Stage 6 scene-map contract before acquisition."""
    path = BASE / "roteiros" / f"scene_map_{SID}.json"
    errors: list[str] = []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return 0, ["SAP-E002:scene_map_missing"]
    except (OSError, json.JSONDecodeError) as exc:
        return 0, [f"SAP-E002:scene_map_invalid:{type(exc).__name__}"]

    if isinstance(raw, dict):
        scenes = next(
            (raw.get(key) for key in ("scenes", "cenas", "items") if isinstance(raw.get(key), list)),
            None,
        )
    elif isinstance(raw, list):
        scenes = raw
    else:
        scenes = None

    if not isinstance(scenes, list) or not scenes:
        return 0, ["SAP-E002:scene_map_empty"]

    expected = len(scenes)
    ids: list[str] = []
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            errors.append(f"SAP-E002:scene_{index:02d}_not_object")
            continue
        raw_id = scene.get("scene_id", scene.get("id", scene.get("scene", index)))
        scene_id = str(raw_id).strip()
        if not scene_id:
            errors.append(f"SAP-E002:scene_{index:02d}_empty_id")
        else:
            ids.append(scene_id)

    if len(ids) != len(set(ids)):
        errors.append("SAP-E002:duplicate_scene_ids")
    return expected, errors


def _probe_asset(path: Path) -> tuple[bool, str]:
    """Cheap corruption/stream check used only after Stage 6 claims success."""
    if not path.is_file():
        return False, "missing"
    try:
        if path.stat().st_size <= 1000:
            return False, "too_small"
    except OSError:
        return False, "stat_failed"

    if path.suffix.lower() not in {".mp4", ".mov", ".webm", ".mkv"}:
        return True, "ok"

    try:
        proc = run_group(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=codec_type,duration",
                "-of", "json", str(path),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
        if proc.returncode != 0:
            return False, f"ffprobe_{proc.returncode}"
        payload = json.loads(proc.stdout or "{}")
        streams = payload.get("streams", []) if isinstance(payload, dict) else []
        if not streams or streams[0].get("codec_type") != "video":
            return False, "no_video_stream"
    except (OSError, ValueError, json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        return False, f"probe_{type(exc).__name__}"
    return True, "ok"


def validate_media_completion(*, ignore_report: bool = False) -> tuple[bool, dict[str, Any]]:
    """Fail closed: a zero exit code is not enough to certify Stage 6.

    ignore_report is used only while reconciling an outer timeout with physical
    media already written to disk. Normal certification still requires report
    consistency.
    """
    expected, contract_errors = scene_contract()
    media_dir = BASE / "imagens" / f"short_{SID}"
    try:
        neutral_scenes = neutral_slate_scene_numbers(media_dir)
    except Exception:
        neutral_scenes = set()
    valid: set[int] = set()
    invalid: list[dict[str, Any]] = []

    if expected <= 0 or contract_errors:
        return False, {
            "expected": expected,
            "valid": 0,
            "missing": list(range(1, expected + 1)) if expected > 0 else [],
            "invalid": invalid,
            "errors": contract_errors,
        }

    try:
        entries = list(media_dir.iterdir())
    except OSError:
        entries = []

    supported = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm", ".mkv"}
    for path in entries:
        if path.suffix.lower() not in supported or not path.stem.startswith("scene_"):
            continue
        suffix = path.stem.split("_", 1)[1]
        try:
            number = int(suffix)
        except ValueError:
            continue
        if number < 1 or number > expected:
            continue
        if number in neutral_scenes:
            invalid.append({
                "scene": number,
                "path": str(path),
                "reason": "neutral_editorial_placeholder",
            })
            continue
        ok, reason = _probe_asset(path)
        if ok:
            valid.add(number)
        else:
            invalid.append({"scene": number, "path": str(path), "reason": reason})

    missing = sorted(set(range(1, expected + 1)) - valid)
    report = read_report()
    report_missing = missing_numbers(report)
    report_expected = expected_from(report)
    report_total = total_from(report)
    report_errors: list[str] = []
    if report and not ignore_report:
        if report_expected not in {0, expected}:
            report_errors.append(
                f"SAP-E002:report_expected_mismatch:{report_expected}!={expected}"
            )
        if report_missing:
            report_errors.append(
                "SAP-E003:report_still_missing:" + ",".join(map(str, report_missing))
            )
        if report_total and report_total < expected:
            report_errors.append(
                f"SAP-E003:report_total_incomplete:{report_total}/{expected}"
            )

    errors = contract_errors + report_errors
    ok = not missing and not invalid and not errors
    return ok, {
        "expected": expected,
        "valid": len(valid),
        "missing": missing,
        "invalid": invalid,
        "neutral_editorial_scenes": sorted(neutral_scenes),
        "errors": errors,
    }


def report_signature() -> tuple[int, int, int] | None:
    try:
        stat = REPORT.stat()
        return stat.st_ino, stat.st_mtime_ns, stat.st_size
    except OSError:
        return None


def round_timeout_seconds() -> tuple[int, int]:
    expected = scene_count_hint()
    report = read_report()
    pending = missing_numbers(report)
    if pending:
        remaining = len(pending)
    else:
        remaining = max(1, expected - current_completed_hint())

    # Keep the controller aligned with midia.py. The selector uses an 18s
    # default per-scene budget; the previous 12s outer budget could kill Stage 6
    # before its own emergency completion path was reached.
    base = env_int("SAP_MEDIA_ROUND_TIMEOUT", 60, 30, 195)
    scene_budget = env_float("SAP_MEDIA_SCENE_BUDGET_SECONDS", 18.0, 10.0, 35.0)
    grace = env_int("SAP_MEDIA_ROUND_GRACE_SECONDS", 12, 6, 30)
    dynamic = int(remaining * scene_budget + grace)
    # Two worst-case rounds stay below main.py's 420s Stage 6 timeout.
    return max(30, min(max(base, dynamic), 195)), remaining


def _scene_rows() -> list[dict[str, Any]]:
    path = BASE / "roteiros" / f"scene_map_{SID}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    if isinstance(data, dict):
        rows = data.get("scenes", [])
    elif isinstance(data, list):
        rows = data
    else:
        rows = []
    return [row for row in rows if isinstance(row, dict)]


def _clear_missing_report() -> None:
    try:
        REPORT.unlink(missing_ok=True)
    except OSError:
        pass


def _atomic_json(path: Path, payload: dict[str, Any]) -> None:
    import tempfile
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


def final_editorial_completion(missing: list[int]) -> bool:
    """Finish a small timed-out tail with audited non-evidentiary media."""
    missing = sorted({int(x) for x in missing if int(x) > 0})
    if not missing:
        return False

    max_scenes = env_int("SAP_MEDIA_FINAL_EDITORIAL_MAX", 3, 0, 6)
    if max_scenes <= 0 or len(missing) > max_scenes:
        print(
            "MEDIA_STAGE_RUNTIME=FINAL_EDITORIAL_SKIP "
            f"missing={','.join(map(str, missing))} max={max_scenes}"
        )
        return False

    media_dir = BASE / "imagens" / f"short_{SID}"
    media_dir.mkdir(parents=True, exist_ok=True)
    rows = _scene_rows()
    completed: list[int] = []
    failures: list[dict[str, Any]] = []

    print(
        "MEDIA_STAGE_RUNTIME=FINAL_EDITORIAL_START "
        f"missing={','.join(map(str, missing))}"
    )

    for number in missing:
        # Editorial reuse is only a bounded visual-continuity fallback. It must
        # never satisfy a scene whose contract still contains explicit MUST
        # evidence requirements; those scenes require a fresh verified asset.
        if 1 <= number <= len(rows):
            scene_contract_row = rows[number - 1]
            raw_must = scene_contract_row.get("must_have", []) if isinstance(scene_contract_row, dict) else []
            explicit_must = (
                [str(item).strip() for item in raw_must]
                if isinstance(raw_must, (list, tuple, set))
                else [str(raw_must).strip()] if raw_must else []
            )
            explicit_must = [item for item in explicit_must if item]
            if explicit_must:
                failures.append({
                    "scene": number,
                    "reason": "explicit_must_requires_verified_fresh_asset",
                    "must_have": explicit_must,
                })
                print(
                    "MEDIA_STAGE_RUNTIME=FINAL_EDITORIAL_BLOCKED "
                    f"scene={number} reason=EXPLICIT_MUST_REQUIRES_VERIFIED_ASSET "
                    f"must={','.join(explicit_must)}"
                )
                continue

        try:
            candidate = create_editorial_reuse(
                media_dir,
                number,
                allow_neutral=False,
            )
        except Exception as exc:
            candidate = None
            failures.append({
                "scene": number,
                "reason": f"{type(exc).__name__}:{str(exc)[:160]}",
            })
            continue

        path = Path(str((candidate or {}).get("local_path", "") or ""))
        if candidate and candidate.get("neutral_slate"):
            failures.append({
                "scene": number,
                "reason": "neutral_editorial_placeholder_rejected",
            })
            continue
        ok, reason = _probe_asset(path)
        if not candidate or not ok:
            failures.append({
                "scene": number,
                "reason": reason or "fallback_failed",
            })
            continue

        try:
            write_provenance(
                candidate,
                str(path),
                method="media_stage_runtime_final_editorial",
            )
        except Exception:
            pass

        if 1 <= number <= len(rows):
            scene = rows[number - 1]
            try:
                visual_engine_unified.note_commit_runtime(
                    candidate,
                    {
                        "SHORT_ID": SID,
                        "numero": number,
                        "scene": number,
                        "cena": scene,
                        "busca": str(scene.get("query", "") or ""),
                        "segmento": str(scene.get("segment", "") or ""),
                    },
                )
            except Exception:
                pass

        completed.append(number)
        print(
            "MEDIA_STAGE_RUNTIME=FINAL_EDITORIAL_SCENE "
            f"scene={number} status=PASS truth_claim=NONE"
        )

    audit = {
        "short_id": SID,
        "version": "STAGE6_FINAL_EDITORIAL_1.0",
        "requested": missing,
        "completed": completed,
        "failures": failures,
        "truth_claim": "NONE",
        "policy": "BOUNDED_SOURCE_BASED_EDITORIAL_ONLY_NO_NEUTRAL_PLACEHOLDERS",
    }
    _atomic_json(
        BASE / "reports" / "media" / f"final_editorial_completion_{SID}.json",
        audit,
    )

    if failures or completed != missing:
        print(
            "MEDIA_STAGE_RUNTIME=FINAL_EDITORIAL_FAIL "
            f"completed={','.join(map(str, completed)) or '-'} "
            f"failed={','.join(str(x['scene']) for x in failures) or '-'}"
        )
        return False

    physically_ready, physical = validate_media_completion(ignore_report=True)
    if not physically_ready:
        print(
            "MEDIA_STAGE_RUNTIME=FINAL_EDITORIAL_INVALID "
            f"valid={physical.get('valid')}/{physical.get('expected')} "
            f"missing={','.join(map(str, physical.get('missing', []))) or '-'}"
        )
        return False

    _clear_missing_report()
    certified, final = validate_media_completion()
    if certified:
        print(
            "MEDIA_STAGE_RUNTIME=FINAL_EDITORIAL_PASS "
            f"scenes={final['valid']}/{final['expected']}"
        )
        return True

    print(
        "MEDIA_STAGE_RUNTIME=FINAL_EDITORIAL_CERT_FAIL "
        f"errors={'|'.join(final.get('errors', [])) or '-'}"
    )
    return False


def main() -> int:
    """Compatibility entrypoint: execute Media Engine V2 only."""
    if not SID:
        print("MEDIA_STAGE_RUNTIME=BLOCKED reason=SHORT_ID_EMPTY")
        return 1
    engine = BASE / "media_engine_v2.py"
    if not engine.is_file():
        print(f"MEDIA_STAGE_RUNTIME=BLOCKED reason=MEDIA_ENGINE_V2_MISSING path={engine}")
        return 1
    env = os.environ.copy()
    env["SHORTAUTOPRO_BASE"] = str(BASE)
    env["SHORT_ID"] = SID
    print(
        "MEDIA_STAGE_RUNTIME=DEPRECATED_SHIM "
        f"delegate=media_engine_v2.py short_id={SID}"
    )
    proc = run_group(
        [sys.executable, str(engine), "--short-id", SID],
        cwd=str(BASE),
        env=env,
        check=False,
        timeout=env_int("SAP_STAGE_TIMEOUT_MEDIA_ENGINE_V2_SECONDS", 900, 180, 1800),
    )
    print(
        "MEDIA_STAGE_RUNTIME=V2_RESULT "
        f"returncode={proc.returncode} short_id={SID}"
    )
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
