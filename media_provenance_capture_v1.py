#!/usr/bin/env python3

import hashlib
import json
import os
import re
import time

from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent


def _first(
    value,
    keys,
):
    if not isinstance(
        value,
        dict
    ):
        return ""

    for key in keys:

        item = value.get(
            key
        )

        if item not in [
            None,
            "",
        ]:

            return item

    return ""


def _sha256(
    path,
):
    digest = hashlib.sha256()

    with Path(path).open(
        "rb"
    ) as handle:

        while True:

            chunk = handle.read(
                1024 * 1024
            )

            if not chunk:
                break

            digest.update(
                chunk
            )

    return digest.hexdigest()


def _safe_name(
    value,
):
    value = re.sub(
        r"[^a-zA-Z0-9_.-]+",
        "_",
        str(
            value
            or ""
        ),
    )

    return value[
        :80
    ].strip(
        "._"
    ) or "asset"


def _source_url(
    candidate,
):
    return str(
        _first(
            candidate,
            [
                "source_url",
                "descriptionurl",
                "page_url",
                "pageURL",
                "source",
                "original_url",
                "remote_url",
                "media_url",
                "download_url",
                "final_url",
                "url",
            ],
        )
        or ""
    ).strip()


def _provider(
    candidate,
):
    explicit = str(
        _first(
            candidate,
            [
                "provider",
                "source_provider",
                "platform",
            ],
        )
        or ""
    ).strip()

    if explicit:
        return explicit

    # Provider is only derived from the source URL's host.
    # It is not used as independent evidence.
    url = _source_url(
        candidate
    )

    try:

        host = (
            urlsplit(
                url
            ).hostname
            or ""
        ).lower()

    except Exception:

        host = ""

    known = {
        "pexels.com":
            "Pexels",

        "www.pexels.com":
            "Pexels",

        "pixabay.com":
            "Pixabay",

        "www.pixabay.com":
            "Pixabay",

        "coverr.co":
            "Coverr",

        "www.coverr.co":
            "Coverr",

        "commons.wikimedia.org":
            "Wikimedia Commons",

        "wikipedia.org":
            "Wikipedia",

        "en.wikipedia.org":
            "Wikipedia",

        "pt.wikipedia.org":
            "Wikipedia",
    }

    return known.get(
        host,
        "",
    )


def normalize_candidate(
    candidate,
):
    if not isinstance(
        candidate,
        dict
    ):

        candidate = {}


    return {
        "provider":
            _provider(
                candidate
            ),

        "title":
            str(
                _first(
                    candidate,
                    [
                        "title",
                        "name",
                        "filename",
                        "alt",
                    ],
                )
                or ""
            ).strip(),

        "license":
            str(
                _first(
                    candidate,
                    [
                        "license",
                        "license_name",
                        "license_short_name",
                    ],
                )
                or ""
            ).strip(),

        "artist":
            str(
                _first(
                    candidate,
                    [
                        "artist",
                        "author",
                        "photographer",
                        "creator",
                        "user",
                    ],
                )
                or ""
            ).strip(),

        "source_group":
            str(
                _first(
                    candidate,
                    [
                        "source_group",
                    ],
                )
                or ""
            ).strip(),

        "source_url":
            _source_url(
                candidate
            ),
    }


