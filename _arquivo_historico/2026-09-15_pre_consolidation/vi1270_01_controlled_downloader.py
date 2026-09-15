#!/usr/bin/env python3

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from pathlib import Path


from vi1000_1_query_gate import (
    license_allowed,
)


BASE = (
    Path.home()
    / "ShortAutoPro"
)

POLICY = json.loads(
    (
        BASE
        / "config/"
        "vi1260_1_predownload_policy.json"
    ).read_text(
        encoding="utf-8"
    )
)

PLAN = (
    BASE
    / "temp/vi1260_1/"
    "selection_plan.json"
)

AUDIT = (
    BASE
    / "logs/producao/"
    "vi1260_1_00_predownload_audit_latest.json"
)

ROOT = (
    BASE
    / "temp/vi1270_downloads"
)

ASSETS = (
    ROOT
    / "assets"
)

MANIFEST = (
    ROOT
    / "download_manifest.json"
)

OUT = (
    BASE
    / "logs/producao/"
    "vi1270_01_controlled_downloader_latest.json"
)


MIN_REQUEST_INTERVAL = 3.5

BACKOFF_SECONDS = [
    12,
    24,
    45,
    60,
]


LAST_REQUEST = {}


def read_json(
    path,
    default=None,
):
    if not path.exists():

        return (
            {}
            if default is None
            else default
        )


    try:

        return json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except Exception:

        return (
            {}
            if default is None
            else default
        )


def write_json(
    path,
    data,
):
    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )


def sha256_file(
    path,
):
    sha = hashlib.sha256()


    with path.open(
        "rb"
    ) as handle:

        while True:

            chunk = handle.read(
                1024
                * 1024
            )


            if not chunk:
                break


            sha.update(
                chunk
            )


    return sha.hexdigest()


def allowed_host(
    hostname,
):
    hostname = str(
        hostname
        or ""
    ).lower()


    if hostname in {
        "upload.wikimedia.org",
        "commons.wikimedia.org",
        "archive.org",
    }:
        return True


    if hostname.endswith(
        ".archive.org"
    ):
        return True


    return False


def canonical_url(
    url,
):
    """
    Remove tracking parameters only.

    Required provider/download parameters remain intact.
    """

    parts = urllib.parse.urlsplit(
        url
    )


    query = urllib.parse.parse_qsl(
        parts.query,
        keep_blank_values=True
    )


    query = [
        (
            key,
            value,
        )

        for key, value
        in query

        if not key.lower().startswith(
            "utm_"
        )
    ]


    return urllib.parse.urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            parts.path,
            urllib.parse.urlencode(
                query,
                doseq=True
            ),
            parts.fragment,
        )
    )


def remote_url(
    candidate,
):
    keys = [
        "remote_url",
        "media_url",
        "original_url",
        "url",
    ]


    for key in keys:

        value = candidate.get(
            key
        )


        if (
            isinstance(
                value,
                str
            )
            and
            value.startswith(
                (
                    "https://",
                    "http://",
                )
            )
        ):

            return canonical_url(
                value
            )


    raw = (
        candidate.get(
            "raw_metadata"
        )
        or {}
    )


    for key in keys:

        value = raw.get(
            key
        )


        if (
            isinstance(
                value,
                str
            )
            and
            value.startswith(
                (
                    "https://",
                    "http://",
                )
            )
        ):

            return canonical_url(
                value
            )


    return None


# VI1270.2 WIKIMEDIA THUMBNAIL FALLBACK
def preferred_download_url(
    url,
    mime,
    *,
    width=1280,
):
    """
    Wikimedia explicitly recommends thumbnails when
    original-file requests are rate limited.

    For ordinary raster images we therefore use a
    1280px Commons thumbnail.

    Video/PDF files keep their original URL.
    """

    parts = urllib.parse.urlsplit(
        url
    )


    hostname = str(
        parts.hostname
        or ""
    ).lower()


    mime = str(
        mime
        or ""
    ).lower()


    if hostname != "upload.wikimedia.org":
        return url


    if mime not in {
        "image/jpeg",
        "image/png",
        "image/webp",
    }:
        return url


    path = parts.path


    prefix = (
        "/wikipedia/commons/"
    )


    if (
        not path.startswith(
            prefix
        )
        or
        "/thumb/"
        in path
    ):
        return url


    relative = path[
        len(prefix):
    ]


    pieces = relative.split(
        "/"
    )


    if len(pieces) < 3:
        return url


    filename = pieces[-1]


    lower = urllib.parse.unquote(
        filename
    ).lower()


    if not lower.endswith(
        (
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        )
    ):
        return url


    thumb_path = (
        "/wikipedia/commons/thumb/"
        + relative
        + "/"
        + str(
            int(width)
        )
        + "px-"
        + filename
    )


    return urllib.parse.urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            thumb_path,
            "",
            "",
        )
    )


