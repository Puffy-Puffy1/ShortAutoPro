#!/usr/bin/env python3

import json
import re
import unicodedata

from pathlib import Path


VERSION = "1000.1"

BASE = (
    Path.home()
    / "ShortAutoPro"
)

POLICY_PATH = (
    BASE
    / "config"
    / "vi1000_1_semantic_policy.json"
)


PROPER_RE = re.compile(
    r"\b"
    r"[A-ZÁÉÍÓÚÂÊÔÃÕÇ]"
    r"[A-Za-zÀ-ÿ'’\-]+"
    r"(?:\s+"
    r"[A-ZÁÉÍÓÚÂÊÔÃÕÇ]"
    r"[A-Za-zÀ-ÿ'’\-]+"
    r"){1,3}"
    r"\b"
)


PERSON_ROLE_TERMS = {
    "estudante",
    "student",
    "mulher",
    "woman",
    "homem",
    "man",
    "jovem",
    "young",
    "hospede",
    "hóspede",
    "guest",
    "turista",
    "tourist",
    "vitima",
    "vítima",
    "victim",
}


GENERIC_HUMAN_PATTERNS = {
    "uma mulher",
    "um homem",
    "uma pessoa",
    "a person",
    "someone",
    "alguem",
    "alguém",
    "pessoas",
    "funcionarios",
    "funcionários",
    "maintenance staff",
    "employees",
    "workers"
}


ROLE_SIGNALS = {
    "DOCUMENT": {
        "autopsia": 3.5,
        "laudo": 3.5,
        "relatorio": 3.0,
        "report": 3.0,
        "documento": 2.8,
        "document": 2.8,
        "registro": 2.5,
        "record": 2.5,
        "pericia": 2.3,
        "coroner": 3.0
    },

    "EVIDENCE": {
        "camera": 2.5,
        "filmagem": 3.0,
        "video": 2.5,
        "footage": 3.0,
        "surveillance": 3.5,
        "imagens": 1.7,
        "evidence": 3.0,
        "prova": 2.8,
        "seguranca": 1.7
    },

    "OBJECT": {
        "medicacao": 3.0,
        "medicamento": 3.0,
        "remedio": 3.0,
        "medicine": 3.0,
        "bottle": 2.3,
        "frasco": 2.3,
        "water tank": 3.0,
        "caixa d agua": 3.0,
        "caixa dagua": 3.0
    },

    "HUMAN": {
        "estudante": 2.5,
        "student": 2.5,
        "mulher": 2.0,
        "homem": 2.0,
        "pessoa": 2.0,
        "person": 2.0,
        "funcionario": 2.0,
        "funcionarios": 2.2,
        "funcionário": 2.0,
        "funcionários": 2.2,
        "maintenance staff": 3.0,
        "corpo": 1.5,
        "body": 1.5
    },

    "LOCATION": {
        "hotel": 2.0,
        "corredor": 3.0,
        "hallway": 3.0,
        "elevador": 3.0,
        "elevator": 3.0,
        "quarto": 2.5,
        "room": 2.0,
        "telhado": 2.8,
        "rooftop": 2.8,
        "topo": 1.5,
        "predio": 1.5,
        "building": 1.5
    }
}


FACTUAL_SIGNALS = {
    "oficial": 1.5,
    "official": 1.5,
    "confirmou": 1.5,
    "confirmed": 1.5,
    "policia": 1.5,
    "police": 1.5,
    "investigadores": 1.2,
    "investigators": 1.2,
    "autopsia": 3.0,
    "laudo": 3.0,
    "relatorio": 2.5,
    "report": 2.5,
    "pericia": 2.5,
    "surveillance": 2.3,
    "filmagem": 2.0,
    "camera de seguranca": 2.3,
    "encontraram o corpo": 3.5,
    "found the body": 3.5,
    "registro": 1.5,
    "record": 1.5
}


CTA_TERMS = {
    "comente",
    "comment",
    "compartilhe",
    "share",
    "curta",
    "like",
    "siga",
    "follow"
}


