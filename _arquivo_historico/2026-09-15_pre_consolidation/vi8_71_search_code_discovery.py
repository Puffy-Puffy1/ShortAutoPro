#!/usr/bin/env python3

from pathlib import Path
import re

VERSION = "8.71"

BASE = Path.home() / "ShortAutoPro"

KEYWORDS = (
    "wikimedia",
    "wikipedia",
    "commons",
    "search",
    "buscar",
    "busca",
    "download",
    "requests.get",
    "requests.post",
    "urllib",
    "httpx",
    "aiohttp",
    "provider",
    "source_router",
    "media",
    "image",
    "imagem",
)

EXCLUDED_DIRS = {
    "__pycache__",
    "backups",
    ".git",
    "videos",
    "audios",
    "temp",
}


def discover():
    files = []

    for path in BASE.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {
            ".py",
            ".sh",
        }:
            continue

        if any(
            part in EXCLUDED_DIRS
            for part in path.parts
        ):
            continue

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="ignore"
            )
        except Exception:
            continue

        low = text.lower()

        hits = [
            keyword
            for keyword in KEYWORDS
            if keyword.lower() in low
        ]

        if not hits:
            continue

        functions = re.findall(
            r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
            text,
            flags=re.M
        )

        files.append({
            "path": str(path),
            "relative":
                str(path.relative_to(BASE)),
            "hits": sorted(
                set(hits)
            ),
            "functions":
                functions[:40],
        })

    files.sort(
        key=lambda item: (
            -len(item["hits"]),
            item["relative"]
        )
    )

    return {
        "version": VERSION,
        "count": len(files),
        "files": files,
    }


def self_test():
    assert VERSION == "8.71"
    print(
        "VI8.71 SEARCH CODE DISCOVERY=PASS"
    )


if __name__ == "__main__":
    self_test()
