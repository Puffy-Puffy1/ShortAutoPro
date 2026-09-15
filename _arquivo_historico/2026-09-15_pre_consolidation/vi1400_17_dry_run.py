#!/usr/bin/env python3

from vi1400_02_artifact_discovery import (
    discover,
)

from vi1400_03_timeline import (
    build_timeline,
)

from vi1400_04_frame_metrics import (
    analyze,
)

from vi1400_05_editorial_qa import (
    run as editorial,
)

from vi1400_06_visual_qa import (
    run as visual,
)

from vi1400_07_subtitle_qa import (
    run as subtitles,
)

from vi1400_08_audio_qa import (
    run_audio,
)

from vi1400_09_temporal_qa import (
    run_temporal,
)

from vi1400_10_rescue_planner import (
    run as rescue,
)

from vi1400_11_operational_guard import (
    run as guard,
)

from vi1400_12_publication_pack import (
    run as publication,
)

from vi1400_13_score_engine import (
    run as score,
)

from vi1400_16_release_manifest import (
    run as manifest,
)


def main():
    discover()

    build_timeline()

    analyze()

    editorial()

    visual()

    subtitles()

    run_audio()

    run_temporal()

    rescue()

    guard()

    publication()

    result = score()

    manifest()


    print(
        (
            "VI1400_DRY_RUN_CERTIFIED"

            if result[
                "ready_for_final_canary"
            ]

            else

            "VI1400_DRY_RUN_SAFE_HOLD"
        )
    )


if __name__ == "__main__":

    main()