def extension_for(
    url,
    mime,
):
    suffix = Path(
        urllib.parse.urlparse(
            url
        ).path
    ).suffix.lower()


    valid = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".webm",
        ".mp4",
        ".pdf",
    }


    if suffix in valid:

        return (
            ".jpg"
            if suffix == ".jpeg"
            else suffix
        )


    mapping = {
        "image/jpeg":
            ".jpg",

        "image/png":
            ".png",

        "image/webp":
            ".webp",

        "video/webm":
            ".webm",

        "video/mp4":
            ".mp4",

        "application/pdf":
            ".pdf",
    }


    return mapping.get(
        mime,
        ".bin"
    )


def normalized_content_type(
    response,
):
    value = str(
        response.headers.get(
            "Content-Type",
            ""
        )
    )


    return (
        value
        .split(
            ";",
            1
        )[0]
        .strip()
        .lower()
    )


def throttle(
    hostname,
):
    now = time.monotonic()


    previous = LAST_REQUEST.get(
        hostname
    )


    if previous is not None:

        elapsed = (
            now
            -
            previous
        )


        remaining = (
            MIN_REQUEST_INTERVAL
            -
            elapsed
        )


        if remaining > 0:

            time.sleep(
                remaining
            )


    LAST_REQUEST[
        hostname
    ] = time.monotonic()


def retry_after_seconds(
    error,
):
    try:

        raw = error.headers.get(
            "Retry-After"
        )


        if raw is None:
            return None


        value = int(
            str(
                raw
            ).strip()
        )


        return max(
            1,
            min(
                value,
                90
            )
        )


    except Exception:

        return None


def open_with_backoff(
    request,
    *,
    maximum_retries=4,
):
    url = request.full_url

    host = (
        urllib.parse.urlparse(
            url
        ).hostname
    )


    last_error = None


    for attempt in range(
        maximum_retries + 1
    ):

        throttle(
            host
        )


        try:

            return urllib.request.urlopen(
                request,
                timeout=35
            )


        except urllib.error.HTTPError as exc:

            last_error = exc


            retryable = (
                exc.code
                in {
                    429,
                    500,
                    502,
                    503,
                    504,
                }
            )


            if (
                not retryable
                or
                attempt >= maximum_retries
            ):

                raise


            header_delay = (
                retry_after_seconds(
                    exc
                )
            )


            fallback_delay = (
                BACKOFF_SECONDS[
                    min(
                        attempt,
                        len(
                            BACKOFF_SECONDS
                        )
                        - 1
                    )
                ]
            )


            delay = (
                header_delay
                if header_delay
                is not None
                else fallback_delay
            )


            try:
                exc.close()
            except Exception:
                pass


            print(
                "HTTP",
                exc.code,
                "| RETRY",
                attempt + 1,
                "/",
                maximum_retries,
                "| WAIT",
                delay,
                "s"
            )


            time.sleep(
                delay
            )


        except urllib.error.URLError as exc:

            last_error = exc


            if attempt >= maximum_retries:
                raise


            delay = (
                BACKOFF_SECONDS[
                    min(
                        attempt,
                        len(
                            BACKOFF_SECONDS
                        )
                        - 1
                    )
                ]
            )


            print(
                "NETWORK RETRY",
                attempt + 1,
                "/",
                maximum_retries,
                "| WAIT",
                delay,
                "s",
                "|",
                str(
                    exc
                )
            )


            time.sleep(
                delay
            )


    raise last_error