def write_provenance(
    candidate,
    local_path,
    *,
    method,
):
    path = Path(
        local_path
    ).expanduser()

    if not path.exists():
        return None

    if not path.is_file():
        return None

    suffix = path.suffix.lower()

    if suffix not in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".avif",
        ".gif",
        ".mp4",
        ".webm",
        ".mov",
        ".mkv",
        ".pdf",
    }:

        return None


    identity = normalize_candidate(
        candidate
    )


    # We need at least one genuine source URL.
    # Query/search/topic are deliberately ignored.
    if not identity[
        "source_url"
    ]:

        return None


    digest = _sha256(
        path
    )


    record = {
        "schema":
            "SHORTAUTOPRO_SOURCE_PROVENANCE_V1",

        "provider":
            identity[
                "provider"
            ],

        "title":
            identity[
                "title"
            ],

        "license":
            identity[
                "license"
            ],

        "artist":
            identity[
                "artist"
            ],

        "source_group":
            identity[
                "source_group"
            ],

        "source_url":
            identity[
                "source_url"
            ],

        "remote_url":
            identity[
                "source_url"
            ],

        "local_path":
            str(
                path.resolve()
            ),

        "sha256":
            digest,

        "bytes":
            path.stat().st_size,

        "suffix":
            suffix,

        "capture_method":
            str(
                method
            ),

        "captured_at_unix":
            time.time(),

        "query_used_as_evidence":
            False,

        "search_used_as_evidence":
            False,

        "topic_used_as_evidence":
            False,
    }


    output_dir = Path(
        os.environ.get(
            "SAP_PROVENANCE_DIR",
            str(
                ROOT
                / "manifests"
                / "source_provenance_live"
            ),
        )
    )


    output_dir.mkdir(
        parents=True,
        exist_ok=True,
    )


    filename = (
        "source_"
        +
        digest[
            :16
        ]
        +
        "_"
        +
        _safe_name(
            path.stem
        )
        +
        ".json"
    )


    output = (
        output_dir
        / filename
    )


    temporary = output.with_suffix(
        ".json.part"
    )


    temporary.write_text(
        json.dumps(
            record,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


    temporary.replace(
        output
    )


    return output


def _find_candidate(
    args,
    kwargs,
):
    preferred = [
        "candidato",
        "candidate",
        "item",
        "asset",
        "media",
    ]


    for key in preferred:

        value = kwargs.get(
            key
        )

        if (
            isinstance(
                value,
                dict
            )
            and
            _source_url(
                value
            )
        ):

            return value


    for value in args:

        if (
            isinstance(
                value,
                dict
            )
            and
            _source_url(
                value
            )
        ):

            return value


    return {}


def _find_url(
    args,
    kwargs,
):
    value = kwargs.get(
        "url"
    )

    if isinstance(
        value,
        str
    ) and value.startswith(
        (
            "http://",
            "https://",
        )
    ):

        return value


    for value in args:

        if (
            isinstance(
                value,
                str
            )
            and
            value.startswith(
                (
                    "http://",
                    "https://",
                )
            )
        ):

            return value


    return ""


def _find_existing_destination(
    args,
    kwargs,
):
    for key in [
        "destino",
        "destination",
        "dest",
        "saida",
        "output",
        "path",
        "arquivo",
    ]:

        value = kwargs.get(
            key
        )

        if value:

            try:

                candidate = Path(
                    value
                )

                if candidate.is_file():
                    return candidate

            except Exception:

                pass


    for value in reversed(
        args
    ):

        if not isinstance(
            value,
            (
                str,
                Path,
            )
        ):
            continue

        if (
            isinstance(
                value,
                str
            )
            and
            value.startswith(
                (
                    "http://",
                    "https://",
                )
            )
        ):
            continue

        try:

            candidate = Path(
                value
            )

            if candidate.is_file():
                return candidate

        except Exception:

            pass


    return None


def _install_shadowed_preserved_1(
    namespace,
):
    """
    Install provenance capture around the active media
    download boundaries.

    No network call is added.
    No media-selection policy is changed.
    """

    if namespace.get(
        "_SAP_PROVENANCE_CAPTURE_V1_INSTALLED"
    ):

        return False


    wrapped = []


    original_candidate = namespace.get(
        "baixar_candidato_5_2"
    )


    if callable(
        original_candidate
    ):

        namespace[
            "_sap_prov_original_baixar_candidato_5_2"
        ] = original_candidate


        def baixar_candidato_5_2(
            *args,
            **kwargs,
        ):
            result = namespace[
                "_sap_prov_original_baixar_candidato_5_2"
            ](
                *args,
                **kwargs,
            )


            ok = False
            destination = None


            if (
                isinstance(
                    result,
                    tuple
                )
                and
                len(
                    result
                )
                >=
                2
            ):

                ok = bool(
                    result[
                        0
                    ]
                )

                destination = result[
                    1
                ]


            if (
                ok
                and
                destination
            ):

                candidate = _find_candidate(
                    args,
                    kwargs,
                )


                try:

                    write_provenance(
                        candidate,
                        destination,
                        method=(
                            "baixar_candidato_5_2"
                        ),
                    )

                except Exception:

                    # Provenance capture must never break
                    # the existing media pipeline.
                    pass


            return result


        namespace[
            "baixar_candidato_5_2"
        ] = baixar_candidato_5_2

        wrapped.append(
            "baixar_candidato_5_2"
        )


    original_download = namespace.get(
        "baixar"
    )


    if callable(
        original_download
    ):

        namespace[
            "_sap_prov_original_baixar"
        ] = original_download


        def baixar(
            *args,
            **kwargs,
        ):
            result = namespace[
                "_sap_prov_original_baixar"
            ](
                *args,
                **kwargs,
            )


            if bool(
                result
            ):

                destination = (
                    _find_existing_destination(
                        args,
                        kwargs,
                    )
                )


                url = _find_url(
                    args,
                    kwargs,
                )


                if (
                    destination is not None
                    and
                    url
                ):

                    try:

                        write_provenance(
                            {
                                "url":
                                    url
                            },
                            destination,
                            method="baixar",
                        )

                    except Exception:

                        pass


            return result


        namespace[
            "baixar"
        ] = baixar

        wrapped.append(
            "baixar"
        )


    namespace[
        "_SAP_PROVENANCE_CAPTURE_V1_INSTALLED"
    ] = {
        "wrapped":
            wrapped,

        "query_used_as_evidence":
            False,

        "topic_used_as_evidence":
            False,
    }


    return bool(
        wrapped
    )


if __name__ == "__main__":
    print(
        "SHORTAUTOPRO SOURCE PROVENANCE CAPTURE V1"
    )


# ============================================================
# SHORTAUTOPRO MEDIA HARDENING V1
#
# Forward-only guard installed at the real media-download
# boundary.
#
# Protections:
# - minimum payload size
# - file-signature validation
# - SHA256 session deduplication
# - same-path reuse remains valid
# - provenance remains bound to accepted media
# - query/search/topic never become evidence
# ============================================================

_SAP_MEDIA_HARDENING_V1 = True

_SAP_SESSION_HASH_PATHS = {}


def _sap_media_limits(
    path,
):
    path = Path(
        path
    )

    suffix = path.suffix.lower()

    image_min = int(
        os.environ.get(
            "SAP_MIN_IMAGE_BYTES",
            "2048",
        )
    )

    video_min = int(
        os.environ.get(
            "SAP_MIN_VIDEO_BYTES",
            "8192",
        )
    )

    generic_min = int(
        os.environ.get(
            "SAP_MIN_MEDIA_BYTES",
            "1024",
        )
    )

    if suffix in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".gif",
        ".avif",
    }:
        return image_min

    if suffix in {
        ".mp4",
        ".mov",
        ".mkv",
        ".webm",
    }:
        return video_min

    return generic_min


def _sap_signature_valid(
    path,
):
    path = Path(
        path
    )

    suffix = path.suffix.lower()

    try:

        with path.open(
            "rb"
        ) as handle:

            head = handle.read(
                64
            )

    except Exception:

        return False


    if suffix in {
        ".jpg",
        ".jpeg",
    }:

        return head.startswith(
            b"\xff\xd8\xff"
        )


    if suffix == ".png":

        return head.startswith(
            b"\x89PNG\r\n\x1a\n"
        )


    if suffix == ".webp":

        return (
            len(head) >= 12
            and
            head[:4] == b"RIFF"
            and
            head[8:12] == b"WEBP"
        )


    if suffix == ".gif":

        return head.startswith(
            (
                b"GIF87a",
                b"GIF89a",
            )
        )


    if suffix in {
        ".mp4",
        ".mov",
    }:

        return (
            b"ftyp"
            in head[:32]
        )


    if suffix in {
        ".webm",
        ".mkv",
    }:

        return head.startswith(
            b"\x1a\x45\xdf\xa3"
        )


    # Unknown formats are not rejected by signature alone.
    return True


def _sap_validate_downloaded_media(
    path,
):
    try:

        path = Path(
            path
        ).expanduser()

    except Exception:

        return {
            "ok":
                False,

            "reason":
                "INVALID_PATH",
        }


    if not path.is_file():

        return {
            "ok":
                False,

            "reason":
                "FILE_MISSING",
        }


    try:

        size = path.stat().st_size

    except Exception:

        return {
            "ok":
                False,

            "reason":
                "STAT_FAILED",
        }


    minimum = _sap_media_limits(
        path
    )


    if size < minimum:

        return {
            "ok":
                False,

            "reason":
                "FILE_TOO_SMALL",

            "bytes":
                size,

            "minimum":
                minimum,
        }


    if not _sap_signature_valid(
        path
    ):

        return {
            "ok":
                False,

            "reason":
                "INVALID_FILE_SIGNATURE",

            "bytes":
                size,
        }


    try:

        digest = _sha256(
            path
        )

    except Exception:

        return {
            "ok":
                False,

            "reason":
                "HASH_FAILED",
        }


    canonical = str(
        path.resolve()
    )


    previous = _SAP_SESSION_HASH_PATHS.get(
        digest
    )


    duplicate = bool(
        previous
        and
        previous
        !=
        canonical
    )


    if not previous:

        _SAP_SESSION_HASH_PATHS[
            digest
        ] = canonical


    return {
        "ok":
            True,

        "reason":
            (
                "DUPLICATE_SHA256"
                if duplicate
                else "VALID"
            ),

        "bytes":
            size,

        "minimum":
            minimum,

        "sha256":
            digest,

        "path":
            canonical,

        "duplicate":
            duplicate,

        "canonical_path":
            previous
            or
            canonical,
    }


def _sap_safe_remove_duplicate(
    path,
    canonical_path,
):
    try:

        path = Path(
            path
        ).resolve()

        canonical = Path(
            canonical_path
        ).resolve()

        if (
            path != canonical
            and
            path.exists()
        ):

            path.unlink()

            return True

    except Exception:

        pass

    return False


def _install_shadowed_preserved_2(
    namespace,
):
    """
    Hardened ShortAutoPro media/provenance boundary.

    This replaces the earlier install() implementation while
    preserving its public contract.

    No additional network operation is performed.
    """

    state = namespace.get(
        "_SAP_PROVENANCE_CAPTURE_V1_INSTALLED"
    )


    if isinstance(
        state,
        dict
    ) and state.get(
        "media_hardening_v1"
    ):

        return False


    wrapped = []


    original_candidate = namespace.get(
        "baixar_candidato_5_2"
    )


    if callable(
        original_candidate
    ):

        namespace[
            "_sap_prov_original_baixar_candidato_5_2"
        ] = original_candidate


        def baixar_candidato_5_2(
            *args,
            **kwargs,
        ):
            result = namespace[
                "_sap_prov_original_baixar_candidato_5_2"
            ](
                *args,
                **kwargs,
            )


            if not (
                isinstance(
                    result,
                    tuple
                )
                and
                len(
                    result
                )
                >=
                2
            ):

                return result


            ok = bool(
                result[
                    0
                ]
            )

            destination = result[
                1
            ]


            if (
                not ok
                or
                not destination
            ):

                return result


            validation = (
                _sap_validate_downloaded_media(
                    destination
                )
            )


            namespace[
                "_SAP_LAST_MEDIA_VALIDATION"
            ] = validation


            if not validation.get(
                "ok"
            ):

                return (
                    False,
                    destination,
                )


            if validation.get(
                "duplicate"
            ):

                _sap_safe_remove_duplicate(
                    destination,
                    validation.get(
                        "canonical_path"
                    ),
                )

                namespace[
                    "_SAP_LAST_DUPLICATE_MEDIA"
                ] = validation

                return (
                    False,
                    destination,
                )


            candidate = _find_candidate(
                args,
                kwargs,
            )


            try:

                write_provenance(
                    candidate,
                    destination,
                    method=(
                        "baixar_candidato_5_2"
                        "_hardened_v1"
                    ),
                )

            except Exception as exc:

                namespace[
                    "_SAP_LAST_PROVENANCE_ERROR"
                ] = (
                    type(exc).__name__
                    +
                    ": "
                    +
                    str(exc)[:300]
                )


            return result


        namespace[
            "baixar_candidato_5_2"
        ] = baixar_candidato_5_2

        wrapped.append(
            "baixar_candidato_5_2"
        )


    namespace[
        "_SAP_PROVENANCE_CAPTURE_V1_INSTALLED"
    ] = {
        "wrapped":
            wrapped,

        "media_hardening_v1":
            True,

        "size_validation":
            True,

        "signature_validation":
            True,

        "sha256_dedup":
            True,

        "same_path_reuse_allowed":
            True,

        "query_used_as_evidence":
            False,

        "search_used_as_evidence":
            False,

        "topic_used_as_evidence":
            False,
    }


    return bool(
        wrapped
    )


# ============================================================
# SHORTAUTOPRO CANONICAL SCENE MEDIA GUARD V1
#
# Ensures exactly one accepted physical media file per scene.
#
# Example:
# scene_03.jpg accepted
# later scene_03.mp4 becomes the accepted winner
# -> scene_03.jpg is removed
#
# This acts only AFTER the already hardened downloader returns
# success, so failed/invalid/duplicate candidates cannot erase
# the previous valid scene media.
# ============================================================

_SAP_CANONICAL_MEDIA_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".avif",
    ".gif",
    ".mp4",
    ".webm",
    ".mov",
    ".mkv",
}


