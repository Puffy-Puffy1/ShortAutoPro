#!/usr/bin/env python3

import json
import re
from pathlib import Path


BASE = Path.home() / "ShortAutoPro"

DISCOVERY = json.loads(
    (
        BASE
        / "temp/vi1310/discovery.json"
    ).read_text(
        encoding="utf-8"
    )
)

OUT = (
    BASE
    / "temp/vi1330/subtitle_safety.json"
)


def main():
    subtitle = Path(
        DISCOVERY[
            "subtitle"
        ]
    )


    text = subtitle.read_text(
        encoding="utf-8",
        errors="replace"
    )


    events = []


    if subtitle.suffix.lower() == ".ass":

        for line in text.splitlines():

            if line.startswith(
                "Dialogue:"
            ):

                parts = line.split(
                    ",",
                    9
                )


                if len(
                    parts
                ) >= 10:

                    events.append(
                        parts[
                            9
                        ]
                    )


    elif subtitle.suffix.lower() == ".srt":

        blocks = re.split(
            r"\n\s*\n",
            text
        )


        for block in blocks:

            lines = [
                line.strip()

                for line in block.splitlines()

                if line.strip()
            ]


            content = [
                line

                for line in lines

                if (
                    "-->"
                    not in line
                    and
                    not line.isdigit()
                )
            ]


            if content:

                events.append(
                    " ".join(
                        content
                    )
                )


    visible_lengths = [
        len(
            re.sub(
                r"\{[^}]*\}",
                "",
                event
            )
        )

        for event in events
    ]


    maximum = max(
        visible_lengths,
        default=0
    )


    checks = {
        "subtitle_file_exists":
            subtitle.exists(),

        "subtitle_events_present":
            len(
                events
            )
            > 0,

        "maximum_event_length_reasonable":
            maximum
            <= 90,
    }


    failed = [
        key

        for key, value in checks.items()

        if value is not True
    ]


    output = {
        "subtitle":
            str(
                subtitle
            ),

        "events":
            len(
                events
            ),

        "maximum_visible_chars":
            maximum,

        "checks":
            checks,

        "failed":
            failed,
    }


    OUT.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


    print()
    print(
        "=============================================="
    )
    print(
        " VI1330 SUBTITLE SAFETY"
    )
    print(
        "=============================================="
    )

    print(
        "EVENTS:",
        len(
            events
        )
    )
    print(
        "MAX CHARS:",
        maximum
    )
    print(
        "FAILED:",
        failed
    )


    if failed:

        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()