def download_one(
    url,
    destination,
    *,
    max_bytes,
):
    parsed = urllib.parse.urlparse(
        url
    )


    if parsed.scheme not in {
        "https",
        "http",
    }:

        raise RuntimeError(
            "invalid_scheme"
        )


    if not allowed_host(
        parsed.hostname
    ):

        raise RuntimeError(
            "unapproved_initial_host:"
            + str(
                parsed.hostname
            )
        )


    request = urllib.request.Request(
        url,
        headers={
            "User-Agent":
                (
                    "ShortAutoPro/1270.1 "
                    "(controlled personal media validation)"
                ),

            "Accept":
                "*/*",

            "Accept-Encoding":
                "identity",
        },
    )


    part = destination.with_suffix(
        destination.suffix
        + ".part"
    )


    part.unlink(
        missing_ok=True
    )


    sha = hashlib.sha256()

    total = 0


    response = open_with_backoff(
        request,
        maximum_retries=4,
    )


    with response:

        final_url = canonical_url(
            response.geturl()
        )


        final_host = (
            urllib.parse.urlparse(
                final_url
            ).hostname
        )


        if not allowed_host(
            final_host
        ):

            raise RuntimeError(
                "unapproved_redirect_host:"
                + str(
                    final_host
                )
            )


        content_type = (
            normalized_content_type(
                response
            )
        )


        allowed_mime = set(
            POLICY[
                "controlled_download"
            ][
                "allowed_mime_types"
            ]
        )


        if content_type not in allowed_mime:

            raise RuntimeError(
                "mime_not_allowed:"
                + content_type
            )


        content_length = (
            response.headers.get(
                "Content-Length"
            )
        )


        if content_length:

            try:

                declared = int(
                    content_length
                )


                if declared > max_bytes:

                    raise RuntimeError(
                        "declared_file_size_limit_exceeded"
                    )


            except ValueError:
                pass


        with part.open(
            "wb"
        ) as handle:

            while True:

                chunk = response.read(
                    256
                    * 1024
                )


                if not chunk:
                    break


                total += len(
                    chunk
                )


                if total > max_bytes:

                    raise RuntimeError(
                        "file_size_limit_exceeded"
                    )


                handle.write(
                    chunk
                )


                sha.update(
                    chunk
                )


    if total < 512:

        part.unlink(
            missing_ok=True
        )

        raise RuntimeError(
            "file_too_small"
        )


    part.replace(
        destination
    )


    return {
        "bytes":
            total,

        "sha256":
            sha.hexdigest(),

        "content_type":
            content_type,

        "final_url":
            final_url,

        "final_host":
            final_host,
    }


def validated_old_asset(
    asset,
):
    if not asset:
        return None


    try:

        path = Path(
            asset[
                "path"
            ]
        ).resolve()


        root = ASSETS.resolve()


        path.relative_to(
            root
        )


    except Exception:

        return None


    if (
        not path.exists()
        or
        not path.is_file()
    ):

        return None


    expected_size = int(
        asset.get(
            "bytes",
            -1
        )
    )


    if (
        expected_size <= 0
        or
        path.stat().st_size
        != expected_size
    ):

        return None


    expected_sha = str(
        asset.get(
            "sha256"
        )
        or ""
    )


    if (
        not expected_sha
        or
        sha256_file(
            path
        )
        != expected_sha
    ):

        return None


    content_type = str(
        asset.get(
            "content_type"
        )
        or ""
    ).lower()


    if content_type not in set(
        POLICY[
            "controlled_download"
        ][
            "allowed_mime_types"
        ]
    ):

        return None


    result = dict(
        asset
    )


    result[
        "path"
    ] = str(
        path
    )


    result[
        "resume_validated"
    ] = True


    return result


