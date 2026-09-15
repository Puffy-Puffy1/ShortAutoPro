#!/usr/bin/env python3

VERSION = "8.93"


def sanitize(value):

    results = []

    if value is None:
        raw = []

    elif isinstance(
        value,
        list
    ):
        raw = value

    elif isinstance(
        value,
        tuple
    ):
        raw = list(value)

    elif isinstance(
        value,
        dict
    ):
        for key in (
            "results",
            "items",
            "images",
            "data",
        ):
            if isinstance(
                value.get(key),
                list
            ):
                raw = value[key]
                break
        else:
            raw = [value]

    else:
        raw = []


    for item in raw[:10]:

        if isinstance(
            item,
            str
        ):
            results.append({
                "url":
                    item,
                "title":
                    None,
                "source":
                    None,
            })

        elif isinstance(
            item,
            dict
        ):
            url = (
                item.get("url")
                or item.get(
                    "image_url"
                )
                or item.get(
                    "src"
                )
                or item.get(
                    "thumbnail"
                )
            )

            results.append({
                "url":
                    url,

                "title":
                    item.get(
                        "title"
                    )
                    or item.get(
                        "name"
                    ),

                "source":
                    item.get(
                        "source"
                    )
                    or item.get(
                        "provider"
                    ),

                "width":
                    item.get(
                        "width"
                    ),

                "height":
                    item.get(
                        "height"
                    ),
            })


    return {
        "version":
            VERSION,

        "count":
            len(results),

        "results":
            results,
    }


def self_test():

    result = sanitize([
        {
            "url":
                "https://example.com/a.jpg"
        }
    ])

    assert result["count"] == 1

    print(
        "VI8.93 RESULT SANITIZER=PASS"
    )


if __name__ == "__main__":
    self_test()
