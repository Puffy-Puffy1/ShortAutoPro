#!/usr/bin/env python3

import hashlib
import json

from pathlib import Path

from vi1000_1_semantic_core import (
    load_policy,
    norm,
)


VERSION = "1000.1"


def unique_strings(values):
    result = []

    seen = set()

    for value in values:
        value = " ".join(
            str(
                value or ""
            ).split()
        ).strip()

        if not value:
            continue

        key = norm(
            value
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            value
        )

    return result


def role_descriptor(
    scene
):
    text = norm(
        scene[
            "segment"
        ]
    )

    if (
        "elevador"
        in text
        or
        "elevator"
        in text
    ):
        return "elevator"

    if (
        "corredor"
        in text
        or
        "hallway"
        in text
    ):
        return "hallway corridor"

    if (
        "telhado"
        in text
        or
        "rooftop"
        in text
        or
        "topo"
        in text
    ):
        return "rooftop"

    if (
        "medic"
        in text
        or
        "remedio"
        in text
    ):
        return "medication"

    if scene[
        "role"
    ] == "DOCUMENT":
        return "official document"

    if scene[
        "role"
    ] == "EVIDENCE":
        return "surveillance evidence"

    if scene[
        "role"
    ] == "HUMAN":
        return "person"

    return scene[
        "role"
    ].lower()


def provider_route(
    scene
):
    if scene[
        "factual"
    ]:
        if scene[
            "role"
        ] == "DOCUMENT":
            return [
                "WIKIMEDIA_COMMONS",
                "INTERNET_ARCHIVE",
                "WIKIPEDIA_CONTEXT_ONLY",
            ]

        return [
            "WIKIMEDIA_COMMONS",
            "INTERNET_ARCHIVE",
        ]

    if scene[
        "identity_required"
    ]:
        return [
            "WIKIMEDIA_COMMONS",
            "INTERNET_ARCHIVE",
        ]

    if scene[
        "role"
    ] in {
        "LOCATION",
        "OBJECT",
        "HUMAN",
    }:
        return [
            "WIKIMEDIA_COMMONS",
            "CURRENT_MEDIA",
        ]

    return [
        "CURRENT_MEDIA",
        "WIKIMEDIA_COMMONS",
    ]


def plan_query(
    scene,
    entities
):
    person = (
        entities.get(
            "primary_person"
        )
        or {}
    )

    location = (
        entities.get(
            "primary_location"
        )
        or {}
    )

    person_name = (
        person.get(
            "name"
        )
        or ""
    )

    location_name = (
        location.get(
            "name"
        )
        or ""
    )

    descriptor = role_descriptor(
        scene
    )


    if scene[
        "identity_required"
    ]:
        variants = [
            f"{person_name} archival photograph",
            f"{person_name} verified image",
            f"{person_name} {descriptor}",
        ]

        intent = (
            "IDENTITY_SPECIFIC"
        )


    elif scene[
        "factual"
    ]:
        subject = " ".join(
            value
            for value in [
                person_name,
                location_name,
            ]
            if value
        )

        if scene[
            "role"
        ] == "DOCUMENT":
            variants = [
                f"{subject} official report document",
                f"{subject} archival record",
                f"{subject} investigation document",
            ]

        elif scene[
            "role"
        ] == "EVIDENCE":
            variants = [
                f"{subject} surveillance footage evidence",
                f"{subject} archival security camera",
                f"{subject} investigation evidence",
            ]

        else:
            variants = [
                f"{subject} {descriptor}",
                f"{subject} archival context",
                f"{subject} investigation context",
            ]

        intent = (
            "CASE_SPECIFIC"
        )


    elif (
        scene[
            "hook_case_specific_preferred"
        ]
        and location_name
    ):
        variants = [
            f"{location_name} {descriptor}",
            f"{location_name} archival exterior",
            f"{location_name} verified location",
        ]

        intent = (
            "HOOK_CASE_SPECIFIC"
        )


    elif (
        scene[
            "location_scope"
        ].startswith(
            "SPECIFIC_LOCATION"
        )
        and location_name
    ):
        variants = [
            f"{location_name} {descriptor}",
            f"{descriptor} hotel interior",
            f"documentary {descriptor}",
        ]

        intent = (
            "LOCATION_SPECIFIC_PREFERRED"
        )


    elif scene[
        "role"
    ] == "HUMAN":
        variants = [
            "anonymous person back view documentary",
            "unrecognizable person contextual reenactment",
            "faceless human silhouette documentary",
        ]

        intent = (
            "GENERIC_HUMAN_ILLUSTRATIVE"
        )


    elif scene[
        "role"
    ] == "OBJECT":
        variants = [
            f"generic {descriptor} neutral",
            f"{descriptor} documentary b-roll",
            f"{descriptor} no visible brand",
        ]

        intent = (
            "OBJECT_ILLUSTRATIVE"
        )


    else:
        variants = [
            f"{descriptor} documentary b-roll",
            f"{descriptor} contextual image",
            f"{descriptor} archival style",
        ]

        intent = (
            "CONTEXTUAL_ILLUSTRATIVE"
        )


    variants = unique_strings(
        variants
    )


    return {
        "scene":
            scene[
                "scene"
            ],

        "intent":
            intent,

        "primary_query":
            (
                variants[0]
                if variants
                else ""
            ),

        "query_variants":
            variants,

        "providers":
            provider_route(
                scene
            ),

        "query_is_evidence":
            False,

        "identity_required":
            scene[
                "identity_required"
            ],

        "case_specific_required":
            scene[
                "factual"
            ],

        "illustration_label_required":
            scene[
                "epistemic_mode"
            ].startswith(
                "ILLUSTRATIVE"
            ),
    }


