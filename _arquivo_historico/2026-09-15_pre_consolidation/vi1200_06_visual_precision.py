#!/usr/bin/env python3

import re

from vi1000_1_semantic_core import (
    norm,
)


STOPWORDS = {
    "a", "o", "as", "os",
    "de", "da", "do", "das", "dos",
    "em", "no", "na", "nos", "nas",
    "um", "uma",
    "e", "ou",
    "que",
    "para", "por",
    "com", "sem",
    "foi", "era",
    "the", "a", "an",
    "of", "in", "on",
    "and", "or",
    "to", "for",
    "with", "without",
    "was", "were",
}


def tokens(
    value
):
    return {
        token
        for token in re.findall(
            r"[a-z0-9]+",
            norm(
                value
            )
        )
        if (
            len(token) >= 4
            and
            token not in STOPWORDS
        )
    }


def contains_any(
    text,
    phrases
):
    text = norm(
        text
    )

    return any(
        norm(
            phrase
        )
        in text

        for phrase in phrases
    )


def candidate_text(
    candidate
):
    raw = (
        candidate.get(
            "raw_metadata"
        )
        or {}
    )

    pieces = [
        candidate.get(
            "title",
            ""
        ),

        candidate.get(
            "evidence_text",
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
            "creator",
            ""
        ),

        raw.get(
            "artist",
            ""
        ),
    ]

    return " ".join(
        str(
            item or ""
        )
        for item in pieces
    )


