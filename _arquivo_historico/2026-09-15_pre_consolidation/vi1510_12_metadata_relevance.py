#!/usr/bin/env python3

import re

from urllib.parse import unquote

from vi1510_01_common import (
    norm,
    save_json,
)

from vi1510_10_domain_policy import (
    requirements,
)


STOPWORDS = {
    "o",
    "a",
    "os",
    "as",
    "de",
    "da",
    "do",
    "das",
    "dos",
    "e",
    "em",
    "um",
    "uma",
    "que",
    "para",
    "por",
    "the",
    "of",
    "and",
    "in",
    "on",
    "with",
    "silencio",
    "silêncio",
    "desastre",
    "desaparecimento",
}


def topic_tokens(
    topic,
):
    tokens = re.findall(
        r"[a-zA-ZÀ-ÿ0-9]+",
        norm(
            topic
        ),
    )


    return {
        token

        for token in tokens

        if (
            len(
                token
            ) >= 4

            and

            token not in STOPWORDS
        )
    }


def metadata_text(
    record,
):
    # Deliberately does NOT use query/search fields.
    return norm(
        " ".join([
            str(
                record.get(
                    "title"
                )
                or ""
            ),

            str(
                record.get(
                    "description"
                )
                or ""
            ),

            unquote(
                str(
                    record.get(
                        "source_url"
                    )
                    or ""
                )
            ),

            str(
                record.get(
                    "source_group"
                )
                or ""
            ),
        ])
    )


def run(
    run_info,
    metadata,
    run_dir,
):
    tokens = topic_tokens(
        run_info.get(
            "topic"
        )
    )


    rows = []


    for index, record in enumerate(
        metadata.get(
            "records",
            []
        )
    ):

        text = metadata_text(
            record
        )


        hits = sorted(
            token

            for token in tokens

            if token in text
        )


        rows.append({
            "record_index":
                index,

            "title":
                record.get(
                    "title"
                ),

            "hits":
                hits,

            "relevant":
                bool(
                    hits
                ),
        })


    relevant = [
        row

        for row in rows

        if row[
            "relevant"
        ]
    ]


    minimum = int(
        requirements(
            run_info.get(
                "domain",
                "CUSTOM"
            )
        ).get(
            "minimum_relevant_records",
            1
        )
    )


    blockers = []


    if len(
        relevant
    ) < minimum:

        blockers.append(
            "insufficient_topic_specific_source_metadata"
        )


    report = {
        "status":
            (
                "PASS"
                if not blockers
                else "HOLD"
            ),

        "topic_tokens":
            sorted(
                tokens
            ),

        "relevant_record_count":
            len(
                relevant
            ),

        "records":
            rows,

        "query_used_as_evidence":
            False,

        "blockers":
            blockers,
    }


    save_json(
        run_dir
        / "metadata_relevance.json",
        report
    )


    return report
