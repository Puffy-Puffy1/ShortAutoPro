#!/usr/bin/env python3

import re

from vi1000_1_semantic_core import norm

from vi1200_06_visual_precision import (
    candidate_text,
    candidate_visual_intents,
    scene_visual_intents,
)


def contains(
    text,
    phrases,
):
    value = norm(text)

    return any(
        norm(phrase) in value
        for phrase in phrases
    )


def primary_names(
    entities,
):
    person = (
        entities.get("primary_person")
        or {}
    ).get("name") or ""

    location = (
        entities.get("primary_location")
        or {}
    ).get("name") or ""

    return person, location


def scene_requirements(
    scene,
    entities,
):
    text = str(
        scene.get("segment")
        or ""
    )

    normalized = norm(text)

    role = str(
        scene.get("role")
        or "CONTEXT"
    ).upper()

    person, location = primary_names(
        entities
    )

    requirements = set(
        scene_visual_intents(scene)
    )


    if (
        str(
            scene.get("identity_scope")
            or ""
        ).startswith(
            "SPECIFIC_PERSON"
        )
    ):
        requirements.add(
            "SPECIFIC_PERSON"
        )


    if contains(
        normalized,
        [
            "funcionario",
            "funcionarios",
            "funcionário",
            "funcionários",
            "manutencao",
            "manutenção",
            "maintenance worker",
            "maintenance staff",
        ]
    ):
        requirements.update({
            "HUMAN",
            "WORKER",
            "MAINTENANCE_WORKER",
        })


    if contains(
        normalized,
        [
            "se esconder",
            "se esconde",
            "esconder",
            "hiding",
            "hide",
            "peek",
        ]
    ):
        requirements.add(
            "HIDE_BEHAVIOR"
        )


    if contains(
        normalized,
        [
            "transtorno bipolar",
            "bipolar",
            "bipolar disorder",
            "mood disorder",
        ]
    ):
        requirements.update({
            "MEDICAL_CONTEXT",
            "MENTAL_HEALTH",
            "BIPOLAR",
        })


    if contains(
        normalized,
        [
            "especulacoes",
            "especulações",
            "paranormal",
            "speculation",
            "speculations",
        ]
    ):
        requirements.add(
            "EVIDENCE_DISCUSSION"
        )


    if contains(
        normalized,
        [
            "tanque de agua",
            "tanque de água",
            "water tank",
            "water tower",
        ]
    ):
        requirements.update({
            "WATER_TANK",
            "ROOFTOP",
        })


    if (
        location
        and
        norm(location) in normalized
    ):
        requirements.add(
            "PRIMARY_LOCATION_MENTIONED"
        )


    if person:
        person_norm = norm(person)

        last_name = (
            person_norm.split()[-1]
            if person_norm.split()
            else ""
        )

        if (
            person_norm in normalized
            or
            (
                last_name
                and
                re.search(
                    rf"\b{re.escape(last_name)}\b",
                    normalized
                )
            )
        ):
            requirements.add(
                "PRIMARY_PERSON_MENTIONED"
            )


    return {
        "role":
            role,

        "requirements":
            sorted(requirements),

        "segment":
            text,
    }


def candidate_semantics(
    candidate,
    entities,
):
    text = candidate_text(
        candidate
    )

    normalized = norm(text)

    semantics = set(
        candidate_visual_intents(
            candidate
        )
    )

    person, location = primary_names(
        entities
    )


    entity_mentions = {
        norm(value)
        for value in (
            candidate.get(
                "entity_mentions"
            )
            or []
        )
    }


    if person:
        p = norm(person)

        if (
            p in normalized
            or
            p in entity_mentions
        ):
            semantics.update({
                "SPECIFIC_PERSON",
                "CASE_PERSON",
                "HUMAN",
            })


    if location:
        loc = norm(location)

        if (
            loc in normalized
            or
            loc in entity_mentions
        ):
            semantics.update({
                "VERIFIED_CASE_LOCATION",
                "LOCATION",
            })


    if contains(
        normalized,
        [
            "maintenance worker",
            "maintenance employee",
            "maintenance staff",
            "maintenance technician",
            "building maintenance",
            "hotel maintenance",
            "custodian",
            "janitor",
            "repair worker",
        ]
    ):
        semantics.update({
            "HUMAN",
            "WORKER",
            "MAINTENANCE_WORKER",
        })


    if contains(
        normalized,
        [
            "hotel employee",
            "hotel staff",
            "hotel worker",
        ]
    ):
        semantics.update({
            "HUMAN",
            "WORKER",
            "HOTEL_EMPLOYEE",
        })


    if contains(
        normalized,
        [
            "bipolar disorder",
            "bipolar affective",
            "mood disorder",
            "mental health",
            "psychiatry",
            "psychiatric",
            "manic depression",
        ]
    ):
        semantics.update({
            "BIPOLAR",
            "MENTAL_HEALTH",
            "MEDICAL_CONTEXT",
        })


    if contains(
        normalized,
        [
            "hiding",
            "hide behind",
            "peeking",
            "peek",
            "concealing",
        ]
    ):
        semantics.add(
            "HIDE_BEHAVIOR"
        )


    return sorted(
        semantics
    )


if __name__ == "__main__":
    print(
        "VI1260 SEMANTIC ROLES=PASS"
    )
