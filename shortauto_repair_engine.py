#!/usr/bin/env python3
"""Bounded, evidence-driven repair loop for ShortAutoPro.

The engine coordinates existing repair-capable modules. It never weakens gates,
edits factual narration, or bypasses strict MUST verification.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SID = os.getenv("SHORT_ID", "").strip()
R = BASE / "roteiros"
M = BASE / "manifests"
E = BASE / "reports" / "evolution"
OUT = BASE / "reports" / "repair"


def now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def load(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


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


def quality_snapshot(sid: str, scenes: list[int]) -> dict[str, Any]:
    visual = load(R / f"visual_score_{sid}.json")
    continuity = load(R / f"visual_continuity_{sid}.json")
    media = load(R / f"media_quality_{sid}.json")
    rows = visual.get("scenes", []) if isinstance(visual.get("scenes"), list) else []
    wanted = set(int(x) for x in scenes)
    selected_scores = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            number = int(row.get("scene"))
            score = float(row.get("visual_score", 0) or 0)
        except (TypeError, ValueError):
            continue
        if number in wanted:
            selected_scores.append(score)
    target_visual = (
        sum(selected_scores) / len(selected_scores)
        if selected_scores
        else float(visual.get("visual_score", 0) or 0)
    )
    continuity_score = float(continuity.get("visual_continuity_score", 0) or 0)
    repair_scenes = continuity.get("repair_scenes", []) if isinstance(continuity.get("repair_scenes"), list) else []
    weak_scenes = visual.get("weak_scenes", []) if isinstance(visual.get("weak_scenes"), list) else []
    return {
        "objective": round(0.60 * target_visual + 0.40 * continuity_score, 3),
        "target_visual": round(target_visual, 3),
        "continuity": round(continuity_score, 3),
        "repair_count": len(repair_scenes),
        "weak_count": len(weak_scenes),
        "media_status": str(media.get("status", "")).upper(),
    }


def backup_targeted_media(sid: str, scenes: list[int]) -> dict[str, Any]:
    temp_root = BASE / "temp"
    temp_root.mkdir(parents=True, exist_ok=True)
    backup_dir = Path(tempfile.mkdtemp(prefix=f"repair_{sid}_", dir=str(temp_root)))
    media_dir = BASE / "imagens" / f"short_{sid}"
    media_backup = backup_dir / "media"
    media_backup.mkdir(parents=True, exist_ok=True)
    saved_media = []
    for number in sorted(set(int(x) for x in scenes)):
        for path in media_dir.glob(f"scene_{number:02d}.*"):
            if path.is_file():
                target = media_backup / path.name
                shutil.copy2(path, target)
                saved_media.append(path.name)

    tracked = [
        R / f"media_quality_{sid}.json",
        R / f"visual_score_{sid}.json",
        R / f"visual_continuity_{sid}.json",
        R / f"visual_intelligence_6_{sid}.json",
        media_dir / ".editorial_reuse_index.json",
    ]
    report_backup = backup_dir / "reports"
    report_backup.mkdir(parents=True, exist_ok=True)
    reports: list[dict[str, Any]] = []
    for index, path in enumerate(tracked):
        existed = path.is_file()
        copy_name = f"{index:02d}_{path.name}"
        if existed:
            shutil.copy2(path, report_backup / copy_name)
        reports.append({
            "path": str(path),
            "existed": existed,
            "copy": copy_name,
        })
    return {
        "dir": str(backup_dir),
        "media_dir": str(media_dir),
        "media": saved_media,
        "reports": reports,
        "scenes": sorted(set(int(x) for x in scenes)),
    }


def restore_targeted_media(snapshot: dict[str, Any]) -> None:
    backup_dir = Path(str(snapshot["dir"]))
    media_dir = Path(str(snapshot["media_dir"]))
    media_backup = backup_dir / "media"
    for number in snapshot.get("scenes", []):
        for path in media_dir.glob(f"scene_{int(number):02d}.*"):
            if path.is_file():
                path.unlink()
    for path in media_backup.iterdir():
        if path.is_file():
            shutil.copy2(path, media_dir / path.name)

    report_backup = backup_dir / "reports"
    for item in snapshot.get("reports", []):
        if not isinstance(item, dict):
            continue
        path = Path(str(item.get("path", "")))
        existed = bool(item.get("existed"))
        copy_name = str(item.get("copy", ""))
        if existed:
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(report_backup / copy_name, path)
        else:
            try:
                path.unlink(missing_ok=True)
            except OSError:
                pass


def discard_backup(snapshot: dict[str, Any]) -> None:
    try:
        shutil.rmtree(str(snapshot.get("dir", "")), ignore_errors=True)
    except Exception:
        pass


def plan(sid: str) -> dict[str, Any]:
    release = load(M / f"{sid}_release.json")
    media = load(R / f"media_quality_{sid}.json")
    retention = load(R / f"retention_{sid}.json")
    visual = load(R / f"visual_score_{sid}.json")
    continuity = load(R / f"visual_continuity_{sid}.json")
    caption = load(R / f"caption_layout_{sid}.json")
    audio = load(E / f"final_audio_{sid}.json")
    actions: list[dict[str, Any]] = []

    media_critical = media.get("critical", []) if isinstance(media.get("critical"), list) else []
    media_warnings = media.get("warnings", []) if isinstance(media.get("warnings"), list) else []
    refresh_commands = [
        [sys.executable, "media_stage_runtime.py"],
        [sys.executable, "media_master_gate.py"],
        [sys.executable, "visual_score_engine.py"],
        [sys.executable, "visual_continuity_engine.py", "--selected"],
    ]

    if str(media.get("status", "")).upper() == "BLOCK" or media_critical:
        actions.append({
            "id": "media_reacquire",
            "reason": "media_gate_block",
            "commands": refresh_commands,
            "risk": "bounded_network_retry",
        })
    else:
        low_resolution_scenes: set[int] = set()
        for warning in media_warnings:
            match = __import__("re").search(
                r"low_resolution:scene_(\d+)",
                str(warning),
                flags=__import__("re").I,
            )
            if match:
                low_resolution_scenes.add(int(match.group(1)))
        if low_resolution_scenes:
            actions.append({
                "id": "media_quality_refresh",
                "reason": "low_resolution_warning",
                "force_scenes": sorted(low_resolution_scenes),
                "commands": refresh_commands,
                "risk": "bounded_network_retry",
            })

    if float(retention.get("retention_score", 100) or 0) < float(retention.get("threshold", 78) or 78):
        actions.append({
            "id": "retention_repair",
            "reason": "retention_below_threshold",
            "commands": [[sys.executable, "retention_engine.py", "--repair"]],
            "risk": "edit_plan_only",
        })

    weak = visual.get("weak_scenes", []) if isinstance(visual.get("weak_scenes"), list) else []
    weak_numbers = sorted({
        int(x) for x in weak
        if str(x).isdigit() and int(x) > 0
    })
    continuity_targets = continuity.get("repair_scenes", []) if isinstance(continuity.get("repair_scenes"), list) else []
    continuity_numbers = sorted({
        int(x) for x in continuity_targets
        if str(x).isdigit() and int(x) > 0
    })

    targeted_media = sorted(set(weak_numbers) | set(continuity_numbers))
    has_media_action = any(str(item.get("id", "")).startswith("media_") for item in actions)
    if targeted_media and not has_media_action:
        actions.append({
            "id": "visual_continuity_repair" if continuity_numbers else "media_quality_refresh",
            "reason": (
                "selected_continuity_repair:"
                + ",".join(map(str, continuity_numbers))
                if continuity_numbers
                else "weak_visual_scenes:" + ",".join(map(str, weak_numbers))
            ),
            "force_scenes": targeted_media,
            "commands": refresh_commands,
            "risk": "bounded_targeted_media_retry",
        })

    if weak_numbers:
        actions.append({
            "id": "professional_edit_repair",
            "reason": f"weak_visual_scenes:{','.join(map(str, weak_numbers))}",
            "commands": [[sys.executable, "professional_edit_repair.py"]],
            "risk": "edit_plan_only",
        })

    caption_status = str(caption.get("status", "")).upper()
    if caption_status == "BLOCK":
        actions.append({
            "id": "caption_repair",
            "reason": "caption_layout_block",
            "commands": [
                [sys.executable, "professional_caption_director.py"],
                [sys.executable, "caption_layout_guard.py"],
            ],
            "risk": "captions_only",
        })

    if str(audio.get("status", "")).upper() == "BLOCK":
        actions.append({
            "id": "audio_remaster",
            "reason": "audio_master_block",
            "commands": [[sys.executable, "audio_finalizer.py"]],
            "risk": "audio_master_only",
        })

    release_actions = release.get("repair_actions", []) if isinstance(release.get("repair_actions"), list) else []
    if any("repair_pacing" in str(x) for x in release_actions) and not any(x["id"] == "retention_repair" for x in actions):
        actions.append({
            "id": "retention_repair",
            "reason": "release_gate_repair_pacing",
            "commands": [[sys.executable, "retention_engine.py", "--repair"]],
            "risk": "edit_plan_only",
        })
    if (
        any("replace_weak_or_generic_media" in str(x) for x in release_actions)
        and not any(
            x["id"].startswith("media_") or x["id"] == "visual_continuity_repair"
            for x in actions
        )
    ):
        targets = sorted(set(weak_numbers) | set(continuity_numbers))
        action = {
            "id": "media_reacquire",
            "reason": "release_gate_media_repair",
            "commands": refresh_commands,
            "risk": "bounded_network_retry",
        }
        if targets:
            action["force_scenes"] = targets
        actions.append(action)

    return {
        "short_id": sid,
        "version": "REPAIR_ENGINE_1.1_TARGETED_MEDIA",
        "generated_at": now(),
        "policy": {
            "max_cycles_default": 1,
            "strict_must_can_never_be_relaxed": True,
            "semantic_text_can_never_be_rewritten": True,
            "fail_closed": True,
        },
        "actions": actions,
        "action_count": len(actions),
    }


def execute(sid: str, max_cycles: int) -> tuple[int, dict[str, Any]]:
    proposal = plan(sid)
    history = []
    max_cycles = max(1, min(max_cycles, 2))
    env = os.environ.copy()
    env["SHORT_ID"] = sid
    for cycle in range(1, max_cycles + 1):
        if not proposal["actions"]:
            break
        cycle_log = {"cycle": cycle, "actions": []}
        for action in proposal["actions"]:
            action_log = {"id": action["id"], "reason": action["reason"], "commands": [], "status": "PASS"}
            action_env = env.copy()
            force_scenes = action.get("force_scenes", [])
            transaction = None
            before_quality = None
            if isinstance(force_scenes, list) and force_scenes:
                force_scenes = sorted(set(int(x) for x in force_scenes))
                action_env["SAP_MEDIA_FORCE_SCENES"] = ",".join(
                    str(x) for x in force_scenes
                )
                action_log["force_scenes"] = list(force_scenes)
                before_quality = quality_snapshot(sid, force_scenes)
                transaction = backup_targeted_media(sid, force_scenes)
                action_log["quality_before"] = before_quality
            for command in action["commands"]:
                command_name = Path(str(command[1] if len(command) > 1 else command[0])).name
                if command_name in {"video_professional.py", "v6_professional.py", "audio_finalizer.py"}:
                    timeout_seconds = int(os.getenv("SAP_REPAIR_RENDER_TIMEOUT", "900") or 900)
                elif command_name == "media_stage_runtime.py":
                    timeout_seconds = int(os.getenv("SAP_REPAIR_MEDIA_TIMEOUT", "420") or 420)
                else:
                    timeout_seconds = int(os.getenv("SAP_REPAIR_ACTION_TIMEOUT", "300") or 300)
                timeout_seconds = max(60, min(timeout_seconds, 1800))
                try:
                    proc = subprocess.run(
                        command,
                        cwd=BASE,
                        env=action_env,
                        check=False,
                        timeout=timeout_seconds,
                    )
                    returncode = proc.returncode
                except subprocess.TimeoutExpired:
                    returncode = 124
                    action_log["timeout_seconds"] = timeout_seconds
                    print(
                        "SHORTAUTO_REPAIR_ACTION_TIMEOUT "
                        f"action={action['id']} command={command_name} "
                        f"limit={timeout_seconds}s"
                    )
                action_log["commands"].append(
                    {
                        "command": command,
                        "returncode": returncode,
                        "timeout_seconds": timeout_seconds,
                    }
                )
                if returncode not in {0, 20}:
                    action_log["status"] = "FAIL"
                    break

            if transaction is not None:
                if action_log["status"] == "PASS":
                    after_quality = quality_snapshot(sid, force_scenes)
                    action_log["quality_after"] = after_quality
                    min_gain = float(os.getenv("SAP_REPAIR_MIN_QUALITY_GAIN", "1.5") or 1.5)
                    improved = (
                        after_quality["media_status"] == "PASS"
                        and (
                            after_quality["objective"] >= before_quality["objective"] + min_gain
                            or after_quality["repair_count"] < before_quality["repair_count"]
                            or after_quality["weak_count"] < before_quality["weak_count"]
                        )
                    )
                    if improved:
                        action_log["acceptance"] = "IMPROVED"
                        discard_backup(transaction)
                    else:
                        restore_targeted_media(transaction)
                        discard_backup(transaction)
                        action_log["status"] = "REVERTED"
                        action_log["acceptance"] = "NO_MEASURED_IMPROVEMENT"
                        print(
                            "SHORTAUTO_REPAIR=REVERTED "
                            f"action={action['id']} scenes={','.join(map(str, force_scenes))} "
                            f"before={before_quality['objective']:.1f} "
                            f"after={after_quality['objective']:.1f}"
                        )
                else:
                    restore_targeted_media(transaction)
                    discard_backup(transaction)
                    action_log["acceptance"] = "COMMAND_FAILED_ROLLBACK"

            cycle_log["actions"].append(action_log)
            if action_log["status"] == "FAIL":
                history.append(cycle_log)
                result = {**proposal, "status": "FAIL", "history": history, "finished_at": now()}
                atomic(OUT / f"repair_{sid}.json", result)
                print(f"SHORTAUTO_REPAIR=FAIL action={action['id']}")
                return 1, result
        history.append(cycle_log)
        proposal = plan(sid)
        if not proposal["actions"]:
            break
        if cycle >= max_cycles:
            break
    status = "PASS" if not proposal["actions"] else "HOLD"
    result = {**proposal, "status": status, "history": history, "finished_at": now()}
    atomic(OUT / f"repair_{sid}.json", result)
    print(f"SHORTAUTO_REPAIR={status} remaining={len(proposal['actions'])} cycles={len(history)}")
    return (0 if status == "PASS" else 20), result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--short-id", default=SID)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--max-cycles", type=int, default=1)
    args = parser.parse_args()
    sid = str(args.short_id or "").strip()
    if not sid:
        print("ERRO REPAIR ENGINE: SHORT_ID vazio")
        return 1
    if not args.execute:
        proposal = plan(sid)
        atomic(OUT / f"repair_plan_{sid}.json", proposal)
        print(json.dumps(proposal, ensure_ascii=False, indent=2))
        return 0
    return execute(sid, args.max_cycles)[0]


if __name__ == "__main__":
    raise SystemExit(main())
