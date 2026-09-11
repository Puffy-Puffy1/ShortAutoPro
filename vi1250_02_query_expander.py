#!/usr/bin/env python3

from vi1000_1_semantic_core import (
    norm,
)

from vi1200_06_visual_precision import (
    scene_visual_intents,
)


def unique(
    values,
    limit=10,
):
    output = []

    seen = set()


    for value in values:

        value = " ".join(
            str(
                value or ""
            ).split()
        )


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

        output.append(
            value
        )


        if len(
            output
        ) >= limit:
            break


    return output


def entity_names(
    entities
):
    person = (
        entities.get(
            "primary_person"
        )
        or {}
    ).get(
        "name"
    ) or ""

    location = (
        entities.get(
            "primary_location"
        )
        or {}
    ).get(
        "name"
    ) or ""


    return (
        person,
        location
    )


def previous_failure_reasons(
    previous_scene
):
    reasons = []


    if not previous_scene:
        return reasons


    for item in (
        previous_scene.get(
            "evaluated"
        )
        or []
    ):

        gate = (
            item.get(
                "combined_gate"
            )
            or {}
        )


        reasons.extend(
            gate.get(
                "reasons"
            )
            or []
        )


    return sorted(
        set(
            reasons
        )
    )


def expanded_queries(
    scene,
    query_plan,
    entities,
    previous_scene=None,
    limit=10,
):
    person, location = (
        entity_names(
            entities
        )
    )


    role = str(
        scene.get(
            "role"
        )
        or ""
    ).upper()


    intents = scene_visual_intents(
        scene
    )


    values = []


    values.extend(
        query_plan.get(
            "query_variants"
        )
        or []
    )


    if scene.get(
        "identity_required"
    ):

        values.extend([
            f"{person} photograph",
            f"{person} photo",
            f"{person} archival image",
            f"{person} surveillance",
            f"{person} elevator",
            f"{person} CCTV",
        ])


    if "ELEVATOR" in intents:

        values.extend([
            f"{location} elevator",
            f"{location} elevator interior",
            f"{person} elevator",
            "hotel elevator interior",
            "elevator doors hotel",
        ])


    if "HALLWAY" in intents:

        values.extend([
            f"{location} hallway",
            f"{location} corridor",
            "hotel hallway interior",
            "hotel corridor interior",
            "empty hotel hallway",
        ])


    if "SURVEILLANCE" in intents:

        values.extend([
            f"{person} surveillance footage",
            f"{person} security camera",
            f"{person} CCTV",
            f"{person} elevator video",
            f"{location} surveillance footage",
        ])


    if "MEDICATION" in intents:

        values.extend([
            "prescription medication bottle",
            "medicine box",
            "medication package",
            "prescription medicine",
            "generic medication bottle",
        ])


    if (
        "ROOFTOP"
        in intents
        or
        "WATER_TANK"
        in intents
    ):

        values.extend([
            f"{location} rooftop",
            f"{location} roof",
            f"{location} water tank",
            "hotel rooftop water tanks",
            "building rooftop water tanks",
            "rooftop water tower",
            "urban rooftop water tanks",
        ])


    if role == "HUMAN":

        if not scene.get(
            "identity_required"
        ):

            values.extend([
                "hotel maintenance worker",
                "maintenance worker rooftop",
                "hotel employee corridor",
                "maintenance staff building",
                "anonymous hotel worker",
                "worker checking water tank",
            ])


    if role == "DOCUMENT":

        values.extend([
            f"{person} official report",
            f"{person} autopsy report",
            f"{person} coroner report",
            f"{person} investigation report",
            f"{person} official record",
            f"{person} case document",
        ])


    if (
        role == "CONTEXT"
        and
        not (
            intents
            &
            {
                "MEDICATION",
                "ELEVATOR",
                "HALLWAY",
                "ROOFTOP",
                "WATER_TANK",
                "SURVEILLANCE",
            }
        )
    ):

        values.extend([
            f"{location} Los Angeles",
            f"{location} building",
            f"{location} exterior",
            f"{person} case",
            f"{person} {location}",
        ])


    failures = previous_failure_reasons(
        previous_scene
    )


    if any(
        "human_visual_required"
        in reason
        for reason in failures
    ):

        values.extend([
            "hotel employee person",
            "maintenance worker person",
            "hotel worker documentary",
        ])


    if any(
        "visual_subtype_mismatch:rooftop"
        in reason
        for reason in failures
    ):

        values.extend([
            "rooftop water tank",
            "hotel roof water tank",
        ])


    return {
        "scene":
            scene[
                "scene"
            ],

        "role":
            role,

        "intents":
            sorted(
                intents
            ),

        "previous_failure_reasons":
            failures,

        "queries":
            unique(
                values,
                limit=limit
            ),
    }


if __name__ == "__main__":
    print(
        "VI1250 QUERY EXPANDER=PASS"
    )
