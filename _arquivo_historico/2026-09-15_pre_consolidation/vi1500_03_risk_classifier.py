#!/usr/bin/env python3

import re

from vi1500_01_common import (
    BASE,
    save_json,
)

from vi1500_02_topic_bank import (
    topics,
)


def classify(
    topic,
    domain,
):
    text = topic.lower()

    score = 0

    reasons = []


    if domain in {
        "HISTORICAL_MYSTERY",
        "HISTORICAL_EVENT",
    }:
        score += 1


    if re.search(
        r"\b(morte|morreu|desastre|desaparecimento|crime)\b",
        text,
    ):
        score += 1

        reasons.append(
            "sensitive_event"
        )


    if re.search(
        r"\b(assassin|suic|homic|terror)\w*",
        text,
    ):
        score += 2

        reasons.append(
            "high_sensitive_event"
        )


    if domain == "SCIENCE_CONCEPT":
        reasons.append(
            "concept_requires_visual_abstraction"
        )


    if score >= 3:
        level = "HIGH"

    elif score >= 1:
        level = "MEDIUM"

    else:
        level = "LOW"


    return {
        "risk_level":
            level,

        "risk_score":
            score,

        "reasons":
            reasons,

        "requires_provenance":
            True,

        "requires_visual_truth_gate":
            True,
    }


if __name__ == "__main__":
    rows = []

    for item in topics():
        result = classify(
            item[
                "topic"
            ],
            item[
                "domain"
            ],
        )

        rows.append({
            **item,
            **result,
        })


    save_json(
        BASE
        / "topic_risk.json",
        {
            "topics":
                rows
        }
    )


    print(
        "VI1500 RISK CLASSIFIER=PASS"
    )

    for row in rows:
        print(
            row[
                "label"
            ],
            "|",
            row[
                "risk_level"
            ],
            "|",
            row[
                "reasons"
            ]
        )
