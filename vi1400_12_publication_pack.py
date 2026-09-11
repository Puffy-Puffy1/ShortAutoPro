#!/usr/bin/env python3

import re

from vi1400_01_common import (
    ROOT,
    TMP,
    load_json,
    save_json,
)


def tagify(
    value,
):
    value = re.sub(
        r"[^\wÀ-ÿ]+",
        "",
        str(
            value
            or ""
        ),
        flags=re.UNICODE,
    )


    return (
        "#"
        + value

        if value

        else None
    )


def infer_story_entities():
    blueprint = load_json(
        ROOT
        / "temp"
        / "vi1000_launch"
        / "launch_blueprint.json",
        {}
    )


    scenes = (
        blueprint.get(
            "scenes"
        )
        or []
    )


    segments = [
        str(
            item.get(
                "segment"
            )
            or ""
        )

        for item
        in scenes

        if isinstance(
            item,
            dict
        )
    ]


    try:

        from vi1000_1_semantic_core import (
            extract_entities,
        )


        entities = extract_entities(
            segments
        )


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


        person = (
            person.get(
                "name"
            )

            if isinstance(
                person,
                dict
            )

            else str(
                person
                or ""
            )
        )


        location = (
            location.get(
                "name"
            )

            if isinstance(
                location,
                dict
            )

            else str(
                location
                or ""
            )
        )


        return (
            person
            or "",
            location
            or "",
        )


    except Exception:

        return (
            "",
            "",
        )


def run():
    artifacts = load_json(
        TMP
        / "artifacts.json"
    )


    plan = load_json(
        artifacts.get(
            "selection_plan"
        )
        or "",
        {}
    )


    selected = (
        plan.get(
            "selected"
        )
        or {}
    )


    source_titles = [
        (
            selected.get(
                str(
                    number
                ),
                {}
            ).get(
                "candidate"
            )
            or {}
        ).get(
            "title",
            ""
        )

        for number in range(
            1,
            13
        )
    ]


    person, location = (
        infer_story_entities()
    )


    subject = (
        person
        or
        "O caso"
    )


    if (
        person
        and
        location
    ):

        titles = [
            (
                f"{person}: o que aconteceu "
                f"em {location}?"
            ),

            (
                f"O mistério de {person} "
                f"em {location}"
            ),

            (
                f"Os detalhes do caso "
                f"{person}"
            ),
        ]


    elif person:

        titles = [
            f"O que aconteceu com {person}?",
            f"Os detalhes do caso {person}",
            f"O mistério envolvendo {person}",
        ]


    else:

        titles = [
            "O que realmente aconteceu?",
            "Os detalhes que mudam este caso",
            "O mistério explicado em menos de um minuto",
        ]


    description = (
        f"Uma reconstrução visual sobre {subject}"
        +
        (
            f" em {location}"
            if location
            else ""
        )
        +
        ", distinguindo registros do caso, "
        "contexto e imagens ilustrativas."
    )


    hashtags = [
        value

        for value in [
            tagify(
                person
            ),

            tagify(
                location
            ),

            "#Mistério",
            "#Shorts",
        ]

        if value
    ]


    pack = {
        "title_options":
            titles,

        "description":
            description,

        "hashtags":
            hashtags,

        "disclosure_policy":
            (
                "Nunca apresentar imagem ilustrativa "
                "como registro real do caso."
            ),

        "source_titles": [
            title

            for title
            in source_titles

            if title
        ],

        "primary_person":
            person,

        "primary_location":
            location,

        "publication_executed":
            False,
    }


    save_json(
        TMP
        / "publication_pack.json",
        pack
    )


    return pack


if __name__ == "__main__":

    pack = run()


    print(
        "VI1400 PUBLICATION PACK=PASS"
    )

    print(
        "TITLE=",
        pack[
            "title_options"
        ][
            0
        ]
    )

    print(
        "PUBLICATION_EXECUTED=False"
    )
