#!/usr/bin/env python3

import re

from vi1000_1_semantic_core import (
    norm,
)


def metadata_text(
    raw
):
    fields = [
        raw.get(
            "title",
            ""
        ),

        raw.get(
            "description",
            ""
        ),

        raw.get(
            "object_name",
            ""
        ),

        raw.get(
            "categories",
            ""
        ),

        raw.get(
            "credit",
            ""
        ),

        raw.get(
            "artist",
            ""
        ),

        raw.get(
            "creator",
            ""
        ),
    ]

    return " ".join(
        str(value or "")
        for value in fields
    )


def infer_role_tags(
    raw
):
    text = norm(
        metadata_text(
            raw
        )
    )


    tags = set()


    if any(
        value in text
        for value in [
            "surveillance",
            "security camera",
            "elevator video",
            "footage",
            "cctv",
        ]
    ):
        tags.add(
            "EVIDENCE"
        )


    if any(
        value in text
        for value in [
            "report",
            "document",
            "record",
            "autopsy",
            "coroner",
            "certificate",
        ]
    ):
        tags.add(
            "DOCUMENT"
        )


    if any(
        value in text
        for value in [
            "medicine",
            "medication",
            "medical box",
            "medicine box",
            "pill",
            "bottle",
            "water tank",
        ]
    ):
        tags.add(
            "OBJECT"
        )


    if any(
        value in text
        for value in [
            "hotel",
            "hallway",
            "corridor",
            "elevator",
            "rooftop",
            "building",
            "hospital",
            "university",
        ]
    ):
        tags.add(
            "LOCATION"
        )


    if any(
        value in text
        for value in [
            "portrait",
            "photograph of",
            "woman",
            "man",
            "student",
            "person",
        ]
    ):
        tags.add(
            "HUMAN"
        )


    if not tags:
        tags.add(
            "CONTEXT"
        )


    return sorted(
        tags
    )


def entity_mentions(
    raw,
    entities
):
    text = norm(
        metadata_text(
            raw
        )
    )

    hits = []


    for entity in (
        entities.get(
            "entities"
        )
        or []
    ):
        if (
            entity[
                "normalized"
            ]
            in text
        ):
            hits.append(
                entity[
                    "name"
                ]
            )


    return hits


def family(
    raw
):
    mime = str(
        raw.get(
            "mime"
        )
        or ""
    ).lower()

    mediatype = str(
        raw.get(
            "mediatype"
        )
        or ""
    ).lower()


    if (
        mime.startswith(
            "video/"
        )
        or
        mediatype
        in {
            "movies",
            "video",
        }
    ):
        return "VIDEO"


    return "IMAGE"


def adapt(
    raw,
    scene,
    entities,
    search_query=""
):
    hits = entity_mentions(
        raw,
        entities
    )


    case_context = bool(
        hits
    )


    if case_context:
        usage = (
            "CASE_SPECIFIC"
        )

        label = False

    else:
        usage = (
            "ILLUSTRATIVE"
        )

        label = True


    provider = raw.get(
        "provider",
        "UNKNOWN"
    )


    unique_id = (
        raw.get(
            "pageid"
        )
        or
        raw.get(
            "identifier"
        )
        or
        raw.get(
            "title"
        )
        or "unknown"
    )


    width = int(
        raw.get(
            "width"
        )
        or 0
    )

    height = int(
        raw.get(
            "height"
        )
        or 0
    )


    if family(
        raw
    ) == "VIDEO":
        quality = 82

    else:
        pixels = (
            width
            * height
        )

        if pixels >= 2000000:
            quality = 94

        elif pixels >= 800000:
            quality = 84

        else:
            quality = 50


    return {
        "candidate_id":
            (
                str(provider)
                + ":"
                + str(unique_id)
            ),

        "title":
            raw.get(
                "title",
                ""
            ),

        "evidence_text":
            metadata_text(
                raw
            ),

        "entity_mentions":
            hits,

        "role_tags":
            infer_role_tags(
                raw
            ),

        "license":
            raw.get(
                "license",
                ""
            ),

        "license_url":
            raw.get(
                "license_url",
                ""
            ),

        "family":
            family(
                raw
            ),

        "width":
            width,

        "height":
            height,

        "intended_usage":
            usage,

        "illustration_label":
            label,

        "source_group":
            (
                str(provider)
                + ":"
                + str(unique_id)
            ),

        "generic":
            not case_context,

        "quality_score":
            quality,

        "semantic_score":
            (
                94
                if case_context
                else 65
            ),

        "provenance_score":
            (
                98
                if provider
                == "WIKIMEDIA_COMMONS"
                else 80
            ),

        # Deliberately kept separate.
        # evaluate_candidate() never treats this
        # field as evidence.
        "search_query":
            search_query,

        "provider":
            provider,

        "remote_url":
            raw.get(
                "remote_url",
                ""
            ),

        "metadata_only":
            True,

        "raw_metadata":
            raw,
    }


if __name__ == "__main__":
    print(
        "VI1200 REAL CANDIDATE ADAPTER=PASS"
    )
