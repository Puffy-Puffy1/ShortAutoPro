#!/usr/bin/env python3

VERSION = "8.85"

NETWORK_IMPORTS = {
    "requests",
    "urllib",
    "httpx",
    "aiohttp",
}

PROCESS_IMPORTS = {
    "subprocess",
    "os",
}


def evaluate(imports):
    imports = (
        imports
        or []
    )

    network = []

    process = []

    for item in imports:
        root = (
            str(item)
            .split(".")[0]
        )

        if root in NETWORK_IMPORTS:
            network.append(
                item
            )

        if root in PROCESS_IMPORTS:
            process.append(
                item
            )

    return {
        "version": VERSION,
        "network_imports":
            sorted(
                set(network)
            ),
        "process_imports":
            sorted(
                set(process)
            ),
        "network_capable":
            bool(network),
        "process_capable":
            bool(process),
    }


def self_test():
    result = evaluate([
        "requests",
        "json",
    ])

    assert (
        result[
            "network_capable"
        ]
        is True
    )

    print(
        "VI8.85 IMPORT RISK AUDIT=PASS"
    )


if __name__ == "__main__":
    self_test()
