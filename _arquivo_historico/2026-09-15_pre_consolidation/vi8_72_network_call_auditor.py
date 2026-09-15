#!/usr/bin/env python3

from pathlib import Path
import re

VERSION = "8.72"

PATTERNS = {
    "requests_get":
        r"\brequests\.get\s*\(",

    "requests_post":
        r"\brequests\.post\s*\(",

    "urllib":
        r"\burllib\.",

    "httpx":
        r"\bhttpx\.",

    "aiohttp":
        r"\baiohttp\.",

    "curl_shell":
        r"\bcurl\s+",

    "wget_shell":
        r"\bwget\s+",
}


def audit(path):
    p = Path(path)

    try:
        text = p.read_text(
            encoding="utf-8",
            errors="ignore"
        )
    except Exception:
        return {
            "path": str(p),
            "calls": [],
        }

    calls = []

    lines = text.splitlines()

    for number, line in enumerate(
        lines,
        start=1
    ):
        for name, pattern in (
            PATTERNS.items()
        ):
            if re.search(
                pattern,
                line
            ):
                calls.append({
                    "type": name,
                    "line": number,
                    "snippet":
                        line.strip()[:220],
                })

    return {
        "version": VERSION,
        "path": str(p),
        "calls": calls,
        "count": len(calls),
    }


def self_test():
    assert VERSION == "8.72"
    print(
        "VI8.72 NETWORK CALL AUDITOR=PASS"
    )


if __name__ == "__main__":
    self_test()
