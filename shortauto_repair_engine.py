#!/usr/bin/env python3
"""Bounded, evidence-driven repair loop for ShortAutoPro.

The engine coordinates existing repair-capable modules. It never weakens gates,
edits factual narration, or bypasses strict MUST verification.
"""
from __future__ import annotations

import argparse
import json
import os
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
            if isinstance(force_scenes, list) and force_scenes:
                action_env["SAP_MEDIA_FORCE_SCENES"] = ",".join(
                    str(int(x)) for x in force_scenes
                )
                action_log["force_scenes"] = list(force_scenes)
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
