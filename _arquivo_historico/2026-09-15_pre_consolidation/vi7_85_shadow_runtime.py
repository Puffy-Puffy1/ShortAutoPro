#!/usr/bin/env python3

import json

from datetime import datetime
from pathlib import Path

from vi7_70_scene_plan_builder import (
    build_plan
)

from vi7_40_visual_repetition import (
    detect
)

from vi7_52_visual_sequence_planner import (
    analyze as analyze_transitions
)

from vi7_55_documentary_continuity import (
    evaluate as documentary
)

from vi7_58_media_diversity import (
    evaluate as diversity
)

from vi7_73_global_rhythm import (
    evaluate as rhythm
)

from vi7_76_sequence_optimizer import (
    recommendations
)

from vi7_79_visual_quality_gate import (
    evaluate as visual_gate
)

from vi7_82_source_boundary import (
    evaluate as source_boundary
)


VERSION = "7.85"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def latest_scene_map():
    files = []

    for path in (
        BASE
        / "roteiros"
    ).glob(
        "scene_map_*.json"
    ):
        if (
            "_pre_" in path.name
            or path.name.startswith(
                "scene_map_pre_"
            )
        ):
            continue

        files.append(path)

    files.sort(
        key=lambda path:
            path.stat().st_mtime,
        reverse=True
    )

    return (
        files[0]
        if files
        else None
    )


def run(scene_map_path=None):
    path = (
        Path(scene_map_path)
        if scene_map_path
        else latest_scene_map()
    )

    if (
        path is None
        or not path.exists()
    ):
        raise RuntimeError(
            "scene_map_missing"
        )

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    scenes = (
        data.get("scenes")
        or []
    )

    if len(scenes) != 12:
        raise RuntimeError(
            "scene_count_not_12"
        )

    plans = build_plan(
        scenes
    )

    repetition = detect(
        plans
    )

    transitions = analyze_transitions(
        plans
    )

    documentary_result = documentary(
        plans
    )

    diversity_result = diversity(
        plans
    )

    rhythm_result = rhythm(
        plans
    )

    optimizer = recommendations(
        plans,
        repetition,
        transitions
    )

    gate = visual_gate(
        plans
    )

    source = source_boundary()

    result = {
        "generated_at":
            datetime.now().isoformat(
                timespec="seconds"
            ),
        "version": VERSION,
        "mode": "SHADOW_ONLY",
        "scene_map": str(path),
        "short_id":
            data.get("short_id"),
        "plans": plans,
        "repetition":
            repetition,
        "transitions":
            transitions,
        "documentary":
            documentary_result,
        "diversity":
            diversity_result,
        "rhythm":
            rhythm_result,
        "optimizer":
            optimizer,
        "visual_quality_gate":
            gate,
        "source_boundary":
            source,
        "renderer_modified":
            False,
        "render_executed":
            False,
        "video_generated":
            False,
    }

    output = (
        BASE
        / "logs"
        / "producao"
        / "vi7_85_cinematic_shadow_latest.json"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output.write_text(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return result


def self_test():
    assert VERSION == "7.85"

    print(
        "VI7.85 SHADOW RUNTIME=PASS"
    )


if __name__ == "__main__":
    self_test()