def _sap_cleanup_scene_siblings(
    selected_path,
):
    try:
        selected = Path(
            selected_path
        ).expanduser().resolve()

    except Exception:
        return {
            "ok": False,
            "reason": "INVALID_SELECTED_PATH",
            "removed": [],
        }

    if not selected.is_file():
        return {
            "ok": False,
            "reason": "SELECTED_FILE_MISSING",
            "removed": [],
        }

    stem = selected.stem

    # Protect unrelated filenames.
    if not stem.startswith(
        "scene_"
    ):
        return {
            "ok": True,
            "reason": "NON_SCENE_FILENAME",
            "removed": [],
        }

    parent = selected.parent

    removed = []

    for sibling in parent.glob(
        stem + ".*"
    ):

        try:
            sibling = sibling.resolve()
        except Exception:
            continue

        if sibling == selected:
            continue

        if (
            sibling.suffix.lower()
            not in
            _SAP_CANONICAL_MEDIA_EXTENSIONS
        ):
            continue

        if not sibling.is_file():
            continue

        try:
            sibling.unlink()

            removed.append(
                str(
                    sibling
                )
            )

        except Exception:
            pass

    return {
        "ok": True,
        "reason": "CANONICALIZED",
        "selected": str(selected),
        "removed": removed,
    }


