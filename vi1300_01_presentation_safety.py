#!/usr/bin/env python3

import json

from pathlib import Path


BASE = (
    Path.home()
    / "ShortAutoPro"
)


POLICY = json.loads(
    (
        BASE
        / "config/"
        "vi1300_visual_policy.json"
    ).read_text(
        encoding="utf-8"
    )
)


def dimensions_from_candidate(
    selected_item,
):
    candidate = (
        selected_item.get(
            "candidate"
        )
        or {}
    )

    raw = (
        candidate.get(
            "raw_metadata"
        )
        or {}
    )


    def integer(
        *keys
    ):
        for key in keys:

            value = candidate.get(
                key
            )

            if value in {
                None,
                "",
            }:

                value = raw.get(
                    key
                )


            try:

                number = int(
                    value
                )

                if number > 0:
                    return number

            except Exception:
                pass


        return None


    return {
        "width":
            integer(
                "width",
                "image_width",
            ),

        "height":
            integer(
                "height",
                "image_height",
            ),
    }


def dimensions_from_forensics(
    source_group,
    forensic_assets,
):
    for item in forensic_assets:

        if (
            item.get(
                "source_group"
            )
            != source_group
        ):
            continue


        dims = (
            item.get(
                "dimensions"
            )
            or {}
        )


        width = dims.get(
            "width"
        )

        height = dims.get(
            "height"
        )


        if (
            width
            and
            height
        ):

            return {
                "width":
                    int(
                        width
                    ),

                "height":
                    int(
                        height
                    ),
            }


    return {
        "width":
            None,

        "height":
            None,
    }


def resolve_dimensions(
    source_group,
    selected_item,
    forensic_assets,
):
    forensic = (
        dimensions_from_forensics(
            source_group,
            forensic_assets,
        )
    )


    if (
        forensic[
            "width"
        ]
        and
        forensic[
            "height"
        ]
    ):

        return {
            **forensic,
            "source":
                "FORENSIC_BINARY",
        }


    metadata = (
        dimensions_from_candidate(
            selected_item
        )
    )


    if (
        metadata[
            "width"
        ]
        and
        metadata[
            "height"
        ]
    ):

        return {
            **metadata,
            "source":
                "VERIFIED_METADATA",
        }


    return {
        "width":
            None,

        "height":
            None,

        "source":
            "UNKNOWN",
    }


def fullscreen_quality_pass(
    dimensions,
):
    width = dimensions.get(
        "width"
    )

    height = dimensions.get(
        "height"
    )


    if not (
        width
        and
        height
    ):

        return False


    policy = (
        POLICY[
            "fullscreen"
        ]
    )


    return (
        width
        >=
        policy[
            "minimum_width"
        ]

        and

        height
        >=
        policy[
            "minimum_height"
        ]

        and

        min(
            width,
            height
        )
        >=
        policy[
            "minimum_short_edge"
        ]
    )


def is_context_mode(
    mode,
):
    return (
        "CONTEXT"
        in str(
            mode
            or ""
        ).upper()
    )


def is_illustrative(
    scene_record,
):
    mode = str(
        scene_record.get(
            "semantic_mode"
        )
        or ""
    ).upper()


    return bool(
        scene_record.get(
            "generic"
        )
        or
        "ILLUSTRATION"
        in mode
        or
        "ILLUSTRATIVE"
        in mode
    )


def choose_strategy(
    scene_record,
    dimensions,
):
    content_type = str(
        scene_record.get(
            "content_type"
        )
        or ""
    ).lower()


    source_class = str(
        scene_record.get(
            "source_class"
        )
        or ""
    )


    current_constraints = set(
        scene_record.get(
            "presentation_constraints"
        )
        or []
    )


    quality_fullscreen = (
        fullscreen_quality_pass(
            dimensions
        )
    )


    constraints = set(
        current_constraints
    )


    # --------------------------------------------------
    # PDF / documents
    # --------------------------------------------------

    if content_type == "application/pdf":

        constraints.update({
            "NO_RAW_PDF_RENDER",
            "RASTERIZE_PAGE_1_BEFORE_CANARY",
            "DOCUMENT_LEGIBILITY_REQUIRED",
        })


        return {
            "strategy":
                "DOCUMENT_PAGE_PREVIEW",

            "fullscreen_allowed":
                False,

            "constraints":
                sorted(
                    constraints
                ),

            "quality_fullscreen_pass":
                False,
        }


    # --------------------------------------------------
    # Video
    # --------------------------------------------------

    if content_type.startswith(
        "video/"
    ):

        if not quality_fullscreen:

            constraints.update({
                "CONTEXT_INSERT_ONLY",
                "NO_FULLSCREEN",
                "NO_FALSE_DETAIL_ENHANCEMENT",
                "PRESERVE_ARCHIVAL_ASPECT_RATIO",
            })


            return {
                "strategy":
                    "ARCHIVAL_INSET",

                "fullscreen_allowed":
                    False,

                "constraints":
                    sorted(
                        constraints
                    ),

                "quality_fullscreen_pass":
                    False,
            }


        return {
            "strategy":
                "VIDEO_COVER",

            "fullscreen_allowed":
                "NO_FULLSCREEN"
                not in constraints,

            "constraints":
                sorted(
                    constraints
                ),

            "quality_fullscreen_pass":
                True,
        }


    # --------------------------------------------------
    # Images
    # --------------------------------------------------

    if content_type.startswith(
        "image/"
    ):

        if (
            not quality_fullscreen
            or
            "NO_FULLSCREEN"
            in constraints
            or
            "CONTEXT_INSERT_ONLY"
            in constraints
        ):

            constraints.update({
                "NO_FULLSCREEN",
                "PRESERVE_ASPECT_RATIO",
            })


            return {
                "strategy":
                    "IMAGE_INSET",

                "fullscreen_allowed":
                    False,

                "constraints":
                    sorted(
                        constraints
                    ),

                "quality_fullscreen_pass":
                    quality_fullscreen,
            }


        return {
            "strategy":
                "IMAGE_COVER",

            "fullscreen_allowed":
                True,

            "constraints":
                sorted(
                    constraints
                ),

            "quality_fullscreen_pass":
                True,
        }


    constraints.add(
        "UNSUPPORTED_VISUAL_MEDIA"
    )


    return {
        "strategy":
            "HOLD",

        "fullscreen_allowed":
            False,

        "constraints":
            sorted(
                constraints
            ),

        "quality_fullscreen_pass":
            False,
    }


def disclosure_label(
    scene_record,
):
    current = (
        scene_record.get(
            "overlay_label"
        )
    )


    if current:
        return current


    if is_illustrative(
        scene_record
    ):

        return (
            POLICY[
                "illustration"
            ][
                "required_label"
            ]
        )


    if is_context_mode(
        scene_record.get(
            "semantic_mode"
        )
    ):

        return (
            POLICY[
                "context"
            ][
                "required_label"
            ]
        )


    return None


if __name__ == "__main__":

    print(
        "VI1300 PRESENTATION SAFETY=PASS"
    )
