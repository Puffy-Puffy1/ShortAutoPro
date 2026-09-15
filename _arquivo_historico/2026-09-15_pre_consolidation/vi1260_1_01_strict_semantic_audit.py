#!/usr/bin/env python3

import copy
from pathlib import Path

from vi1000_1_semantic_core import norm

from vi1000_1_query_gate import (
    license_allowed,
    technical_pass,
    story_entity_hits,
)

from vi1200_06_visual_precision import (
    candidate_text,
)

from vi1260_01_semantic_roles import (
    candidate_semantics,
)


DOCUMENT_WORDS = {
    "autopsy report",
    "coroner report",
    "medical examiner",
    "official report",
    "case document",
}

TRANSPORT_NEGATIVES = {
    "railroad",
    "railway",
    "train station",
    "rail station",
    "airport",
    "bus terminal",
    "subway station",
    "metro station",
    "tram station",
}

ACTION_WORDS = {
    "door",
    "doorway",
    "hallway",
    "corridor",
    "elevator",
    "lift",
    "hiding",
    "hide",
    "peeking",
    "peek",
    "surveillance",
    "cctv",
}

EVIDENCE_WORDS = {
    "surveillance",
    "cctv",
    "security camera",
    "camera footage",
    "elevator",
    "elevator video",
}


def raw_metadata(candidate):
    return (
        candidate.get("raw_metadata")
        or {}
    )


def first_value(
    candidate,
    *keys
):
    raw = raw_metadata(
        candidate
    )

    for key in keys:
        value = candidate.get(key)

        if value not in {
            None,
            "",
        }:
            return value

        value = raw.get(key)

        if value not in {
            None,
            "",
        }:
            return value

    return None


def media_kind(candidate):
    mime = str(
        first_value(
            candidate,
            "mime",
            "mime_type",
            "content_type",
        )
        or ""
    ).lower()

    title = str(
        candidate.get("title")
        or ""
    ).lower()

    path = Path(title)

    suffix = path.suffix.lower()


    if (
        mime == "application/pdf"
        or
        suffix == ".pdf"
    ):
        return "PDF"


    if (
        mime.startswith("video/")
        or
        suffix in {
            ".webm",
            ".mp4",
            ".mov",
            ".mkv",
        }
    ):
        return "VIDEO"


    if (
        mime.startswith("image/")
        or
        suffix in {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        }
    ):
        return "IMAGE"


    return "OTHER"


# VI1260.2.1 DOWNLOAD FORMAT COMPATIBILITY
def controlled_download_format_allowed(
    candidate,
):
    mime = str(
        first_value(
            candidate,
            "mime",
            "mime_type",
            "content_type",
        )
        or ""
    ).lower()


    title = str(
        candidate.get(
            "title"
        )
        or ""
    ).lower()


    allowed_mime = {
        "image/jpeg",
        "image/png",
        "image/webp",
        "video/webm",
        "video/mp4",
        "application/pdf",
    }


    allowed_suffix = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".webm",
        ".mp4",
        ".pdf",
    }


    suffix = Path(
        title
    ).suffix.lower()


    if mime:

        if mime in allowed_mime:
            return True


        # Explicitly known but unsupported formats
        # must not reach the downloader.
        if mime.startswith(
            (
                "image/",
                "video/",
                "application/",
            )
        ):
            return False


    return (
        suffix
        in allowed_suffix
    )


def contains_any(
    text,
    values
):
    value = norm(
        text
    )

    return any(
        norm(item) in value
        for item in values
    )


def safe_metadata(candidate):
    reasons = []

    if not license_allowed(
        candidate.get("license")
    ):
        reasons.append(
            "license_failed"
        )


    evidence = str(
        candidate.get(
            "evidence_text"
        )
        or ""
    ).strip()


    if not evidence:
        reasons.append(
            "metadata_evidence_missing"
        )


    return reasons