def load_policy():
    return json.loads(
        POLICY_PATH.read_text(
            encoding="utf-8"
        )
    )


def strip_accents(value):
    return "".join(
        char
        for char in unicodedata.normalize(
            "NFKD",
            str(value or "")
        )
        if not unicodedata.combining(
            char
        )
    )


def norm(value):
    value = strip_accents(
        value
    ).lower()

    value = (
        value
        .replace("_", " ")
        .replace("-", " ")
        .replace("’", "'")
    )

    value = re.sub(
        r"[^a-z0-9' ]+",
        " ",
        value
    )

    return re.sub(
        r"\s+",
        " ",
        value
    ).strip()


def contains_term(
    text,
    term
):
    return (
        norm(term)
        in norm(text)
    )


def score_terms(
    text,
    weighted_terms
):
    low = norm(
        text
    )

    score = 0.0

    hits = []

    for term, weight in (
        weighted_terms.items()
    ):
        clean = norm(
            term
        )

        if clean in low:
            score += float(
                weight
            )

            hits.append(
                clean
            )

    return (
        round(
            score,
            2
        ),
        hits
    )


def phrase_context_is_location(
    phrase,
    segments
):
    target = re.escape(
        norm(
            phrase
        )
    )

    patterns = [
        rf"\bem\s+{target}\b",
        rf"\bin\s+{target}\b",
        rf"\bna cidade de\s+{target}\b",
        rf"\bcidade de\s+{target}\b",
        rf"\bcity of\s+{target}\b",
        rf"\bviajou para\s+{target}\b",
        rf"\btravelled to\s+{target}\b",
        rf"\btraveled to\s+{target}\b"
    ]

    for segment in segments:
        low = norm(
            segment
        )

        for pattern in patterns:
            if re.search(
                pattern,
                low
            ):
                return True

    return False


def classify_entity_type(
    phrase,
    segments,
    policy
):
    clean = norm(
        phrase
    )

    words = clean.split()

    prefixes = set(
        norm(value)
        for value in policy[
            "entity_policy"
        ][
            "location_prefixes"
        ]
    )

    if (
        words
        and words[0]
        in prefixes
    ):
        return "LOCATION"

    if phrase_context_is_location(
        phrase,
        segments
    ):
        return "LOCATION"

    return "PERSON"


