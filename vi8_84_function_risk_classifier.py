#!/usr/bin/env python3

VERSION = "8.84"

DANGEROUS = (
    "download",
    "save",
    "write",
    "replace",
    "delete",
    "remove",
    "unlink",
    "recover",
    "recovery",
    "upload",
    "render",
    "ffmpeg",
)

SEARCH = (
    "search",
    "query",
    "find",
    "lookup",
    "buscar",
    "busca",
)


def evaluate(function):
    name = str(
        function.get(
            "name"
        )
        or ""
    ).lower()

    args = [
        str(x).lower()
        for x in (
            function.get(
                "args"
            )
            or []
        )
    ]

    risks = []

    if any(
        token in name
        for token in DANGEROUS
    ):
        risks.append(
            "dangerous_function_name"
        )

    dangerous_args = [
        arg
        for arg in args
        if any(
            token in arg
            for token in (
                "output",
                "dest",
                "destination",
                "save",
                "write",
                "download",
                "replace",
            )
        )
    ]

    if dangerous_args:
        risks.append(
            "write_like_parameters"
        )

    search_like = any(
        token in name
        for token in SEARCH
    )

    if risks:
        classification = "BLOCKED"

    elif search_like:
        classification = (
            "SEARCH_CANDIDATE"
        )

    else:
        classification = "OTHER"

    return {
        "version": VERSION,
        "name":
            function.get(
                "name"
            ),
        "args":
            function.get(
                "args"
            )
            or [],
        "classification":
            classification,
        "risks":
            risks,
    }


def self_test():
    assert evaluate({
        "name":
            "download_image",
        "args":
            ["url"]
    })["classification"] == "BLOCKED"

    assert evaluate({
        "name":
            "search_images",
        "args":
            ["query"]
    })["classification"] == (
        "SEARCH_CANDIDATE"
    )

    print(
        "VI8.84 FUNCTION RISK CLASSIFIER=PASS"
    )


if __name__ == "__main__":
    self_test()