def context_technical_policy(
    candidate,
    *,
    archival=False,
):
    """
    VI1260.2

    Full technical quality is still preferred.

    A verified case/archive asset may survive a
    technical-resolution failure ONLY as contextual
    insert media, never as unrestricted/fullscreen
    replacement.
    """

    if technical_pass(
        candidate
    ):
        return {
            "passed":
                True,

            "restricted":
                False,

            "presentation_constraints":
                [],
        }


    source_class = str(
        candidate.get(
            "source_class"
        )
        or ""
    )


    if (
        archival
        and
        source_class
        in {
            "CASE_ARCHIVE",
            "VERIFIED_LOCATION",
            "CASE_ENTITY",
        }
    ):
        return {
            "passed":
                True,

            "restricted":
                True,

            "presentation_constraints": [
                "CONTEXT_INSERT_ONLY",
                "NO_FULLSCREEN",
                "NO_FALSE_DETAIL_ENHANCEMENT",
            ],
        }


    return {
        "passed":
            False,

        "restricted":
            False,

        "presentation_constraints": [],
    }


def make_pass(
    item,
    *,
    mode,
    semantics,
    overlay_label=None,
    claim_visualized=False,
    constraints=None,
):
    result = copy.deepcopy(
        item
    )

    evaluation = dict(
        result.get(
            "evaluation"
        )
        or {}
    )

    evaluation[
        "passed"
    ] = True

    evaluation[
        "mode"
    ] = mode

    evaluation[
        "candidate_semantics"
    ] = sorted(
        semantics
    )

    evaluation[
        "query_used_as_evidence"
    ] = False

    evaluation[
        "overlay_label"
    ] = overlay_label

    evaluation[
        "claim_visualized"
    ] = claim_visualized

    evaluation[
        "presentation_constraints"
    ] = list(
        constraints
        or []
    )

    evaluation[
        "strict_reasons"
    ] = []


    result[
        "evaluation"
    ] = evaluation

    result[
        "rank"
    ] = max(
        1.0,
        float(
            result.get(
                "rank",
                0
            )
        ),
    )

    return result


def reject(
    item,
    reasons,
    semantics=None,
):
    result = copy.deepcopy(
        item
    )

    evaluation = dict(
        result.get(
            "evaluation"
        )
        or {}
    )

    evaluation[
        "passed"
    ] = False

    evaluation[
        "mode"
    ] = "STRICT_REJECT"

    evaluation[
        "query_used_as_evidence"
    ] = False

    evaluation[
        "strict_reasons"
    ] = sorted(
        set(
            reasons
        )
    )

    evaluation[
        "candidate_semantics"
    ] = sorted(
        semantics
        or []
    )


    result[
        "evaluation"
    ] = evaluation

    result[
        "rank"
    ] = -10000.0

    return result