# Preserve current hardened installer.
_sap_install_before_canonical_v1 = _install_shadowed_preserved_2


def install(
    namespace,
):
    """
    Install existing provenance/hardening first, then add
    canonical one-file-per-scene enforcement.
    """

    state = namespace.get(
        "_SAP_CANONICAL_SCENE_MEDIA_V1_INSTALLED"
    )

    if isinstance(
        state,
        dict
    ):
        return False


    # First install all existing hardening/provenance logic.
    previous_result = (
        _sap_install_before_canonical_v1(
            namespace
        )
    )


    current_downloader = namespace.get(
        "baixar_candidato_5_2"
    )


    if not callable(
        current_downloader
    ):
        namespace[
            "_SAP_CANONICAL_SCENE_MEDIA_V1_INSTALLED"
        ] = {
            "wrapped": False,
            "reason": "DOWNLOADER_NOT_FOUND",
        }

        return bool(
            previous_result
        )


    namespace[
        "_sap_canonical_original_baixar_candidato_5_2"
    ] = current_downloader


    def baixar_candidato_5_2(
        *args,
        **kwargs,
    ):
        result = namespace[
            "_sap_canonical_original_baixar_candidato_5_2"
        ](
            *args,
            **kwargs,
        )


        success = bool(
            isinstance(
                result,
                tuple,
            )
            and
            len(
                result
            )
            >=
            2
            and
            result[
                0
            ]
        )


        if not success:
            return result


        selected_path = result[
            1
        ]


        cleanup = (
            _sap_cleanup_scene_siblings(
                selected_path
            )
        )


        namespace[
            "_SAP_LAST_CANONICAL_SCENE_MEDIA"
        ] = cleanup


        return result


    namespace[
        "baixar_candidato_5_2"
    ] = baixar_candidato_5_2


    namespace[
        "_SAP_CANONICAL_SCENE_MEDIA_V1_INSTALLED"
    ] = {
        "wrapped": True,
        "exactly_one_media_per_scene": True,
        "cleanup_only_after_success": True,
        "preserves_failed_previous_media": True,
    }


    return True