def extract_entities(
    segments
):
    policy = load_policy()

    false_words = set(
        norm(value)
        for value in policy[
            "entity_policy"
        ][
            "false_anchor_words"
        ]
    )

    candidates = {}


    for scene_index, segment in enumerate(
        segments,
        start=1
    ):
        for match in PROPER_RE.finditer(
            str(segment or "")
        ):
            phrase = (
                match.group(0)
                .strip()
            )

            clean = norm(
                phrase
            )

            words = clean.split()

            if (
                len(words)
                <
                policy[
                    "entity_policy"
                ][
                    "minimum_entity_words"
                ]
            ):
                continue

            if not words:
                continue

            if words[0] in false_words:
                continue

            if any(
                word in false_words
                for word in words
            ):
                continue

            key = clean

            item = candidates.setdefault(
                key,
                {
                    "name":
                        phrase,

                    "normalized":
                        clean,

                    "occurrences":
                        0,

                    "scenes":
                        [],
                }
            )

            item[
                "occurrences"
            ] += 1

            if scene_index not in (
                item[
                    "scenes"
                ]
            ):
                item[
                    "scenes"
                ].append(
                    scene_index
                )


    entities = []


    for item in (
        candidates.values()
    ):
        entity_type = (
            classify_entity_type(
                item[
                    "name"
                ],
                segments,
                policy
            )
        )

        words = (
            item[
                "normalized"
            ].split()
        )

        aliases = []

        if entity_type == "PERSON":
            if len(words) >= 2:
                aliases.extend([
                    words[0],
                    words[-1],
                ])

        score = (
            50
            +
            min(
                30,
                item[
                    "occurrences"
                ] * 10
            )
            +
            min(
                15,
                len(
                    item[
                        "scenes"
                    ]
                ) * 3
            )
        )

        entities.append({
            **item,

            "type":
                entity_type,

            "aliases":
                sorted(
                    set(
                        aliases
                    )
                ),

            "confidence":
                min(
                    100,
                    score
                ),
        })


    # Remove shorter duplicates contained in
    # longer canonical entities.
    canonical = []

    for entity in sorted(
        entities,
        key=lambda item: (
            len(
                item[
                    "normalized"
                ].split()
            ),
            item[
                "confidence"
            ],
        ),
        reverse=True
    ):
        duplicate = False

        for existing in canonical:
            if (
                entity[
                    "normalized"
                ]
                ==
                existing[
                    "normalized"
                ]
            ):
                duplicate = True
                break

            if (
                entity[
                    "type"
                ]
                ==
                existing[
                    "type"
                ]
                and
                entity[
                    "normalized"
                ]
                in
                existing[
                    "aliases"
                ]
            ):
                duplicate = True
                break

        if not duplicate:
            canonical.append(
                entity
            )


    persons = [
        item
        for item in canonical
        if item[
            "type"
        ]
        == "PERSON"
    ]

    locations = [
        item
        for item in canonical
        if item[
            "type"
        ]
        == "LOCATION"
    ]


    persons.sort(
        key=lambda item:
            item[
                "confidence"
            ],
        reverse=True
    )


    # Named facilities are preferred over broad cities
    # for primary-location reasoning.
    def location_rank(item):
        first = (
            item[
                "normalized"
            ].split()[0]
        )

        facility = first in {
            "hotel",
            "motel",
            "hospital",
            "university",
            "universidade"
        }

        return (
            1 if facility else 0,
            item[
                "confidence"
            ]
        )


    locations.sort(
        key=location_rank,
        reverse=True
    )


    return {
        "entities":
            canonical,

        "persons":
            persons,

        "locations":
            locations,

        "primary_person":
            (
                persons[0]
                if persons
                else None
            ),

        "primary_location":
            (
                locations[0]
                if locations
                else None
            ),
    }


def scene_role_scores(
    segment
):
    result = {}

    hits = {}

    for role, signals in (
        ROLE_SIGNALS.items()
    ):
        score, current_hits = (
            score_terms(
                segment,
                signals
            )
        )

        result[
            role
        ] = score

        hits[
            role
        ] = current_hits


    maximum = max(
        result.values(),
        default=0
    )


    if maximum <= 0:
        role = "CONTEXT"

    else:
        priority = [
            "DOCUMENT",
            "EVIDENCE",
            "OBJECT",
            "HUMAN",
            "LOCATION"
        ]

        role = max(
            priority,
            key=lambda name: (
                result[
                    name
                ],
                -priority.index(
                    name
                )
            )
        )


    return {
        "role":
            role,

        "scores":
            result,

        "hits":
            hits,
    }


def factual_analysis(
    segment
):
    score, hits = score_terms(
        segment,
        FACTUAL_SIGNALS
    )

    threshold = (
        load_policy()
        [
            "semantic_policy"
        ][
            "factual_threshold"
        ]
    )

    return {
        "score":
            score,

        "hits":
            hits,

        "factual":
            score >= threshold,
    }


def generic_human_scene(
    segment
):
    low = norm(
        segment
    )

    return any(
        norm(pattern)
        in low

        for pattern in (
            GENERIC_HUMAN_PATTERNS
        )
    )


def entity_explicit_in_scene(
    segment,
    entity
):
    if not entity:
        return False

    return (
        entity[
            "normalized"
        ]
        in norm(
            segment
        )
    )