def strict_scene3(
    item,
    entities,
):
    candidate = item[
        "candidate"
    ]

    kind = media_kind(
        candidate
    )

    text = candidate_text(
        candidate
    )

    semantics = set(
        candidate_semantics(
            candidate,
            entities
        )
    )

    source_class = str(
        candidate.get(
            "source_class"
        )
        or ""
    )

    metadata_reasons = (
        safe_metadata(
            candidate
        )
    )


    if metadata_reasons:
        return reject(
            item,
            metadata_reasons,
            semantics
        )


    if (
        kind == "PDF"
        or
        contains_any(
            text,
            DOCUMENT_WORDS
        )
    ):
        return reject(
            item,
            [
                "scene3_document_cannot_represent_person"
            ],
            semantics
        )


    if kind not in {
        "IMAGE",
        "VIDEO",
    }:
        return reject(
            item,
            [
                "scene3_requires_visual_media"
            ],
            semantics
        )


    # Best path: genuine person-linked visual.
    if (
        "SPECIFIC_PERSON"
        in semantics
        and
        source_class
        in {
            "CASE_ARCHIVE",
            "CASE_ENTITY",
        }
    ):
        tech = context_technical_policy(
            candidate,
            archival=True,
        )

        if not tech[
            "passed"
        ]:
            return reject(
                item,
                [
                    "scene3_case_person_technical_failure"
                ],
                semantics
            )


        return make_pass(
            item,
            mode=(
                "STRICT_CASE_PERSON_ARCHIVAL_CONTEXT"
                if tech[
                    "restricted"
                ]
                else
                "STRICT_CASE_PERSON_VISUAL"
            ),
            semantics=semantics,
            overlay_label=(
                "IMAGEM DE CONTEXTO"
                if tech[
                    "restricted"
                ]
                else None
            ),
            claim_visualized=(
                not tech[
                    "restricted"
                ]
            ),
            constraints=tech[
                "presentation_constraints"
            ],
        )


    # Safe fallback: verified Hotel Cecil visual.
    # It is explicitly context and does NOT pretend
    # to be a portrait of Elisa.
    if (
        "VERIFIED_CASE_LOCATION"
        in semantics
        and
        source_class
        in {
            "VERIFIED_LOCATION",
            "CASE_ENTITY",
        }
        and
        story_entity_hits(
            candidate,
            entities
        )
    ):
        tech = context_technical_policy(
            candidate,
            archival=True,
        )

        if not tech[
            "passed"
        ]:
            return reject(
                item,
                [
                    "scene3_case_location_technical_failure"
                ],
                semantics
            )


        constraints = list(
            tech[
                "presentation_constraints"
            ]
        )

        constraints.append(
            "DO_NOT_IMPLY_PORTRAIT"
        )


        return make_pass(
            item,
            mode="STRICT_CASE_LOCATION_CONTEXT",
            semantics=semantics,
            overlay_label="IMAGEM DE CONTEXTO",
            claim_visualized=False,
            constraints=constraints,
        )


    return reject(
        item,
        [
            "scene3_specific_person_or_verified_case_location_required"
        ],
        semantics
    )


def strict_scene6(
    item,
    entities,
):
    candidate = item[
        "candidate"
    ]

    kind = media_kind(
        candidate
    )

    text = candidate_text(
        candidate
    )

    semantics = set(
        candidate_semantics(
            candidate,
            entities
        )
    )


    metadata_reasons = (
        safe_metadata(
            candidate
        )
    )


    if metadata_reasons:
        return reject(
            item,
            metadata_reasons,
            semantics
        )


    if kind not in {
        "IMAGE",
        "VIDEO",
    }:
        return reject(
            item,
            [
                "scene6_requires_visual_media"
            ],
            semantics
        )


    if not controlled_download_format_allowed(
        candidate
    ):
        return reject(
            item,
            [
                "scene6_download_format_not_allowed"
            ],
            semantics
        )


    if contains_any(
        text,
        TRANSPORT_NEGATIVES
    ):
        return reject(
            item,
            [
                "scene6_transport_location_negative_evidence"
            ],
            semantics
        )


    semantic_match = bool(
        semantics
        &
        {
            "HIDE_BEHAVIOR",
            "HALLWAY",
            "ELEVATOR",
            "SURVEILLANCE",
        }
    )


    lexical_match = contains_any(
        text,
        ACTION_WORDS
    )


    if not (
        semantic_match
        or
        lexical_match
    ):
        return reject(
            item,
            [
                "scene6_action_visual_missing"
            ],
            semantics
        )


    source_class = str(
        candidate.get(
            "source_class"
        )
        or ""
    )


    archival = (
        source_class
        in {
            "CASE_ARCHIVE",
            "CASE_ENTITY",
            "VERIFIED_LOCATION",
        }
    )


    tech = context_technical_policy(
        candidate,
        archival=archival,
    )


    if not tech[
        "passed"
    ]:
        return reject(
            item,
            [
                "scene6_technical_gate_failed"
            ],
            semantics
        )


    generic = bool(
        candidate.get(
            "generic"
        )
    )


    constraints = list(
        tech[
            "presentation_constraints"
        ]
    )

    constraints.append(
        "DO_NOT_CLAIM_HIDING_ACTION"
    )


    return make_pass(
        item,
        mode=(
            "STRICT_ACTION_ILLUSTRATION"
            if generic
            else
            "STRICT_ACTION_CONTEXT"
        ),
        semantics=semantics,
        overlay_label=(
            "IMAGEM ILUSTRATIVA"
            if generic
            else
            "IMAGEM DE CONTEXTO"
        ),
        claim_visualized=False,
        constraints=constraints,
    )


