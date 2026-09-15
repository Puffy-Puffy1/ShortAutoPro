#!/usr/bin/env python3

from vi1500_01_common import (
    BASE,
    save_json,
    sha256_text,
)

from vi1500_02_topic_bank import (
    topics,
)

from vi1500_03_risk_classifier import (
    classify,
)


def build():
    private = []

    public = []


    for item in topics():
        topic = item[
            "topic"
        ]

        risk = classify(
            topic,
            item[
                "domain"
            ],
        )

        digest = sha256_text(
            topic
        )


        private.append({
            **item,
            **risk,
            "topic_hash":
                digest,
        })


        public.append({
            "label":
                item[
                    "label"
                ],

            "domain":
                item[
                    "domain"
                ],

            "risk_level":
                risk[
                    "risk_level"
                ],

            "topic_hash":
                digest,
        })


    save_json(
        BASE
        / "queue_private.json",
        {
            "topics":
                private
        }
    )


    save_json(
        BASE
        / "queue_public.json",
        {
            "topics":
                public,

            "blind_qa":
                True,
        }
    )


    return private


if __name__ == "__main__":
    values = build()

    print(
        "VI1500 BLIND CONTROLLER=PASS"
    )

    print(
        "TOPICS=",
        len(
            values
        )
    )