def main():
    audit = read_json(
        AUDIT
    ).get(
        "gate",
        {}
    )


    plan = read_json(
        PLAN
    )


    ready = (
        audit.get(
            "status"
        )
        ==
        "VI1260_1_PREDOWNLOAD_SEMANTICS_CERTIFIED"

        and

        audit.get(
            "ready_for_controlled_download"
        )
        is True

        and

        plan.get(
            "download_allowed"
        )
        is True
    )


    if not ready:

        report = {
            "version":
                "1270.1",

            "status":
                "VI1270_DOWNLOAD_BLOCKED_BY_PREDOWNLOAD_GATE",

            "download_executed":
                False,

            "reason":
                "predownload_gate_not_ready",

            "ffmpeg":
                False,

            "renderer":
                False,

            "video":
                False,

            "production_mutation":
                False,
        }


        write_json(
            OUT,
            {
                "gate":
                    report
            }
        )


        print(
            "VI1270.1: DOWNLOAD BLOCKED BY PREDOWNLOAD GATE"
        )

        return


    ASSETS.mkdir(
        parents=True,
        exist_ok=True
    )


    selected = (
        plan.get(
            "selected"
        )
        or {}
    )


    old_manifest = read_json(
        MANIFEST,
        {}
    )


    old_assets = (
        old_manifest.get(
            "source_assets"
        )
        or {}
    )


    max_file = int(
        POLICY[
            "controlled_download"
        ][
            "maximum_file_bytes"
        ]
    )


    max_total = int(
        POLICY[
            "controlled_download"
        ][
            "maximum_total_bytes"
        ]
    )


    source_assets = {}

    scene_map = {}

    failures = []

    total_bytes = 0

    resumed_assets = 0

    fresh_assets = 0


    print()
    print(
        "=============================================="
    )

    print(
        " VI1270.1 RESUMABLE CONTROLLED DOWNLOAD"
    )

    print(
        "=============================================="
    )


    for key in sorted(
        selected,
        key=lambda value:
            int(
                value
            )
    ):

        item = selected[
            key
        ]


        if (
            item.get(
                "decision"
            )
            != "SELECT_SAFE"
        ):

            failures.append({
                "scene":
                    int(
                        key
                    ),

                "reason":
                    "scene_not_selected",
            })

            continue


        candidate = (
            item.get(
                "candidate"
            )
            or {}
        )


        group = str(
            candidate.get(
                "source_group"
            )
            or
            (
                "SCENE:"
                + key
            )
        )


        # Already activated in this current run.
        if group in source_assets:

            scene_map[
                key
            ] = source_assets[
                group
            ]


            print(
                "SCENE",
                key,
                "| REUSE",
                "|",
                candidate.get(
                    "title"
                )
            )

            continue


        # Resume a previously validated successful
        # asset instead of downloading it again.
        old = validated_old_asset(
            old_assets.get(
                group
            )
        )


        if old is not None:

            if (
                total_bytes
                +
                old[
                    "bytes"
                ]
                >
                max_total
            ):

                failures.append({
                    "scene":
                        int(
                            key
                        ),

                    "reason":
                        "total_budget_exceeded_by_resumed_asset",
                })

                continue


            source_assets[
                group
            ] = old


            scene_map[
                key
            ] = old


            total_bytes += int(
                old[
                    "bytes"
                ]
            )


            resumed_assets += 1


            print(
                "SCENE",
                key,
                "| RESUME_OK",
                "|",
                old[
                    "bytes"
                ],
                "bytes",
                "|",
                candidate.get(
                    "title"
                )
            )

            continue


        if not license_allowed(
            candidate.get(
                "license"
            )
        ):

            failures.append({
                "scene":
                    int(
                        key
                    ),

                "reason":
                    "license_not_allowed",

                "title":
                    candidate.get(
                        "title"
                    ),
            })

            continue


        source_url = remote_url(
            candidate
        )


        if not source_url:

            failures.append({
                "scene":
                    int(
                        key
                    ),

                "reason":
                    "remote_url_missing",

                "title":
                    candidate.get(
                        "title"
                    ),
            })

            continue


        candidate_mime = str(
            candidate.get(
                "mime"
            )
            or
            (
                candidate.get(
                    "raw_metadata"
                )
                or {}
            ).get(
                "mime"
            )
            or ""
        ).lower()


        download_url = preferred_download_url(
            source_url,
            candidate_mime,
            width=1280,
        )


        group_hash = (
            hashlib.sha256(
                group.encode(
                    "utf-8"
                )
            )
            .hexdigest()[
                :20
            ]
        )


        ext = extension_for(
            download_url,
            candidate_mime
        )


        destination = (
            ASSETS
            /
            (
                group_hash
                + ext
            )
        )


        try:

            result = download_one(
                download_url,
                destination,
                max_bytes=max_file
            )


            if (
                total_bytes
                +
                result[
                    "bytes"
                ]
                >
                max_total
            ):

                destination.unlink(
                    missing_ok=True
                )

                raise RuntimeError(
                    "total_download_budget_exceeded"
                )


            total_bytes += (
                result[
                    "bytes"
                ]
            )


            asset = {
                "source_group":
                    group,

                "title":
                    candidate.get(
                        "title"
                    ),

                "provider":
                    candidate.get(
                        "provider"
                    ),

                "license":
                    candidate.get(
                        "license"
                    ),

                "original_url":
                    source_url,

                "download_url":
                    download_url,

                "final_url":
                    result[
                        "final_url"
                    ],

                "content_type":
                    result[
                        "content_type"
                    ],

                "bytes":
                    result[
                        "bytes"
                    ],

                "sha256":
                    result[
                        "sha256"
                    ],

                "path":
                    str(
                        destination
                    ),

                "resume_validated":
                    False,
            }


            source_assets[
                group
            ] = asset


            scene_map[
                key
            ] = asset


            fresh_assets += 1


            print(
                "SCENE",
                key,
                "| DOWNLOAD_OK",
                "|",
                result[
                    "bytes"
                ],
                "bytes",
                "|",
                str(
                    candidate.get(
                        "title"
                    )
                )[:75]
            )


        except Exception as exc:

            destination.unlink(
                missing_ok=True
            )


            failures.append({
                "scene":
                    int(
                        key
                    ),

                "reason":
                    (
                        type(
                            exc
                        ).__name__
                        + ":"
                        + str(
                            exc
                        )
                    ),

                "title":
                    candidate.get(
                        "title"
                    ),

                "source_url":
                    source_url,

                "download_url":
                    download_url,
            })


            print(
                "SCENE",
                key,
                "| DOWNLOAD_HOLD",
                "|",
                type(
                    exc
                ).__name__,
                str(
                    exc
                )
            )


    mapped_scenes = len(
        scene_map
    )


    unique_assets = len(
        source_assets
    )


    certified = (
        not failures
        and
        mapped_scenes == 12
        and
        unique_assets >= 8
        and
        total_bytes <= max_total
    )


    status = (
        "VI1270_CONTROLLED_DOWNLOAD_CERTIFIED"

        if certified

        else
        "VI1270_CONTROLLED_DOWNLOAD_HOLD"
    )


    manifest = {
        "version":
            "1270.1",

        "status":
            status,

        "mapped_scenes":
            mapped_scenes,

        "unique_assets":
            unique_assets,

        "resumed_assets":
            resumed_assets,

        "fresh_assets":
            fresh_assets,

        "total_bytes":
            total_bytes,

        "scene_map":
            scene_map,

        "source_assets":
            source_assets,

        "failures":
            failures,

        "ffmpeg_allowed":
            False,

        "render_allowed":
            False,

        "production_mutation_allowed":
            False,
    }


    write_json(
        MANIFEST,
        manifest
    )


    report = {
        "version":
            "1270.1",

        "status":
            status,

        "download_executed":
            True,

        "mapped_scenes":
            mapped_scenes,

        "unique_assets":
            unique_assets,

        "resumed_assets":
            resumed_assets,

        "fresh_assets":
            fresh_assets,

        "total_bytes":
            total_bytes,

        "failures":
            failures,

        "ffmpeg":
            False,

        "renderer":
            False,

        "video":
            False,

        "production_mutation":
            False,
    }


    write_json(
        OUT,
        {
            "gate":
                report
        }
    )


    print()
    print(
        "===== DOWNLOAD SUMMARY ====="
    )

    print(
        "MAPPED SCENES:",
        mapped_scenes
    )

    print(
        "UNIQUE ASSETS:",
        unique_assets
    )

    print(
        "RESUMED ASSETS:",
        resumed_assets
    )

    print(
        "FRESH ASSETS:",
        fresh_assets
    )

    print(
        "TOTAL BYTES:",
        total_bytes
    )

    print(
        "FAILURES:",
        failures
    )

    print(
        "STATUS:",
        status
    )


    print()
    print(
        "FFMPEG EXECUTED: False"
    )

    print(
        "VIDEO GENERATED: False"
    )

    print(
        "RENDERER ACTIVATED: False"
    )

    print(
        "PRODUCTION MUTATED: False"
    )


    if not certified:

        raise SystemExit(
            1
        )


if __name__ == "__main__":
    main()