def strict_scene8(
    item,
    entities,
):
    candidate = item[
        "candidate"
    ]

    kind = media_kind(
        candidate
    )

    text = candidate_text(
        candidate
    )

    semantics = set(
        candidate_semantics(
            candidate,
            entities
        )
    )


    metadata_reasons = (
        safe_metadata(
            candidate
        )
    )


    if metadata_reasons:
        return reject(
            item,
            metadata_reasons,
            semantics
        )


    if kind == "PDF":
        return reject(
            item,
            [
                "scene8_document_not_evidence_discussion_visual"
            ],
            semantics
        )


    if kind not in {
        "IMAGE",
        "VIDEO",
    }:
        return reject(
            item,
            [
                "scene8_requires_visual_media"
            ],
            semantics
        )


    semantic_match = bool(
        semantics
        &
        {
            "SURVEILLANCE",
            "ELEVATOR",
            "EVIDENCE",
        }
    )


    lexical_match = contains_any(
        text,
        EVIDENCE_WORDS
    )


    if not (
        semantic_match
        or
        lexical_match
    ):
        return reject(
            item,
            [
                "scene8_surveillance_or_elevator_context_required"
            ],
            semantics
        )


    source_class = str(
        candidate.get(
            "source_class"
        )
        or ""
    )


    archival = (
        source_class
        in {
            "CASE_ARCHIVE",
            "CASE_ENTITY",
        }
    )


    tech = context_technical_policy(
        candidate,
        archival=archival,
    )


    if not tech[
        "passed"
    ]:
        return reject(
            item,
            [
                "scene8_technical_gate_failed"
            ],
            semantics
        )


    generic = bool(
        candidate.get(
            "generic"
        )
    )


    constraints = list(
        tech[
            "presentation_constraints"
        ]
    )


    if generic:
        constraints.append(
            "DO_NOT_IMPLY_ACTUAL_ELISA_FOOTAGE"
        )


    return make_pass(
        item,
        mode=(
            "STRICT_GENERIC_EVIDENCE_CONTEXT"
            if generic
            else
            "STRICT_CASE_EVIDENCE_ARCHIVAL_CONTEXT"
            if tech[
                "restricted"
            ]
            else
            "STRICT_EVIDENCE_DISCUSSION"
        ),
        semantics=semantics,
        overlay_label=(
            "IMAGEM ILUSTRATIVA"
            if generic
            else
            "IMAGEM DE CONTEXTO"
            if tech[
                "restricted"
            ]
            else None
        ),
        claim_visualized=(
            not generic
            and
            not tech[
                "restricted"
            ]
        ),
        constraints=constraints,
    )


def strict_item(
    scene,
    item,
    entities,
):
    number = int(
        scene[
            "scene"
        ]
    )


    if number == 3:
        return strict_scene3(
            item,
            entities
        )


    if number == 6:
        return strict_scene6(
            item,
            entities
        )


    if number == 8:
        return strict_scene8(
            item,
            entities
        )


    result = copy.deepcopy(
        item
    )


    if result.get(
        "evaluation",
        {}
    ).get(
        "passed"
    ):
        result[
            "evaluation"
        ][
            "query_used_as_evidence"
        ] = False


    return result


if __name__ == "__main__":
    print(
        "VI1260.2 STRICT SEMANTIC AUDIT=PASS"
    )
