#!/usr/bin/env python3

VERSION = "8.01"

def normalize(candidate=None):
    candidate = dict(candidate or {})

    return {
        "path":
            candidate.get("path"),

        "source":
            candidate.get("source", "UNKNOWN"),

        "media_type":
            str(
                candidate.get(
                    "media_type",
                    "STILL"
                )
            ).upper(),

        "width":
            candidate.get("width"),

        "height":
            candidate.get("height"),

        "query":
            candidate.get("query", ""),

        "category":
            candidate.get("category"),

        "shot":
            candidate.get("shot"),

        "source_score":
            float(
                candidate.get(
                    "source_score",
                    0
                )
                or 0
            ),

        "relevance_score":
            float(
                candidate.get(
                    "relevance_score",
                    0
                )
                or 0
            ),

        "metadata":
            candidate.get(
                "metadata"
            )
            or {},
    }

def self_test():
    result = normalize({
        "path": "image.jpg"
    })

    assert result["media_type"] == "STILL"
    assert result["path"] == "image.jpg"

    print(
        "VI8.01 MEDIA CANDIDATE MODEL=PASS"
    )

if __name__ == "__main__":
    self_test()
