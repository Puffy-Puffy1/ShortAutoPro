#!/usr/bin/env python3

import json
import time

from urllib.parse import (
    urlencode,
    urlparse,
)

from urllib.request import (
    Request,
    urlopen,
)

from urllib.error import (
    HTTPError,
    URLError,
)

from pathlib import Path


BASE = (
    Path.home()
    / "ShortAutoPro"
)

POLICY_PATH = (
    BASE
    / "config"
    / "vi1200_real_policy.json"
)


def load_policy():
    return json.loads(
        POLICY_PATH.read_text(
            encoding="utf-8"
        )
    )


POLICY = load_policy()


STATS = {
    "requests_attempted":
        0,

    "requests_succeeded":
        0,

    "requests_failed":
        0,

    "metadata_bytes_received":
        0,

    "remote_media_bytes_received":
        0,

    "hosts":
        {},

    "errors":
        [],
}


USER_AGENT = (
    "ShortAutoPro-VI1200/1.0 "
    "(metadata-only controlled pipeline)"
)


def allowed_url(
    url
):
    parsed = urlparse(
        url
    )

    allowed_hosts = set(
        POLICY[
            "network"
        ][
            "allowed_hosts"
        ]
    )

    return (
        parsed.scheme == "https"
        and
        parsed.hostname
        in allowed_hosts
    )


def record_host(
    url
):
    host = (
        urlparse(
            url
        ).hostname
        or "UNKNOWN"
    )

    STATS[
        "hosts"
    ][
        host
    ] = (
        STATS[
            "hosts"
        ].get(
            host,
            0
        )
        + 1
    )


def get_json(
    base_url,
    params=None,
    timeout=None,
):
    if not allowed_url(
        base_url
    ):
        return {
            "ok":
                False,

            "error":
                "host_not_allowed",

            "url":
                base_url,
        }


    if params:
        query = urlencode(
            params,
            doseq=True
        )

        url = (
            base_url
            + "?"
            + query
        )

    else:
        url = base_url


    maximum = int(
        POLICY[
            "network"
        ][
            "maximum_total_requests"
        ]
    )


    if (
        STATS[
            "requests_attempted"
        ]
        >= maximum
    ):
        return {
            "ok":
                False,

            "error":
                "request_budget_exhausted",

            "url":
                base_url,
        }


    retries = int(
        POLICY[
            "network"
        ][
            "retries"
        ]
    )


    timeout = (
        timeout
        or
        int(
            POLICY[
                "network"
            ][
                "timeout_seconds"
            ]
        )
    )


    last_error = None


    for attempt in range(
        retries + 1
    ):
        # VI1250.1 HARD REQUEST BUDGET
        if (
            STATS[
                "requests_attempted"
            ]
            >= maximum
        ):
            last_error = (
                "request_budget_exhausted"
            )
            break

        STATS[
            "requests_attempted"
        ] += 1

        record_host(
            base_url
        )


        request = Request(
            url,
            headers={
                "User-Agent":
                    USER_AGENT,

                "Accept":
                    "application/json",
            }
        )


        try:
            with urlopen(
                request,
                timeout=timeout
            ) as response:

                raw = response.read()

                STATS[
                    "metadata_bytes_received"
                ] += len(
                    raw
                )

                data = json.loads(
                    raw.decode(
                        "utf-8"
                    )
                )


                STATS[
                    "requests_succeeded"
                ] += 1


                return {
                    "ok":
                        True,

                    "status":
                        getattr(
                            response,
                            "status",
                            200
                        ),

                    "data":
                        data,

                    "bytes":
                        len(
                            raw
                        ),

                    "url":
                        base_url,

                    "attempt":
                        attempt + 1,
                }


        except (
            HTTPError,
            URLError,
            TimeoutError,
            json.JSONDecodeError,
        ) as exc:

            last_error = (
                type(exc).__name__
                + ":"
                + str(exc)[:180]
            )


            if attempt < retries:
                time.sleep(
                    0.6
                    * (
                        attempt + 1
                    )
                )


        except Exception as exc:
            last_error = (
                type(exc).__name__
                + ":"
                + str(exc)[:180]
            )

            break


    STATS[
        "requests_failed"
    ] += 1


    STATS[
        "errors"
    ].append(
        last_error
        or "unknown_network_error"
    )


    return {
        "ok":
            False,

        "error":
            last_error
            or "unknown_network_error",

        "url":
            base_url,
    }


def stats():
    return dict(
        STATS
    )


if __name__ == "__main__":
    print(
        "VI1200 TRANSPORT IMPORT=PASS"
    )

    print(
        "REMOTE MEDIA DOWNLOAD=False"
    )
