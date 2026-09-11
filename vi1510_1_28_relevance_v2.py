#!/usr/bin/env python3

import re

from urllib.parse import (
    unquote,
)

from vi1510_01_common import (
    save_json,
)

from vi1510_1_26_evidence_text import (
    folded,
)


# Generic linguistic/function words only.
#
# No benchmark/topic-specific nouns are allowed here.
STOPWORDS = {
    "sobre",
    "entre",
    "para",
    "como",
    "onde",
    "quando",
    "porque",
    "caso",
    "evento",
    "historia",
    "história",

    "what",
    "where",
    "when",
    "with",
    "from",
    "into",
    "about",
    "case",
    "event",
    "story",
    "history",
    "the",
    "and",
    "that",
    "this",
}


def tokens(
    topic,
):
    words = re.findall(
        r"[a-z0-9]+",
        folded(
            topic
        ),
    )


    values = []


    for word in words:

        if (
            len(
                word
            ) < 4

            or

            word in STOPWORDS

            or

            word.isdigit()
        ):
            continue


        values.append(
            word
        )


    return sorted(
        set(
            values
        )
    )


def record_text(
    record,
):
    """
    Search/topic/query text is intentionally excluded.

    Only independent source metadata is allowed to
    contribute to semantic relevance.
    """

    return folded(
        " ".join([
            str(
                record.get(
                    "title"
                )
                or ""
            ),

            str(
                record.get(
                    "evidence_text"
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

            str(
                record.get(
                    "provider"
                )
                or ""
            ),
        ])
    )


def run(
    run,
    metadata,
    run_dir,
):
    anchors = tokens(
        run.get(
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

        text = record_text(
            record
        )


        hits = [
            anchor

            for anchor in anchors

            if re.search(
                r"\b"
                +
                re.escape(
                    anchor
                )
                +
                r"\b",
                text,
            )
        ]


        # Generic rule:
        # at least one topic-derived anchor must appear
        # in independent source metadata.
        relevant = bool(
            hits
        )


        rows.append({
            "record_index":
                index,

            "title":
                record.get(
                    "title"
                ),

            "provider":
                record.get(
                    "provider"
                ),

            "source_url":
                record.get(
                    "source_url"
                ),

            "source_group":
                record.get(
                    "source_group"
                ),

            "hits":
                hits,

            "relevant":
                relevant,
        })


    relevant_rows = [
        row

        for row in rows

        if row[
            "relevant"
        ]
    ]


    report = {
        "status":
            (
                "PASS"
                if relevant_rows
                else "HOLD"
            ),

        "anchors":
            anchors,

        "record_count":
            len(
                rows
            ),

        "relevant_record_count":
            len(
                relevant_rows
            ),

        "relevant_records":
            relevant_rows,

        "records":
            rows,

        "query_used_as_evidence":
            False,

        "blockers":
            (
                []

                if relevant_rows

                else [
                    "insufficient_topic_specific_source_metadata"
                ]
            ),
    }


    save_json(
        run_dir
        / "metadata_relevance_v2.json",
        report
    )


    return report
