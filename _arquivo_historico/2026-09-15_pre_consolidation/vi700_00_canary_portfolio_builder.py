#!/usr/bin/env python3
from short_id_runtime_v1 import resolve_short_id as _sap_resolve_short_id

import ast
import hashlib
import json
import os
import re
import shutil
import struct
from pathlib import Path
from collections import Counter


VERSION = "700.00"

BASE = Path.home() / "ShortAutoPro"
LOG = BASE / "logs/producao"

VI330 = LOG / "vi330_00_controlled_real_ab_latest.json"
VI420 = LOG / "vi420_00_batch_deep_ab_latest.json"
VI500 = LOG / "vi500_00_global_provenance_identity_latest.json"
VI600 = LOG / "vi600_00_provenance_replacement_engine_latest.json"
VI650 = LOG / "vi650_00_shadow_portfolio_optimizer_latest.json"

OUT = (
    LOG /
    "vi700_00_canary_portfolio_builder_latest.json"
)

CANARY_DIR = (
    BASE /
    "temp/vi700_canary_media"
)

MANIFEST = (
    BASE /
    "temp/vi700_canary/"
    "portfolio_manifest.json"
)

RUNTIME_MODULE = (
    BASE /
    "vi700_runtime_override.py"
)

ENV_FILE = (
    BASE /
    "temp/vi700_canary/"
    "canary_env.sh"
)


IMAGE_EXT = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


VIDEO_EXT = {
    ".mp4",
    ".webm",
    ".mov",
    ".m4v",
    ".ogv",
    ".mpeg",
    ".mpg",
}


ACTIVE_OVERRIDE_SCENES = {
    3,
    8,
    9,
    10,
    11,
}


SCENE7_HARD_NEGATIVES = {
    "farm",
    "farming",
    "agriculture",
    "agricultural",
    "grain",
    "silo",
    "barn",
    "livestock",
    "schofield farm",
    "world trade center",
    "wtc",
    "twin towers",
    "vaporwave",
}


SCENE7_STRONG_VISUAL = {
    "elevator interior",
    "hotel elevator",
    "elevator doors",
    "inside elevator",
    "lift interior",
    "elevator car",
}


def load_gate(path, required=False):
    if not path.exists():
        if required:
            raise RuntimeError(
                f"missing:{path.name}"
            )

        return {}

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    return data.get(
        "gate",
        data
    )