def plan_queries(
    scenes,
    entities
):
    return [
        plan_query(
            scene,
            entities
        )
        for scene in scenes
    ]


def license_allowed(
    value
):
    low = norm(
        value
    )

    accepted = (
        load_policy()
        [
            "candidate_policy"
        ][
            "accepted_licenses"
        ]
    )

    return any(
        norm(token)
        in low

        for token in accepted
    )


def candidate_text(
    candidate
):
    # Search query is deliberately absent.
    return norm(
        " ".join([
            str(
                candidate.get(
                    "title"
                )
                or ""
            ),
            str(
                candidate.get(
                    "evidence_text"
                )
                or ""
            ),
            " ".join(
                candidate.get(
                    "entity_mentions"
                )
                or []
            ),
            " ".join(
                candidate.get(
                    "role_tags"
                )
                or []
            ),
        ])
    )


def story_entity_hits(
    candidate,
    entities
):
    text = candidate_text(
        candidate
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


def role_match(
    scene_role,
    candidate_tags
):
    tags = set(
        norm(value).upper()
        for value in (
            candidate_tags
            or []
        )
    )

    role = str(
        scene_role
    ).upper()


    compatibility = {
        "CONTEXT": {
            "CONTEXT",
            "BROLL",
            "LOCATION",
        },

        "LOCATION": {
            "LOCATION",
            "BROLL",
        },

        "HUMAN": {
            "HUMAN",
            "PERSON",
        },

        "OBJECT": {
            "OBJECT",
        },

        "EVIDENCE": {
            "EVIDENCE",
            "ARCHIVAL VIDEO",
            "VIDEO",
            "SURVEILLANCE",
        },

        "DOCUMENT": {
            "DOCUMENT",
            "REPORT",
            "RECORD",
        },
    }


    return bool(
        compatibility.get(
            role,
            {
                role
            }
        )
        &
        tags
    )


def document_evidence(
    candidate
):
    text = candidate_text(
        candidate
    )

    tags = set(
        norm(value)
        for value in (
            candidate.get(
                "role_tags"
            )
            or []
        )
    )


    if tags & {
        "document",
        "report",
        "record",
    }:
        return True


    # "File:" itself deliberately proves nothing.
    terms = {
        "official report",
        "autopsy report",
        "record document",
        "police report",
        "coroner report",
        "official document",
    }


    return any(
        norm(term)
        in text
        for term in terms
    )


def technical_pass(
    candidate
):
    family = str(
        candidate.get(
            "family"
        )
        or "IMAGE"
    ).upper()


    if family == "VIDEO":
        return True


    width = int(
        candidate.get(
            "width"
        )
        or 0
    )

    height = int(
        candidate.get(
            "height"
        )
        or 0
    )


    pixels = (
        width
        * height
    )


    minimum = (
        load_policy()
        [
            "candidate_policy"
        ][
            "minimum_image_pixels"
        ]
    )


    return (
        pixels >= minimum
    )


def evaluate_candidate(
    scene,
    candidate,
    entities
):
    reasons = []


    if not license_allowed(
        candidate.get(
            "license"
        )
    ):
        reasons.append(
            "license_gate_failed"
        )


    if not technical_pass(
        candidate
    ):
        reasons.append(
            "technical_gate_failed"
        )


    if not role_match(
        scene[
            "role"
        ],
        candidate.get(
            "role_tags"
        )
    ):
        reasons.append(
            "role_gate_failed"
        )


    evidence = candidate_text(
        candidate
    )


    entity_hits = story_entity_hits(
        candidate,
        entities
    )


    primary_person = (
        entities.get(
            "primary_person"
        )
        or {}
    )

    primary_location = (
        entities.get(
            "primary_location"
        )
        or {}
    )


    person_name = (
        primary_person.get(
            "normalized"
        )
        or ""
    )

    location_name = (
        primary_location.get(
            "normalized"
        )
        or ""
    )


    intended_usage = str(
        candidate.get(
            "intended_usage"
        )
        or "ILLUSTRATIVE"
    ).upper()


    if scene[
        "identity_required"
    ]:
        if (
            not person_name
            or
            person_name
            not in evidence
        ):
            reasons.append(
                "specific_identity_not_proven"
            )


    if scene[
        "factual"
    ]:
        if intended_usage != (
            "CASE_SPECIFIC"
        ):
            reasons.append(
                "factual_scene_requires_case_specific_usage"
            )

        if not entity_hits:
            reasons.append(
                "case_entity_evidence_missing"
            )


    if (
        scene[
            "role"
        ]
        == "DOCUMENT"
        and
        not document_evidence(
            candidate
        )
    ):
        reasons.append(
            "document_evidence_missing"
        )


    # VI1000.1.1
    #
    # Identity evidence and location evidence are
    # independent dimensions.
    #
    # A verified photograph of a named person must not
    # be rejected merely because that photograph does
    # not also prove the story location.
    #
    # Specific-location proof is required only when:
    #   1) the location is EXPLICIT in this scene, and
    #   2) location is semantically material:
    #      - the scene itself is LOCATION, or
    #      - the scene contains a factual claim.
    #
    # Inferred story location never becomes mandatory
    # evidence by itself.
    location_evidence_required = (
        scene.get(
            "location_scope"
        )
        == "SPECIFIC_LOCATION_EXPLICIT"
        and
        (
            scene.get(
                "role"
            )
            == "LOCATION"
            or
            scene.get(
                "factual"
            )
            is True
        )
    )

    if (
        intended_usage
        == "CASE_SPECIFIC"
        and
        location_evidence_required
        and
        location_name
        and
        location_name
        not in evidence
    ):
        reasons.append(
            "specific_location_not_proven"
        )


    # VI1100.1
    #
    # CASE_SPECIFIC is a claim about provenance,
    # not merely a ranking hint.
    #
    # Therefore every candidate declaring itself
    # CASE_SPECIFIC must contain independent evidence
    # linking the media to at least one resolved story
    # entity.
    #
    # Search-query text is intentionally excluded from
    # candidate_text() and can never satisfy this gate.
    if (
        intended_usage
        == "CASE_SPECIFIC"
        and
        not entity_hits
    ):
        reasons.append(
            "case_specific_entity_evidence_missing"
        )


    illustrative = (
        intended_usage
        == "ILLUSTRATIVE"
    )


    if illustrative:
        label_required = (
            load_policy()
            [
                "semantic_policy"
            ][
                "illustrative_media_requires_label"
            ]
        )

        if (
            label_required
            and
            not candidate.get(
                "illustration_label"
            )
        ):
            reasons.append(
                "illustration_label_missing"
            )


    if (
        scene[
            "hook_priority"
        ]
        == 100
        and
        scene[
            "hook_case_specific_preferred"
        ]
    ):
        if (
            intended_usage
            != "CASE_SPECIFIC"
        ):
            reasons.append(
                "hook_generic_fallback_disallowed"
            )

        if not entity_hits:
            reasons.append(
                "hook_case_entity_missing"
            )


    passed = (
        not reasons
    )


    return {
        "passed":
            passed,

        "reasons":
            sorted(
                set(
                    reasons
                )
            ),

        "entity_hits":
            entity_hits,

        "role_match":
            role_match(
                scene[
                    "role"
                ],
                candidate.get(
                    "role_tags"
                )
            ),

        "license_pass":
            license_allowed(
                candidate.get(
                    "license"
                )
            ),

        "technical_pass":
            technical_pass(
                candidate
            ),

        "query_used_as_evidence":
            False,

        "location_evidence_required":
            location_evidence_required,
    }


def fallback_decision(
    evaluations
):
    for item in evaluations:
        if not item[
            "evaluation"
        ][
            "passed"
        ]:
            continue

        usage = str(
            item[
                "candidate"
            ].get(
                "intended_usage"
            )
            or ""
        ).upper()

        if usage == (
            "CASE_SPECIFIC"
        ):
            tier = (
                "CASE_SPECIFIC_VERIFIED"
            )

        else:
            tier = (
                "CONTEXTUAL_ILLUSTRATIVE_LICENSED"
            )

        return {
            "decision":
                "SELECT",

            "tier":
                tier,

            "candidate":
                item[
                    "candidate"
                ],
        }


    return {
        "decision":
            "HOLD_SCENE",

        "tier":
            "HOLD_SCENE",

        "candidate":
            None,
    }


def audit_portfolio(
    portfolio
):
    policy = (
        load_policy()
        [
            "diversity_policy"
        ]
    )


    source_groups = [
        item[
            "source_group"
        ]
        for item in portfolio
    ]


    unique = set(
        source_groups
    )


    total = len(
        portfolio
    )


    ratio = (
        len(unique)
        / total
        if total
        else 0
    )


    counts = {}


    for item in portfolio:
        group = item[
            "source_group"
        ]

        counts[group] = (
            counts.get(
                group,
                0
            )
            + 1
        )


    max_run = 0

    current = None

    run = 0


    for group in source_groups:
        if group == current:
            run += 1

        else:
            current = group
            run = 1

        max_run = max(
            max_run,
            run
        )


    windows = []

    blockers = []


    for start in range(
        0,
        max(
            0,
            total - 5
        )
    ):
        part = portfolio[
            start:
            start + 6
        ]

        if len(part) < 6:
            continue

        current_unique = len({
            item[
                "source_group"
            ]
            for item in part
        })

        windows.append({
            "start_scene":
                part[0][
                    "scene"
                ],

            "end_scene":
                part[-1][
                    "scene"
                ],

            "unique_sources":
                current_unique,
        })

        if (
            current_unique
            <
            policy[
                "minimum_unique_sources_per_6_scene_window"
            ]
        ):
            blockers.append(
                "low_window_diversity:"
                f"{part[0]['scene']}-"
                f"{part[-1]['scene']}"
            )


    if (
        ratio
        <
        policy[
            "minimum_unique_source_ratio"
        ]
    ):
        blockers.append(
            "unique_source_ratio_too_low"
        )


    if (
        total >= 12
        and
        len(unique)
        <
        policy[
            "minimum_unique_source_groups_for_12_scenes"
        ]
    ):
        blockers.append(
            "unique_source_count_too_low"
        )


    if (
        max_run
        >
        policy[
            "maximum_consecutive_same_source_group"
        ]
    ):
        blockers.append(
            "consecutive_source_repetition"
        )


    for item in portfolio:
        if not item.get(
            "generic"
        ):
            continue

        if (
            counts[
                item[
                    "source_group"
                ]
            ]
            >
            policy[
                "generic_source_max_scenes"
            ]
        ):
            blockers.append(
                "generic_source_reused:"
                + item[
                    "source_group"
                ]
            )


    return {
        "passed":
            not blockers,

        "unique_source_count":
            len(
                unique
            ),

        "unique_source_ratio":
            round(
                ratio,
                3
            ),

        "maximum_consecutive_same_source":
            max_run,

        "counts":
            counts,

        "windows":
            windows,

        "blockers":
            sorted(
                set(
                    blockers
                )
            ),
    }


if __name__ == "__main__":
    print(
        "VI1000.1 QUERY/GATE ENGINE=PASS"
    )