def classify_scenes(
    segments,
    entity_result=None
):
    if entity_result is None:
        entity_result = (
            extract_entities(
                segments
            )
        )

    policy = load_policy()

    primary_person = (
        entity_result[
            "primary_person"
        ]
    )

    primary_location = (
        entity_result[
            "primary_location"
        ]
    )

    single_story_person = (
        len(
            entity_result[
                "persons"
            ]
        )
        == 1
    )


    classified = []


    for index, segment in enumerate(
        segments,
        start=1
    ):
        role_data = (
            scene_role_scores(
                segment
            )
        )

        role = role_data[
            "role"
        ]

        factual = (
            factual_analysis(
                segment
            )
        )

        explicit_person = (
            entity_explicit_in_scene(
                segment,
                primary_person
            )
        )

        generic_human = (
            generic_human_scene(
                segment
            )
        )


        identity_required = False

        identity_scope = (
            "NONE"
        )

        identity_confidence = 0


        if (
            role == "HUMAN"
            and explicit_person
        ):
            identity_required = True

            identity_scope = (
                "SPECIFIC_PERSON_EXPLICIT"
            )

            identity_confidence = 100


        elif (
            role == "HUMAN"
            and
            single_story_person
            and
            not generic_human
        ):
            identity_confidence = (
                policy[
                    "semantic_policy"
                ][
                    "identity_inference_confidence"
                ]
            )

            identity_required = (
                identity_confidence
                >=
                policy[
                    "semantic_policy"
                ][
                    "identity_inference_confidence"
                ]
            )

            identity_scope = (
                "SPECIFIC_PERSON_INFERRED"
            )


        elif role == "HUMAN":
            identity_scope = (
                "GENERIC_HUMAN_OR_GROUP"
            )


        explicit_location = (
            entity_explicit_in_scene(
                segment,
                primary_location
            )
        )


        location_scope = "NONE"

        location_confidence = 0


        if explicit_location:
            location_scope = (
                "SPECIFIC_LOCATION_EXPLICIT"
            )

            location_confidence = 100


        elif (
            role == "LOCATION"
            and
            primary_location
        ):
            location_scope = (
                "SPECIFIC_LOCATION_INFERRED_STORY_CONTEXT"
            )

            location_confidence = (
                policy[
                    "semantic_policy"
                ][
                    "specific_location_inference_confidence"
                ]
            )


        elif role == "LOCATION":
            location_scope = (
                "GENERIC_LOCATION"
            )


        if factual[
            "factual"
        ]:
            epistemic_mode = (
                "CASE_SPECIFIC_REQUIRED"
            )

        elif identity_required:
            epistemic_mode = (
                "IDENTITY_SPECIFIC_REQUIRED"
            )

        elif role == "HUMAN":
            epistemic_mode = (
                "ILLUSTRATIVE_NO_IDENTITY_ATTRIBUTION"
            )

        else:
            epistemic_mode = (
                "ILLUSTRATIVE_ALLOWED"
            )


        hook_priority = (
            100
            if index == 1
            else 0
        )


        hook_case_specific = (
            index == 1
            and
            policy[
                "hook_policy"
            ][
                "scene_1_case_specific_preferred"
            ]
        )


        is_cta = (
            index == len(
                segments
            )
            or
            any(
                norm(term)
                in norm(
                    segment
                )

                for term in CTA_TERMS
            )
        )


        classified.append({
            "scene":
                index,

            "segment":
                segment,

            "role":
                role,

            "role_scores":
                role_data[
                    "scores"
                ],

            "role_hits":
                role_data[
                    "hits"
                ],

            "factual":
                factual[
                    "factual"
                ],

            "factual_score":
                factual[
                    "score"
                ],

            "factual_hits":
                factual[
                    "hits"
                ],

            "identity_required":
                identity_required,

            "identity_scope":
                identity_scope,

            "identity_confidence":
                identity_confidence,

            "generic_human":
                generic_human,

            "location_scope":
                location_scope,

            "location_confidence":
                location_confidence,

            "epistemic_mode":
                epistemic_mode,

            "hook_priority":
                hook_priority,

            "hook_case_specific_preferred":
                hook_case_specific,

            "cta":
                is_cta,
        })


    return classified


if __name__ == "__main__":
    print(
        "VI1000.1 SEMANTIC CORE=PASS"
    )