def sha256(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            block = f.read(
                1024 * 1024
            )

            if not block:
                break

            h.update(block)

    return h.hexdigest()


def normalize(value):
    text = str(
        value or ""
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = (
        text
        .replace("_", " ")
        .replace("-", " ")
        .lower()
    )

    return re.sub(
        r"\s+",
        " ",
        text
    ).strip()


def by_scene(items):
    result = {}

    for item in items or []:
        try:
            result[
                int(item["scene"])
            ] = item

        except Exception:
            continue

    return result


def file_family(path):
    ext = path.suffix.lower()

    if ext in IMAGE_EXT:
        return "IMAGE"

    if ext in VIDEO_EXT:
        return "VIDEO"

    return "UNKNOWN"


def image_magic(path):
    with open(path, "rb") as f:
        head = f.read(12)

    return {
        "jpeg":
            head[:2]
            == b"\xff\xd8",

        "png":
            head[:8]
            == b"\x89PNG\r\n\x1a\n",
    }


def video_magic(path):
    with open(path, "rb") as f:
        head = f.read(16)

    return {
        "webm":
            head[:4]
            == b"\x1a\x45\xdf\xa3",

        "mp4":
            (
                len(head) >= 8
                and head[4:8]
                == b"ftyp"
            ),
    }


def jpeg_size(path):
    try:
        with open(path, "rb") as f:
            if (
                f.read(2)
                != b"\xff\xd8"
            ):
                return None

            while True:
                b = f.read(1)

                if not b:
                    return None

                if b != b"\xff":
                    continue

                while b == b"\xff":
                    b = f.read(1)

                marker = b[0]

                if marker in {
                    0xD8,
                    0xD9,
                }:
                    continue

                raw = f.read(2)

                if len(raw) != 2:
                    return None

                length = struct.unpack(
                    ">H",
                    raw
                )[0]

                if marker in {
                    0xC0, 0xC1, 0xC2,
                    0xC3, 0xC5, 0xC6,
                    0xC7, 0xC9, 0xCA,
                    0xCB, 0xCD, 0xCE,
                    0xCF,
                }:
                    data = f.read(5)

                    if len(data) != 5:
                        return None

                    height, width = (
                        struct.unpack(
                            ">HH",
                            data[1:5]
                        )
                    )

                    return width, height

                f.seek(
                    length - 2,
                    1
                )

    except Exception:
        return None


def png_size(path):
    try:
        with open(path, "rb") as f:
            data = f.read(24)

        if (
            len(data) >= 24
            and data[:8]
            == b"\x89PNG\r\n\x1a\n"
        ):
            return struct.unpack(
                ">II",
                data[16:24]
            )

    except Exception:
        pass

    return None


def image_size(path):
    size = jpeg_size(
        path
    )

    if size:
        return size

    return png_size(
        path
    )


def validate_asset(payload):
    path_value = payload.get(
        "sandbox_path"
    )

    if not path_value:
        return {
            "valid": False,
            "reason":
                "sandbox_path_missing",
        }

    path = Path(
        path_value
    )

    if not path.exists():
        return {
            "valid": False,
            "reason":
                "sandbox_file_missing",
        }

    expected = str(
        payload.get(
            "sha256"
        )
        or ""
    )

    actual = sha256(
        path
    )

    if (
        expected
        and expected != actual
    ):
        return {
            "valid": False,
            "reason":
                "sha256_mismatch",

            "expected":
                expected,

            "actual":
                actual,
        }

    family = file_family(
        path
    )

    if family == "IMAGE":
        magic = image_magic(
            path
        )

        if not (
            magic["jpeg"]
            or magic["png"]
        ):
            return {
                "valid": False,
                "reason":
                    "invalid_image_magic",
            }

        dimensions = image_size(
            path
        )

        if not dimensions:
            return {
                "valid": False,
                "reason":
                    "image_dimensions_missing",
            }

    elif family == "VIDEO":
        magic = video_magic(
            path
        )

        if not (
            magic["webm"]
            or magic["mp4"]
        ):
            return {
                "valid": False,
                "reason":
                    "invalid_video_magic",
            }

        dimensions = (
            payload.get("width"),
            payload.get("height"),
        )

    else:
        return {
            "valid": False,
            "reason":
                "unsupported_asset_family",
        }

    return {
        "valid":
            True,

        "path":
            str(path),

        "family":
            family,

        "sha256":
            actual,

        "bytes":
            path.stat().st_size,

        "dimensions":
            (
                list(dimensions)
                if dimensions
                else None
            ),
    }


def current_media_map(
    vi500
):
    return by_scene(
        vi500.get(
            "current_media"
        )
        or []
    )


def portfolio_map(
    vi650
):
    return by_scene(
        vi650.get(
            "portfolio"
        )
        or []
    )


def scene7_strict_audit(
    vi650
):
    selection = (
        vi650.get(
            "selections",
            {}
        ).get("7")
    )

    if selection is None:
        selection = (
            vi650.get(
                "selections",
                {}
            ).get(7)
        )

    if not selection:
        return {
            "candidate":
                None,

            "passed":
                False,

            "reason":
                "no_scene7_candidate",
        }

    candidate = (
        selection.get(
            "selected_metadata"
        )
        or {}
    )

    text = normalize(
        " ".join([
            str(
                candidate.get(
                    "title"
                )
                or ""
            ),
            str(
                candidate.get(
                    "evidence"
                )
                or ""
            ),
            " ".join(
                candidate.get(
                    "role_hits"
                )
                or []
            ),
        ])
    )

    negatives = sorted({
        term
        for term in (
            SCENE7_HARD_NEGATIVES
        )
        if term in text
    })

    strong = sorted({
        term
        for term in (
            SCENE7_STRONG_VISUAL
        )
        if term in text
    })

    # Generic "elevator" alone is no longer enough.
    passed = (
        bool(strong)
        and not negatives
    )

    return {
        "candidate":
            candidate.get(
                "title"
            ),

        "passed":
            passed,

        "strong_visual_hits":
            strong,

        "negative_hits":
            negatives,

        "reason":
            (
                "strict_hotel_elevator_context_pass"
                if passed
                else
                "generic_elevator_metadata_rejected"
            ),
    }


def source_asset_for_scene(
    scene,
    portfolio,
    vi600,
    vi420
):
    item = portfolio.get(
        scene,
        {}
    )

    asset = (
        item.get("asset")
        or {}
    )

    if asset.get(
        "sandbox_path"
    ):
        return asset

    if scene == 3:
        staged = (
            vi600.get(
                "staged_replacements",
                {}
            ).get("3")
        )

        if staged is None:
            staged = (
                vi600.get(
                    "staged_replacements",
                    {}
                ).get(3)
            )

        if staged:
            return staged

    if scene == 9:
        candidate = (
            vi420.get(
                "scene9",
                {}
            ).get(
                "candidate"
            )
            or {}
        )

        if candidate:
            return candidate

    return {}


def copy_canary_asset(
    scene,
    payload
):
    validated = validate_asset(
        payload
    )

    if not validated[
        "valid"
    ]:
        return {
            "copied":
                False,

            "validation":
                validated,
        }

    source = Path(
        validated["path"]
    )

    suffix = source.suffix.lower()

    destination = (
        CANARY_DIR /
        f"scene_{scene:02d}{suffix}"
    )

    CANARY_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    shutil.copy2(
        source,
        destination
    )

    copied_hash = sha256(
        destination
    )

    if (
        copied_hash
        != validated[
            "sha256"
        ]
    ):
        destination.unlink(
            missing_ok=True
        )

        return {
            "copied":
                False,

            "validation":
                {
                    "valid":
                        False,

                    "reason":
                        "copy_hash_mismatch",
                },
        }

    return {
        "copied":
            True,

        "source_path":
            str(source),

        "canary_path":
            str(destination),

        "sha256":
            copied_hash,

        "bytes":
            destination.stat().st_size,

        "family":
            validated[
                "family"
            ],

        "dimensions":
            validated[
                "dimensions"
            ],

        "title":
            payload.get(
                "title"
            ),

        "license":
            payload.get(
                "license"
            ),

        "license_score":
            payload.get(
                "license_score"
            ),
    }


def source_code_audit():
    targets = [
        BASE /
        "vi6_95_scene_executor.py",

        BASE /
        "video.py",

        BASE /
        "v6.py",

        BASE /
        "gerar_short.sh",
    ]

    keywords = {
        "VI700_CANARY_MODE",
        "VI730_CANARY_MODE",
        "scene",
        "media",
        "motion_plan",
        "scene_executor",
        "render",
    }

    report = {}

    for path in targets:
        entry = {
            "exists":
                path.exists(),

            "sha256":
                None,

            "functions":
                [],

            "keyword_hits":
                [],
        }

        if not path.exists():
            report[
                path.name
            ] = entry

            continue

        entry[
            "sha256"
        ] = sha256(
            path
        )

        text = path.read_text(
            encoding="utf-8",
            errors="ignore"
        )

        if (
            path.suffix
            == ".py"
        ):
            try:
                tree = ast.parse(
                    text
                )

                entry[
                    "functions"
                ] = [
                    node.name
                    for node in (
                        ast.walk(
                            tree
                        )
                    )
                    if isinstance(
                        node,
                        (
                            ast.FunctionDef,
                            ast.AsyncFunctionDef,
                        )
                    )
                ]

            except Exception as exc:
                entry[
                    "ast_error"
                ] = (
                    type(exc).__name__
                    + ":"
                    + str(exc)
                )

        lines = text.splitlines()

        for number, line in enumerate(
            lines,
            start=1
        ):
            low = line.lower()

            matched = [
                keyword
                for keyword
                in keywords
                if keyword.lower()
                in low
            ]

            if not matched:
                continue

            entry[
                "keyword_hits"
            ].append({
                "line":
                    number,

                "keywords":
                    sorted(
                        matched
                    ),

                "text":
                    line.strip()[:240],
            })

            if len(
                entry[
                    "keyword_hits"
                ]
            ) >= 40:
                break

        report[
            path.name
        ] = entry

    return report


def hook_candidates(
    source_audit
):
    executor = (
        source_audit.get(
            "vi6_95_scene_executor.py",
            {}
        )
    )

    functions = (
        executor.get(
            "functions"
        )
        or []
    )

    scored = []

    for function in functions:
        low = function.lower()

        score = 0

        if "scene" in low:
            score += 4

        if "render" in low:
            score += 3

        if "media" in low:
            score += 3

        if "execute" in low:
            score += 2

        if "resolve" in low:
            score += 2

        if score:
            scored.append({
                "function":
                    function,

                "score":
                    score,
            })

    scored.sort(
        key=lambda x:
            x["score"],
        reverse=True
    )

    return scored[:10]


def write_runtime_module():
    content = r'''#!/usr/bin/env python3

import hashlib
import json
import os
import re
from pathlib import Path


_DEFAULT_MANIFEST = (
    Path.home()
    / "ShortAutoPro"
    / "temp/vi700_canary/portfolio_manifest.json"
)

_CACHE = {
    "path": None,
    "mtime": None,
    "data": None,
}


def _sha256(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        while True:
            block = f.read(1024 * 1024)

            if not block:
                break

            h.update(block)

    return h.hexdigest()


def _scene_number(value):
    if isinstance(value, int):
        return value

    match = re.search(
        r"(\d+)",
        str(value or "")
    )

    if not match:
        return None

    return int(match.group(1))


def canary_enabled():
    return (
        os.environ.get(
            "VI700_PORTFOLIO_CANARY",
            "OFF"
        ).upper()
        == "ON"
    )


def _manifest_path():
    override = os.environ.get(
        "VI700_PORTFOLIO_MANIFEST"
    )

    if override:
        return Path(override)

    return _DEFAULT_MANIFEST


def load_manifest():
    path = _manifest_path()

    if not path.exists():
        return {}

    mtime = path.stat().st_mtime

    if (
        _CACHE["path"] == str(path)
        and _CACHE["mtime"] == mtime
        and _CACHE["data"] is not None
    ):
        return _CACHE["data"]

    data = json.loads(
        path.read_text(
            encoding="utf-8"
        )
    )

    _CACHE["path"] = str(path)
    _CACHE["mtime"] = mtime
    _CACHE["data"] = data

    return data


def resolve_scene_media(
    scene,
    original_path
):
    if not canary_enabled():
        return str(original_path)

    number = _scene_number(scene)

    if number is None:
        return str(original_path)

    manifest = load_manifest()

    scenes = (
        manifest.get("scenes")
        or {}
    )

    entry = (
        scenes.get(str(number))
        or {}
    )

    if not entry.get(
        "override_active"
    ):
        return str(original_path)

    candidate = entry.get(
        "canary_path"
    )

    expected = entry.get(
        "expected_sha256"
    )

    if not candidate:
        return str(original_path)

    path = Path(candidate)

    if not path.exists():
        return str(original_path)

    if expected:
        try:
            actual = _sha256(path)

        except Exception:
            return str(original_path)

        if actual != expected:
            return str(original_path)

    return str(path)


def describe_scene(scene):
    number = _scene_number(scene)

    if number is None:
        return {}

    return (
        load_manifest()
        .get("scenes", {})
        .get(str(number), {})
    )
'''

    RUNTIME_MODULE.write_text(
        content,
        encoding="utf-8"
    )

    os.chmod(
        RUNTIME_MODULE,
        0o755
    )

    return {
        "written":
            RUNTIME_MODULE.exists(),

        "path":
            str(
                RUNTIME_MODULE
            ),

        "sha256":
            (
                sha256(
                    RUNTIME_MODULE
                )
                if RUNTIME_MODULE.exists()
                else None
            ),
    }


def write_env():
    ENV_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    content = (
        '#!/data/data/com.termux/files/usr/bin/bash\n'
        'export VI700_PORTFOLIO_CANARY=ON\n'
        f'export VI700_PORTFOLIO_MANIFEST="{MANIFEST}"\n'
    )

    ENV_FILE.write_text(
        content,
        encoding="utf-8"
    )

    os.chmod(
        ENV_FILE,
        0o755
    )

    return {
        "path":
            str(
                ENV_FILE
            ),

        "sha256":
            sha256(
                ENV_FILE
            ),
    }


def evaluate():
    vi330 = load_gate(
        VI330,
        required=True
    )

    vi420 = load_gate(
        VI420,
        required=True
    )

    vi500 = load_gate(
        VI500,
        required=True
    )

    vi600 = load_gate(
        VI600,
        required=True
    )

    vi650 = load_gate(
        VI650,
        required=True
    )

    short_id = str(
        vi650.get(
            "short_id"
        )
        or vi600.get(
            "short_id"
        )
        or _sap_resolve_short_id()
    )

    current = current_media_map(
        vi500
    )

    portfolio = portfolio_map(
        vi650
    )

    fallback_errors = []

    for scene in range(
        1,
        13
    ):
        item = current.get(
            scene,
            {}
        )

        path_value = item.get(
            "path"
        )

        if not path_value:
            fallback_errors.append(
                f"scene_{scene}_current_path_missing"
            )

            continue

        path = Path(
            path_value
        )

        if not path.exists():
            fallback_errors.append(
                f"scene_{scene}_current_media_missing"
            )

    scene7_audit = scene7_strict_audit(
        vi650
    )

    staged = {}

    stage_errors = {}

    for scene in sorted(
        ACTIVE_OVERRIDE_SCENES
    ):
        asset = source_asset_for_scene(
            scene,
            portfolio,
            vi600,
            vi420
        )

        result = copy_canary_asset(
            scene,
            asset
        )

        if result.get(
            "copied"
        ):
            staged[
                scene
            ] = result

        else:
            stage_errors[
                scene
            ] = result


    active_hashes = {}

    active_titles = {}

    for scene, asset in (
        staged.items()
    ):
        active_hashes.setdefault(
            asset["sha256"],
            []
        ).append(
            scene
        )

        title = str(
            asset.get(
                "title"
            )
            or ""
        )

        if title:
            active_titles.setdefault(
                title,
                []
            ).append(
                scene
            )

    duplicate_hashes = {
        digest:
            scenes
        for digest, scenes
        in active_hashes.items()
        if len(scenes) > 1
    }

    duplicate_titles = {
        title:
            scenes
        for title, scenes
        in active_titles.items()
        if len(scenes) > 1
    }

    # Scene 1/4 same source is now explicitly
    # NON-ACTIVE duplication and therefore not a blocker.
    scene1_candidate = (
        vi330.get(
            "candidate"
        )
        or {}
    )

    scene1_validation = validate_asset(
        scene1_candidate
    )

    scene4_source = (
        vi600.get(
            "scene4_factual_source"
        )
        or {}
    )

    scene4_validation = (
        validate_asset(
            scene4_source
        )
        if scene4_source.get(
            "sandbox_path"
        )
        else {
            "valid": False,
            "reason":
                "scene4_source_missing",
        }
    )

    shared_case_source = (
        scene1_validation.get(
            "valid"
        )
        and scene4_validation.get(
            "valid"
        )
        and scene1_validation.get(
            "sha256"
        )
        == scene4_validation.get(
            "sha256"
        )
    )

    manifest_scenes = {}

    for scene in range(
        1,
        13
    ):
        current_item = (
            current.get(
                scene,
                {}
            )
        )

        original_path = (
            current_item.get(
                "path"
            )
        )

        active = (
            scene in staged
        )

        asset = (
            staged.get(
                scene
            )
            or {}
        )

        if active:
            mode = (
                "CANARY_IMAGE_OVERRIDE"
            )

        elif scene == 1:
            mode = (
                "LEGACY_BASE_WITH_ARCHIVAL_INSERT_RESERVED"
            )

        elif scene == 4:
            mode = (
                "LEGACY_WITH_FACTUAL_FRAME_RESERVED"
            )

        elif scene in {
            5,
            6,
        }:
            mode = (
                "LEGACY_ANONYMOUS_HUMAN_PENDING"
            )

        elif scene == 7:
            mode = (
                "LEGACY_STRICT_VIDEO_REJECTED"
            )

        elif scene == 12:
            mode = (
                "LEGACY_FACTUAL_DOCUMENT_HOLD"
            )

        elif scene == 2:
            mode = (
                "KEEP_CURRENT_VERIFIED"
            )

        else:
            mode = (
                "LEGACY_KEEP_CURRENT"
            )

        manifest_scenes[
            str(scene)
        ] = {
            "scene":
                scene,

            "original_path":
                original_path,

            "override_active":
                active,

            "mode":
                mode,

            "canary_path":
                asset.get(
                    "canary_path"
                ),

            "expected_sha256":
                asset.get(
                    "sha256"
                ),

            "family":
                asset.get(
                    "family"
                ),

            "dimensions":
                asset.get(
                    "dimensions"
                ),

            "title":
                asset.get(
                    "title"
                ),

            "license":
                asset.get(
                    "license"
                ),

            "license_score":
                asset.get(
                    "license_score"
                ),
        }

    manifest_payload = {
        "version":
            VERSION,

        "short_id":
            short_id,

        "canary_only":
            True,

        "active_override_scenes":
            sorted(
                staged
            ),

        "scenes":
            manifest_scenes,

        "special_assets": {
            "scene_1_archival_video": {
                "ready":
                    scene1_validation.get(
                        "valid",
                        False
                    ),

                "active_in_first_canary":
                    False,

                "path":
                    scene1_candidate.get(
                        "sandbox_path"
                    ),

                "sha256":
                    scene1_candidate.get(
                        "sha256"
                    ),

                "reason":
                    "low_resolution_hybrid_insert_reserved",
            },

            "scene_4_factual_source": {
                "ready":
                    scene4_validation.get(
                        "valid",
                        False
                    ),

                "active_in_first_canary":
                    False,

                "path":
                    scene4_source.get(
                        "sandbox_path"
                    ),

                "sha256":
                    scene4_source.get(
                        "sha256"
                    ),

                "reason":
                    "frame_derivation_not_yet_enabled",
            },
        },

        "production_media_mutated":
            False,

        "production_plan_mutated":
            False,

        "renderer_activation":
            False,
    }

    MANIFEST.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    MANIFEST.write_text(
        json.dumps(
            manifest_payload,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    runtime = write_runtime_module()

    env_info = write_env()

    source_audit = (
        source_code_audit()
    )

    hooks = hook_candidates(
        source_audit
    )


    blockers = []

    if fallback_errors:
        blockers.append(
            "legacy_fallback_media_missing"
        )

    if stage_errors:
        blockers.append(
            "active_canary_asset_validation_failed"
        )

    if duplicate_hashes:
        blockers.append(
            "active_override_duplicate_hash"
        )

    if duplicate_titles:
        blockers.append(
            "active_override_duplicate_title"
        )

    if len(staged) < 3:
        blockers.append(
            "insufficient_safe_canary_overrides"
        )

    if not runtime[
        "written"
    ]:
        blockers.append(
            "runtime_override_module_missing"
        )

    if not MANIFEST.exists():
        blockers.append(
            "canary_manifest_missing"
        )

    warnings = []

    if shared_case_source:
        warnings.append(
            "scene1_scene4_shared_source_nonactive_duplicate_allowed"
        )

    if not scene7_audit[
        "passed"
    ]:
        warnings.append(
            "scene7_false_positive_rejected_keep_legacy"
        )

    warnings.extend([
        "scene1_hybrid_insert_reserved_for_later_canary",
        "scene4_frame_derivation_reserved_for_later_canary",
        "scene5_scene6_anonymous_human_pending_keep_legacy",
        "scene12_factual_document_hold_keep_legacy",
    ])

    canary_ready = (
        not blockers
        and len(staged) >= 3
    )

    production_ready = False

    corrections = {
        "vi650_duplicate_title_blocker":
            (
                "DOWNGRADED_NONACTIVE_SHARED_SOURCE"
                if shared_case_source
                else
                "NOT_PRESENT"
            ),

        "scene7_generic_elevator_match":
            "HARDENED_STRONG_VISUAL_CONTEXT_REQUIRED",

        "schofield_farm_candidate":
            (
                "REJECTED"
                if not scene7_audit[
                    "passed"
                ]
                else "NOT_SELECTED"
            ),

        "first_canary_policy":
            "ONLY_PROVEN_SAFE_IMAGE_OVERRIDES",

        "legacy_fallback":
            "MANDATORY_FOR_EVERY_SCENE",

        "renderer_hook":
            "PREPARED_NOT_ACTIVATED",

        "automatic_replace":
            False,
    }

    report = {
        "version":
            VERSION,

        "status":
            (
                "VI700_CANARY_PORTFOLIO_READY"
                if canary_ready
                else "HOLD"
            ),

        "short_id":
            short_id,

        "canary_ready":
            canary_ready,

        "production_ready":
            production_ready,

        "corrections":
            corrections,

        "active_override_scenes":
            sorted(
                staged
            ),

        "active_override_count":
            len(
                staged
            ),

        "staged_assets":
            staged,

        "stage_errors":
            stage_errors,

        "legacy_fallback_errors":
            fallback_errors,

        "scene7_strict_audit":
            scene7_audit,

        "scene1_validation":
            scene1_validation,

        "scene4_validation":
            scene4_validation,

        "shared_case_source":
            shared_case_source,

        "active_duplicate_hashes":
            duplicate_hashes,

        "active_duplicate_titles":
            duplicate_titles,

        "manifest": {
            "path":
                str(
                    MANIFEST
                ),

            "sha256":
                sha256(
                    MANIFEST
                ),
        },

        "runtime_module":
            runtime,

        "environment_file":
            env_info,

        "source_code_audit":
            source_audit,

        "hook_candidates":
            hooks,

        "blockers":
            blockers,

        "warnings":
            warnings,

        "network_executed":
            False,

        "download_executed":
            False,

        "production_media_mutated":
            False,

        "production_plan_mutated":
            False,

        "core_source_mutated":
            False,

        "renderer_activation":
            False,

        "automatic_replace":
            False,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,
    }

    OUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUT.write_text(
        json.dumps(
            {"gate": report},
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return report


if __name__ == "__main__":
    r = evaluate()

    print()
    print(
        "=============================================="
    )
    print(
        " VI700 CANARY PORTFOLIO BUILDER"
    )
    print(
        "=============================================="
    )

    print(
        "STATUS:",
        r["status"]
    )

    print(
        "CANARY READY:",
        r["canary_ready"]
    )

    print(
        "PRODUCTION READY:",
        r["production_ready"]
    )

    print(
        "ACTIVE OVERRIDES:",
        r[
            "active_override_scenes"
        ]
    )

    print(
        "COUNT:",
        r[
            "active_override_count"
        ]
    )

    print()
    print(
        "===== CORRECTIONS ====="
    )

    for key, value in (
        r["corrections"].items()
    ):
        print(
            key,
            "=",
            value
        )

    print()
    print(
        "===== ACTIVE CANARY MEDIA ====="
    )

    for scene, item in (
        r[
            "staged_assets"
        ].items()
    ):
        print(
            "SCENE",
            scene,
            "|",
            item[
                "title"
            ]
        )

        print(
            "   PATH:",
            item[
                "canary_path"
            ]
        )

        print(
            "   DIMENSIONS:",
            item[
                "dimensions"
            ]
        )

        print(
            "   SHA256:",
            item[
                "sha256"
            ]
        )

        print(
            "   LICENSE:",
            item[
                "license"
            ]
        )

    print()
    print(
        "===== SCENE 7 STRICT AUDIT ====="
    )

    print(
        r[
            "scene7_strict_audit"
        ]
    )

    print()
    print(
        "SCENE1/4 SHARED SOURCE:",
        r[
            "shared_case_source"
        ]
    )

    print(
        "ACTIVE DUPLICATE HASHES:",
        r[
            "active_duplicate_hashes"
        ]
    )

    print(
        "ACTIVE DUPLICATE TITLES:",
        r[
            "active_duplicate_titles"
        ]
    )

    print()
    print(
        "MANIFEST:",
        r["manifest"]
    )

    print(
        "RUNTIME MODULE:",
        r[
            "runtime_module"
        ]
    )

    print(
        "CANARY ENV:",
        r[
            "environment_file"
        ]
    )

    print()
    print(
        "===== RENDERER HOOK CANDIDATES ====="
    )

    for item in (
        r[
            "hook_candidates"
        ]
    ):
        print(
            item
        )

    executor = (
        r[
            "source_code_audit"
        ].get(
            "vi6_95_scene_executor.py",
            {}
        )
    )

    print()
    print(
        "EXECUTOR FUNCTIONS:",
        executor.get(
            "functions"
        )
    )

    print(
        "EXECUTOR SHA256:",
        executor.get(
            "sha256"
        )
    )

    print()
    print(
        "BLOCKERS:",
        r["blockers"]
    )

    print(
        "WARNINGS:",
        r["warnings"]
    )

    print()
    print(
        "NETWORK EXECUTED:",
        r[
            "network_executed"
        ]
    )

    print(
        "DOWNLOAD EXECUTED:",
        r[
            "download_executed"
        ]
    )

    print(
        "PRODUCTION MEDIA MUTATED:",
        r[
            "production_media_mutated"
        ]
    )

    print(
        "CORE SOURCE MUTATED:",
        r[
            "core_source_mutated"
        ]
    )

    print(
        "RENDERER ACTIVATION:",
        r[
            "renderer_activation"
        ]
    )

    print(
        "FFMPEG EXECUTED:",
        r[
            "ffmpeg_executed"
        ]
    )

    print(
        "VIDEO GENERATED:",
        r[
            "video_generated"
        ]
    )