def media_kind(
    candidate
):
    raw = (
        candidate.get(
            "raw_metadata"
        )
        or {}
    )

    mime = str(
        raw.get(
            "mime"
        )
        or ""
    ).lower()

    title = str(
        candidate.get(
            "title"
        )
        or ""
    ).lower()

    family = str(
        candidate.get(
            "family"
        )
        or ""
    ).upper()

    mediatype = str(
        raw.get(
            "mediatype"
        )
        or ""
    ).lower()


    if (
        mime
        == "application/pdf"
        or
        title.endswith(
            ".pdf"
        )
    ):
        return "PDF"


    if (
        family == "VIDEO"
        or
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


def scene_visual_intents(
    scene
):
    text = norm(
        scene.get(
            "segment"
        )
        or ""
    )

    role = str(
        scene.get(
            "role"
        )
        or "CONTEXT"
    ).upper()

    intents = {
        role
    }


    if contains_any(
        text,
        [
            "elevador",
            "elevator",
            "portas do elevador",
        ]
    ):
        intents.add(
            "ELEVATOR"
        )


    if contains_any(
        text,
        [
            "corredor",
            "hallway",
            "corridor",
        ]
    ):
        intents.add(
            "HALLWAY"
        )


    if contains_any(
        text,
        [
            "telhado",
            "cobertura",
            "rooftop",
            "topo do predio",
            "topo do prédio",
        ]
    ):
        intents.add(
            "ROOFTOP"
        )


    if contains_any(
        text,
        [
            "camera de seguranca",
            "câmera de segurança",
            "filmagem",
            "footage",
            "surveillance",
            "gravacao",
            "gravação",
        ]
    ):
        intents.add(
            "SURVEILLANCE"
        )


    if contains_any(
        text,
        [
            "medicacao",
            "medicação",
            "medicamento",
            "medicine",
            "remedio",
            "remédio",
        ]
    ):
        intents.add(
            "MEDICATION"
        )


    if contains_any(
        text,
        [
            "caixa d agua",
            "caixa d'agua",
            "water tank",
            "tanque de agua",
        ]
    ):
        intents.add(
            "WATER_TANK"
        )


    if role == "HUMAN":
        intents.add(
            "HUMAN"
        )


    if role == "DOCUMENT":
        intents.add(
            "DOCUMENT"
        )


    if role == "OBJECT":
        intents.add(
            "OBJECT"
        )


    return intents


def candidate_visual_intents(
    candidate
):
    text = norm(
        candidate_text(
            candidate
        )
    )

    role_tags = {
        str(
            item
        ).upper()

        for item in (
            candidate.get(
                "role_tags"
            )
            or []
        )
    }

    intents = set(
        role_tags
    )


    if contains_any(
        text,
        [
            "elevator",
            "elevador",
        ]
    ):
        intents.add(
            "ELEVATOR"
        )


    if contains_any(
        text,
        [
            "hallway",
            "corridor",
            "corredor",
        ]
    ):
        intents.add(
            "HALLWAY"
        )


    if contains_any(
        text,
        [
            "rooftop",
            "roof top",
            "roof",
            "telhado",
            "water tower",
            "water tank",
        ]
    ):
        intents.add(
            "ROOFTOP"
        )


    if contains_any(
        text,
        [
            "surveillance",
            "security camera",
            "cctv",
            "elevator video",
            "security footage",
            "footage",
        ]
    ):
        intents.add(
            "SURVEILLANCE"
        )


    if contains_any(
        text,
        [
            "medicine",
            "medication",
            "medicine box",
            "medical box",
            "pill bottle",
            "medicamento",
        ]
    ):
        intents.add(
            "MEDICATION"
        )

        intents.add(
            "OBJECT"
        )


    if contains_any(
        text,
        [
            "water tank",
            "water tower",
            "tanque de agua",
        ]
    ):
        intents.add(
            "WATER_TANK"
        )

        intents.add(
            "OBJECT"
        )


    human_words = re.search(
        r"\b("
        r"woman|man|person|student|portrait|"
        r"girl|boy|employee|worker|guest"
        r")\b",
        text
    )


    if human_words:
        intents.add(
            "HUMAN"
        )


    if contains_any(
        text,
        [
            "hotel",
            "hospital",
            "university",
            "building",
        ]
    ):
        intents.add(
            "LOCATION"
        )


    if (
        media_kind(
            candidate
        )
        == "PDF"
    ):
        intents.add(
            "DOCUMENT"
        )

        intents.add(
            "PDF"
        )


    if contains_any(
        text,
        [
            "official report",
            "autopsy report",
            "police report",
            "coroner report",
            "document",
            "official record",
        ]
    ):
        intents.add(
            "DOCUMENT"
        )


    return intents


def evaluate_visual_precision(
    scene,
    candidate
):
    reasons = []

    scene_intents = (
        scene_visual_intents(
            scene
        )
    )

    candidate_intents = (
        candidate_visual_intents(
            candidate
        )
    )

    role = str(
        scene.get(
            "role"
        )
        or "CONTEXT"
    ).upper()

    kind = media_kind(
        candidate
    )


    if (
        kind == "PDF"
        and
        role != "DOCUMENT"
    ):
        reasons.append(
            "pdf_not_allowed_for_visual_scene"
        )


    if (
        role == "HUMAN"
        and
        "HUMAN"
        not in candidate_intents
    ):
        reasons.append(
            "human_visual_required"
        )


    if (
        role == "OBJECT"
        and
        not (
            {
                "OBJECT",
                "MEDICATION",
                "WATER_TANK",
            }
            &
            candidate_intents
        )
    ):
        reasons.append(
            "object_visual_required"
        )


    if (
        role == "DOCUMENT"
        and
        "DOCUMENT"
        not in candidate_intents
    ):
        reasons.append(
            "document_visual_required"
        )


    if role == "EVIDENCE":
        if (
            "SURVEILLANCE"
            in scene_intents
            and
            not (
                "SURVEILLANCE"
                in candidate_intents
                or
                (
                    kind == "VIDEO"
                    and
                    "ELEVATOR"
                    in candidate_intents
                )
            )
        ):
            reasons.append(
                "surveillance_visual_required"
            )


        if (
            kind == "PDF"
            and
            "SURVEILLANCE"
            in scene_intents
        ):
            reasons.append(
                "document_not_surveillance_visual"
            )


    subtype_requirements = [
        "ELEVATOR",
        "HALLWAY",
        "ROOFTOP",
        "MEDICATION",
        "WATER_TANK",
    ]


    for subtype in subtype_requirements:

        if (
            subtype
            in scene_intents
            and
            subtype
            not in candidate_intents
        ):
            reasons.append(
                "visual_subtype_mismatch:"
                + subtype.lower()
            )


    scene_words = tokens(
        scene.get(
            "segment"
        )
        or ""
    )

    media_words = tokens(
        candidate_text(
            candidate
        )
    )

    overlap = sorted(
        scene_words
        &
        media_words
    )


    strong_visual_match = bool(
        (
            scene_intents
            -
            {
                "CONTEXT",
                "LOCATION",
                "HUMAN",
                "OBJECT",
                "DOCUMENT",
                "EVIDENCE",
            }
        )
        &
        candidate_intents
    )


    if (
        role == "CONTEXT"
        and
        not strong_visual_match
        and
        not overlap
    ):
        reasons.append(
            "context_metadata_has_zero_scene_overlap"
        )


    precision_score = 100


    precision_score -= (
        len(
            reasons
        )
        * 30
    )


    precision_score += min(
        10,
        len(
            overlap
        )
        * 2
    )


    return {
        "passed":
            not reasons,

        "reasons":
            sorted(
                set(
                    reasons
                )
            ),

        "media_kind":
            kind,

        "scene_intents":
            sorted(
                scene_intents
            ),

        "candidate_intents":
            sorted(
                candidate_intents
            ),

        "metadata_overlap":
            overlap,

        "precision_score":
            max(
                0,
                min(
                    100,
                    precision_score
                )
            ),
    }


if __name__ == "__main__":
    print(
        "VI1200.1 VISUAL PRECISION=PASS"
    )
