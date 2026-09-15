#!/usr/bin/env python3

from urllib.parse import urlparse

VERSION = "8.94"


def evaluate(results):

    safe = []
    rejected = []


    for item in (
        results or []
    ):

        url = str(
            item.get("url")
            or ""
        ).strip()

        try:
            parsed = urlparse(
                url
            )
        except Exception:
            parsed = None


        if (
            not parsed
            or parsed.scheme not in {
                "http",
                "https",
            }
            or not parsed.netloc
        ):
            rejected.append({
                "item":
                    item,
                "reason":
                    "invalid_url",
            })

            continue


        safe.append(
            item
        )


    return {
        "version":
            VERSION,

        "safe":
            safe,

        "safe_count":
            len(safe),

        "rejected":
            rejected,

        "rejected_count":
            len(rejected),
    }


def self_test():

    result = evaluate([
        {
            "url":
                "https://example.com/a.jpg"
        },
        {
            "url":
                "/local/file.jpg"
        },
    ])

    assert result[
        "safe_count"
    ] == 1

    print(
        "VI8.94 RESULT SAFETY AUDIT=PASS"
    )


if __name__ == "__main__":
    self_test()
