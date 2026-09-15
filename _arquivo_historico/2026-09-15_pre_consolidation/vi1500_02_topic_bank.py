#!/usr/bin/env python3

import json
import os

from vi1500_01_common import (
    BASE,
    save_json,
)


DEFAULT_TOPICS = [
    {
        "label":
            "A",

        "domain":
            "HISTORICAL_MYSTERY",

        "topic":
            "O desaparecimento da colônia de Roanoke"
    },

    {
        "label":
            "B",

        "domain":
            "HISTORICAL_EVENT",

        "topic":
            "O desastre do dirigível Hindenburg em 1937"
    },

    {
        "label":
            "C",

        "domain":
            "SCIENCE_CONCEPT",

        "topic":
            "O paradoxo de Fermi e o silêncio do universo"
    }
]


def topics():
    raw = (
        os.environ.get(
            "VI1500_TOPICS_JSON",
            ""
        )
        .strip()
    )


    if raw:
        values = json.loads(
            raw
        )

        if not isinstance(
            values,
            list
        ):
            raise ValueError(
                "VI1500_TOPICS_JSON must be a list"
            )

        result = []

        for index, value in enumerate(
            values[:3],
            1
        ):
            if isinstance(
                value,
                str
            ):
                result.append({
                    "label":
                        chr(
                            64 + index
                        ),

                    "domain":
                        "CUSTOM",

                    "topic":
                        value,
                })

            elif isinstance(
                value,
                dict
            ):
                result.append({
                    "label":
                        str(
                            value.get(
                                "label"
                            )
                            or
                            chr(
                                64 + index
                            )
                        ),

                    "domain":
                        str(
                            value.get(
                                "domain"
                            )
                            or
                            "CUSTOM"
                        ),

                    "topic":
                        str(
                            value.get(
                                "topic"
                            )
                            or ""
                        ),
                })

        return result


    return list(
        DEFAULT_TOPICS
    )


if __name__ == "__main__":
    values = topics()

    save_json(
        BASE
        / "topic_bank.json",
        {
            "topics":
                values
        }
    )

    print(
        "VI1500 TOPIC BANK=PASS"
    )

    for item in values:
        print(
            item[
                "label"
            ],
            "|",
            item[
                "domain"
            ],
            "|",
            item[
                "topic"
            ]
        )
