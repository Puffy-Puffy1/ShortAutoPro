#!/usr/bin/env python3

from __future__ import annotations

import ast
import hashlib
import inspect
import json
import os
import py_compile
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path


ROOT = Path.home() / "ShortAutoPro"

SHORT_ID = os.environ.get(
    "SHORT_ID",
    "2026-09-02_2358",
).strip()


PASS = 0
WARN = 0
FAIL = 0

RESULTS = []


def section(title):

    print()
    print("=" * 76)
    print(title)
    print("=" * 76)


def record(level, name, detail=""):

    global PASS, WARN, FAIL

    if level == "PASS":
        PASS += 1

    elif level == "WARN":
        WARN += 1

    elif level == "FAIL":
        FAIL += 1

    RESULTS.append(
        {
            "level": level,
            "name": name,
            "detail": detail,
        }
    )

    suffix = (
        f" | {detail}"
        if detail
        else ""
    )

    print(
        f"{level} | {name}{suffix}"
    )


def sha256(path):

    path = Path(path)

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b"",
        ):

            h.update(chunk)

    return h.hexdigest()


def load_source(name):

    path = ROOT / name

    return path.read_text(
        encoding="utf-8",
        errors="replace",
    )


def compile_file(name):

    path = ROOT / name

    if not path.is_file():

        record(
            "FAIL",
            f"COMPILE_{name}",
            "arquivo ausente",
        )

        return False

    try:

        py_compile.compile(
            str(path),
            doraise=True,
        )

        record(
            "PASS",
            f"COMPILE_{name}",
        )

        return True

    except Exception as exc:

        record(
            "FAIL",
            f"COMPILE_{name}",
            f"{type(exc).__name__}: {exc}",
        )

        return False


# ============================================================
# 1. PROJECT
# ============================================================

section(
    "1. PROJECT / CRITICAL FILES"
)

critical = [
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "legenda_dinamica.py",
    "visual_selection_engine_v4.py",
    "visual_selection_bridge_v42.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
    "visual_scene_commit_lock_v1.py",
    "fresh_render_guard_v1.py",
    "render_input_fingerprint_v1.py",
]


for name in critical:

    path = ROOT / name

    if path.is_file():

        record(
            "PASS",
            f"FILE_{name}",
            f"{path.stat().st_size} bytes",
        )

    else:

        record(
            "FAIL",
            f"FILE_{name}",
            "ausente",
        )


# ============================================================
# 2. HASHES
# ============================================================

section(
    "2. CORE HASHES"
)

for name in (
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "visual_selection_engine_v4.py",
    "visual_selection_bridge_v42.py",
):

    path = ROOT / name

    if path.is_file():

        print(
            f"SHA256 {name} "
            f"{sha256(path)}"
        )


# ============================================================
# 3. COMPILE
# ============================================================

section(
    "3. PYTHON / SHELL SYNTAX"
)

for name in (
    "midia.py",
    "video.py",
    "v6.py",
    "legenda_dinamica.py",
    "visual_selection_engine_v4.py",
    "visual_selection_bridge_v42.py",
    "media_diversity_guard_v1.py",
    "media_provenance_capture_v1.py",
    "visual_scene_commit_lock_v1.py",
    "fresh_render_guard_v1.py",
    "render_input_fingerprint_v1.py",
):

    compile_file(name)


try:

    result = subprocess.run(
        [
            "bash",
            "-n",
            str(
                ROOT
                / "gerar_short.sh"
            ),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    if result.returncode == 0:

        record(
            "PASS",
            "GERAR_SHORT_SYNTAX",
        )

    else:

        record(
            "FAIL",
            "GERAR_SHORT_SYNTAX",
            result.stderr[-500:],
        )

except Exception as exc:

    record(
        "FAIL",
        "GERAR_SHORT_SYNTAX",
        str(exc),
    )


# ============================================================
# 4. LOAD VSE4
# ============================================================

section(
    "4. VSE4 RUNTIME"
)

vse = None

try:

    vse = runpy.run_path(
        str(
            ROOT
            / "visual_selection_engine_v4.py"
        ),
        run_name="visual_master_audit_v3",
    )

    record(
        "PASS",
        "VSE4_RUNTIME_LOAD",
    )

except Exception as exc:

    record(
        "FAIL",
        "VSE4_RUNTIME_LOAD",
        f"{type(exc).__name__}: {exc}",
    )


required_vse = (
    "score_candidate",
    "candidate_text",
    "tokens",
    "geo_hits",
    "concept_hits",
    "provider",
    "source_group",
    "media_type",
    "candidate_key",
    "must_tier",
)


if vse is not None:

    missing = [
        name
        for name in required_vse
        if not callable(
            vse.get(name)
        )
    ]

    if missing:

        record(
            "FAIL",
            "VSE4_RUNTIME_API",
            ",".join(missing),
        )

    else:

        record(
            "PASS",
            "VSE4_RUNTIME_API",
        )


# ============================================================
# 5. SELF TEST
# ============================================================

section(
    "5. VSE4 SELF TEST"
)


if vse and callable(
    vse.get("self_test")
):

    try:

        vse[
            "self_test"
        ]()

        record(
            "PASS",
            "VSE4_SELF_TEST",
        )

    except Exception as exc:

        record(
            "FAIL",
            "VSE4_SELF_TEST",
            f"{type(exc).__name__}: {exc}",
        )

else:

    record(
        "FAIL",
        "VSE4_SELF_TEST",
        "self_test ausente",
    )


# ============================================================
# 6. MULTI-THEME SEMANTIC MATRIX
# ============================================================

section(
    "6. MULTI-THEME VISUAL SEMANTIC MATRIX"
)


def make_candidate(
    title,
    provider_name="Pixabay",
    score=150,
    must="2/2",
    media="foto",
    cid=None,
):

    return {
        "provider": provider_name,
        "tipo": media,
        "title": title,
        "score": score,
        "must": must,
        "width": 1920,
        "height": 1080,
        "id": (
            cid
            or
            hashlib.md5(
                title.encode()
            ).hexdigest()[:10]
        ),
    }


semantic_cases = [

    (
        "CRIME_INVESTIGATION",
        "Police investigation in an apartment crime scene",
        "police detective investigation apartment crime scene",
        "smiling woman relaxing drinking coffee bedroom",
    ),

    (
        "FORENSICS",
        "Forensic report revealed evidence during investigation",
        "forensic evidence laboratory investigation report",
        "pills medication tablets medicine pharmacy",
    ),

    (
        "COURT",
        "The defendants were convicted in court after the trial",
        "courtroom judge trial courthouse justice",
        "bedroom lifestyle smiling woman sofa",
    ),

    (
        "SPACE",
        "Rocket launch began the space mission",
        "rocket launch spacecraft astronaut space",
        "coffee shop woman relaxing lifestyle",
    ),

    (
        "WILDFIRE",
        "Firefighters fought a major forest fire",
        "forest fire smoke firefighter emergency rescue",
        "fashion model smiling studio portrait",
    ),

    (
        "TECHNOLOGY",
        "Researchers analyzed computer data and digital networks",
        "computer technology digital network data",
        "vacation beach couple relaxing",
    ),

    (
        "MILITARY",
        "Military forces entered combat during the conflict",
        "military soldiers army battle war combat",
        "shopping fashion smiling lifestyle",
    ),

    (
        "OCEAN",
        "Researchers explored the ocean underwater",
        "ocean underwater research sea water",
        "office business meeting coffee",
    ),

    (
        "BUSINESS",
        "The company analyzed financial market data",
        "business company office finance market data",
        "forest mountain vacation hiking",
    ),
]


if vse:

    score_candidate = vse[
        "score_candidate"
    ]

    semantic_pass = 0

    for (
        name,
        scene,
        good_title,
        bad_title,
    ) in semantic_cases:

        state = {
            "providers": [],
            "groups": [],
            "types": [],
            "keys": [],
        }


        try:

            good = score_candidate(
                make_candidate(
                    good_title,
                    provider_name="Wikimedia",
                    score=135,
                ),
                scene,
                state,
            )

            bad = score_candidate(
                make_candidate(
                    bad_title,
                    provider_name="Pixabay",
                    score=220,
                ),
                scene,
                state,
            )


            good_eff = float(
                good.get(
                    "effective",
                    -99999999,
                )
            )

            bad_eff = float(
                bad.get(
                    "effective",
                    -99999999,
                )
            )


            print()
            print(
                f"{name}_GOOD="
                f"{good_eff:.2f}"
            )

            print(
                f"{name}_BAD="
                f"{bad_eff:.2f}"
            )

            print(
                f"{name}_GOOD_HARD="
                f"{good.get('hard_mismatch')}"
            )

            print(
                f"{name}_BAD_HARD="
                f"{bad.get('hard_mismatch')}"
            )


            ok = (
                not good.get(
                    "hard_mismatch",
                    False,
                )
                and
                good_eff
                >
                bad_eff
            )


            if ok:

                semantic_pass += 1

                record(
                    "PASS",
                    f"SEMANTIC_{name}",
                    f"{good_eff:.1f} > {bad_eff:.1f}",
                )

            else:

                record(
                    "FAIL",
                    f"SEMANTIC_{name}",
                    f"{good_eff:.1f} <= {bad_eff:.1f}",
                )


        except Exception as exc:

            record(
                "FAIL",
                f"SEMANTIC_{name}",
                f"{type(exc).__name__}: {exc}",
            )


    print()
    print(
        "SEMANTIC_MATRIX_SCORE="
        f"{semantic_pass}/{len(semantic_cases)}"
    )


# ============================================================
# 7. GEOGRAPHY MATRIX
# ============================================================

section(
    "7. GEOGRAPHIC CONTRADICTION MATRIX"
)


geo_cases = [

    (
        "SP_VS_NY",
        "Investigação em São Paulo Brasil",
        "Apartment building Sao Paulo Brazil",
        "Empire State Building Manhattan New York",
    ),

    (
        "RIO_VS_LONDON",
        "Evento no Rio de Janeiro Brasil",
        "Rio de Janeiro Copacabana Brazil",
        "London Tower Bridge United Kingdom",
    ),

    (
        "PARIS_VS_TOKYO",
        "Caso ocorrido em Paris France",
        "Paris France Eiffel Tower",
        "Tokyo Shibuya Japan",
    ),

    (
        "LONDON_VS_NYC",
        "Investigation in London United Kingdom",
        "London Westminster United Kingdom",
        "New York Manhattan USA",
    ),
]


if vse:

    for (
        name,
        scene,
        good_title,
        bad_title,
    ) in geo_cases:

        state = {
            "providers": [],
            "groups": [],
            "types": [],
            "keys": [],
        }

        try:

            good = score_candidate(
                make_candidate(
                    good_title,
                    "Wikimedia",
                    120,
                ),
                scene,
                state,
            )

            bad = score_candidate(
                make_candidate(
                    bad_title,
                    "Pixabay",
                    230,
                ),
                scene,
                state,
            )


            bad_hard = bool(
                bad.get(
                    "hard_mismatch"
                )
            )

            good_safe = not bool(
                good.get(
                    "hard_mismatch"
                )
            )


            if (
                bad_hard
                and
                good_safe
                and
                good["effective"]
                >
                bad["effective"]
            ):

                record(
                    "PASS",
                    f"GEO_{name}",
                )

            else:

                record(
                    "FAIL",
                    f"GEO_{name}",
                    json.dumps(
                        {
                            "good":
                                good.get(
                                    "effective"
                                ),

                            "bad":
                                bad.get(
                                    "effective"
                                ),

                            "bad_hard":
                                bad_hard,

                            "good_safe":
                                good_safe,
                        },
                        ensure_ascii=False,
                    ),
                )


        except Exception as exc:

            record(
                "FAIL",
                f"GEO_{name}",
                str(exc),
            )


# ============================================================
# 8. PROVIDER DIVERSITY
# ============================================================

section(
    "8. PROVIDER / SOURCE DIVERSITY"
)


if vse:

    state = {
        "providers": [
            "pixabay",
            "pixabay",
        ],

        "groups": [
            "pixabay",
            "pixabay",
        ],

        "types": [
            "photo",
            "photo",
        ],

        "keys": [],
    }


    providers_to_test = [
        "Pixabay",
        "Pexels",
        "Wikimedia",
        "Coverr",
    ]


    candidates = [

        make_candidate(
            "police investigation apartment evidence",
            provider_name=p,
            score=150,
            must="2/2",
            media=(
                "video"
                if p in (
                    "Pexels",
                    "Coverr",
                )
                else "foto"
            ),
            cid=f"diversity_{p}",
        )

        for p in providers_to_test
    ]


    try:

        scored = []

        for c in candidates:

            result = score_candidate(
                c,
                "police investigation apartment evidence",
                state,
            )

            scored.append(
                (
                    result[
                        "effective"
                    ],
                    result,
                )
            )


        scored.sort(
            key=lambda item:
                item[0],
            reverse=True,
        )


        for effective, result in scored:

            print(
                "DIVERSITY_SCORE "
                f"{result.get('provider')} "
                f"{effective:.2f}"
            )


        winner = scored[
            0
        ][1]


        print(
            "DIVERSITY_WINNER="
            f"{winner.get('provider')}"
        )


        if (
            winner.get(
                "provider"
            )
            !=
            "pixabay"
        ):

            record(
                "PASS",
                "REPEATED_PROVIDER_PENALTY",
                winner.get(
                    "provider",
                    "",
                ),
            )

        else:

            record(
                "WARN",
                "REPEATED_PROVIDER_PENALTY",
                "Pixabay continuou vencedor em candidatos equivalentes",
            )


    except Exception as exc:

        record(
            "FAIL",
            "PROVIDER_DIVERSITY_RUNTIME",
            str(exc),
        )


# ============================================================
# 9. REPEATED ASSET KEY
# ============================================================

section(
    "9. EXACT ASSET REPEAT CONTROL"
)


if vse:

    try:

        repeated = make_candidate(
            "police investigation apartment",
            "Pexels",
            150,
            "2/2",
            "video",
            "SAME_ASSET_001",
        )

        fresh = make_candidate(
            "police investigation apartment",
            "Pexels",
            150,
            "2/2",
            "video",
            "FRESH_ASSET_002",
        )


        repeated_key = vse[
            "candidate_key"
        ](
            repeated
        )


        state = {
            "providers": [],
            "groups": [],
            "types": [],
            "keys": [
                repeated_key
            ],
        }


        r1 = score_candidate(
            repeated,
            "police investigation apartment",
            state,
        )

        r2 = score_candidate(
            fresh,
            "police investigation apartment",
            state,
        )


        print(
            "REPEATED_EFFECTIVE=",
            r1["effective"],
        )

        print(
            "FRESH_EFFECTIVE=",
            r2["effective"],
        )


        if (
            r2[
                "effective"
            ]
            >
            r1[
                "effective"
            ]
        ):

            record(
                "PASS",
                "EXACT_ASSET_REPEAT_PENALTY",
            )

        else:

            record(
                "WARN",
                "EXACT_ASSET_REPEAT_PENALTY",
                "asset repetido não recebeu penalidade suficiente",
            )


    except Exception as exc:

        record(
            "FAIL",
            "EXACT_ASSET_REPEAT_CONTROL",
            str(exc),
        )


# ============================================================
# 10. PROVIDER ACQUISITION STATIC AUDIT
# ============================================================

section(
    "10. PROVIDER ACQUISITION PATH"
)


try:

    midia_src = load_source(
        "midia.py"
    )

    midia_tree = ast.parse(
        midia_src
    )


    provider_defs = {
        "pexels_video",
        "pexels_foto",
        "pixabay_video",
        "pixabay_foto",
        "coverr_video",
        "buscar_wikimedia_fotos",
        "buscar_todos_candidatos",
    }


    defs = {
        node.name:
            node

        for node in midia_tree.body

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        )
    }


    for name in sorted(
        provider_defs
    ):

        if name in defs:

            record(
                "PASS",
                f"PROVIDER_FUNCTION_{name}",
            )

        else:

            record(
                "WARN",
                f"PROVIDER_FUNCTION_{name}",
                "não encontrada",
            )


    search_fn = defs.get(
        "buscar_todos_candidatos"
    )


    if search_fn:

        calls = set()

        for node in ast.walk(
            search_fn
        ):

            if isinstance(
                node,
                ast.Call,
            ):

                if isinstance(
                    node.func,
                    ast.Name,
                ):

                    calls.add(
                        node.func.id
                    )


        expected_calls = {
            "pexels_video",
            "pexels_foto",
            "pixabay_video",
            "pixabay_foto",
            "coverr_video",
            "buscar_wikimedia_fotos",
        }


        print(
            "ACQUISITION_CALLS=",
            sorted(calls),
        )


        for name in sorted(
            expected_calls
        ):

            if name in calls:

                record(
                    "PASS",
                    f"ACQUISITION_CALL_{name}",
                )

            else:

                record(
                    "WARN",
                    f"ACQUISITION_CALL_{name}",
                    "não chamado diretamente por buscar_todos_candidatos",
                )


except Exception as exc:

    record(
        "FAIL",
        "PROVIDER_ACQUISITION_AUDIT",
        f"{type(exc).__name__}: {exc}",
    )


# ============================================================
# 11. PROVIDER ENV CONFIG - NAMES ONLY
# ============================================================

section(
    "11. PROVIDER CONFIGURATION PRESENCE"
)


try:

    env_names = sorted(
        set(
            re.findall(
                r'''os\.getenv\(\s*["']([^"']+)["']''',
                midia_src,
            )
        )
    )


    provider_envs = [
        name
        for name in env_names
        if any(
            term in name.upper()
            for term in (
                "PEXELS",
                "PIXABAY",
                "COVERR",
                "WIKI",
            )
        )
    ]


    print(
        "PROVIDER_ENV_NAMES=",
        provider_envs,
    )


    if provider_envs:

        record(
            "PASS",
            "PROVIDER_ENV_CONFIGURATION_REFERENCED",
            f"{len(provider_envs)} variáveis",
        )

    else:

        record(
            "WARN",
            "PROVIDER_ENV_CONFIGURATION_REFERENCED",
            "nenhuma variável detectada",
        )


except Exception as exc:

    record(
        "WARN",
        "PROVIDER_ENV_AUDIT",
        str(exc),
    )


# ============================================================
# 12. MIDIA -> V42 BRIDGE INTEGRATION
# ============================================================

section(
    "12. REAL MIDIA -> V42 BRIDGE INTEGRATION"
)


try:

    bridge_refs = [
        (
            i + 1,
            line.strip(),
        )

        for i, line in enumerate(
            midia_src.splitlines()
        )

        if (
            "visual_selection_bridge_v42"
            in line
            or
            "rank_pool("
            in line
            or
            "VSE42"
            in line
            or
            "VSE422"
            in line
        )
    ]


    print(
        "BRIDGE_REFERENCES="
        f"{len(bridge_refs)}"
    )


    for line_no, text in bridge_refs[
        :50
    ]:

        print(
            f"LINE {line_no}: "
            f"{text}"
        )


    if any(
        "visual_selection_bridge_v42"
        in text
        for _, text in bridge_refs
    ):

        record(
            "PASS",
            "MIDIA_IMPORTS_V42_BRIDGE",
        )

    else:

        record(
            "FAIL",
            "MIDIA_IMPORTS_V42_BRIDGE",
            "bridge não referenciado",
        )


    if any(
        "rank_pool("
        in text
        for _, text in bridge_refs
    ):

        record(
            "PASS",
            "MIDIA_CALLS_V42_RANK_POOL",
        )

    else:

        record(
            "FAIL",
            "MIDIA_CALLS_V42_RANK_POOL",
            "rank_pool não encontrado",
        )


except Exception as exc:

    record(
        "FAIL",
        "MIDIA_BRIDGE_STATIC_AUDIT",
        str(exc),
    )


# ============================================================
# 13. BRIDGE LOAD / API
# ============================================================

section(
    "13. V42 BRIDGE RUNTIME API"
)


try:

    bridge = runpy.run_path(
        str(
            ROOT
            / "visual_selection_bridge_v42.py"
        ),
        run_name="visual_master_audit_bridge_v3",
    )


    for name in (
        "rank_pool",
        "reset_state",
    ):

        if callable(
            bridge.get(name)
        ):

            record(
                "PASS",
                f"BRIDGE_API_{name}",
                str(
                    inspect.signature(
                        bridge[name]
                    )
                ),
            )

        else:

            record(
                "FAIL",
                f"BRIDGE_API_{name}",
                "ausente",
            )


except Exception as exc:

    record(
        "FAIL",
        "BRIDGE_RUNTIME_LOAD",
        f"{type(exc).__name__}: {exc}",
    )


# ============================================================
# 14. COMMIT LOCK STATIC INTEGRATION
# ============================================================

section(
    "14. SCENE COMMIT LOCK"
)


try:

    diversity_src = load_source(
        "media_diversity_guard_v1.py"
    )


    commit_mentions = (
        diversity_src.count(
            "visual_scene_commit_lock_v1"
        )
        +
        diversity_src.count(
            "SCENE_COMMIT_LOCK"
        )
    )


    print(
        "COMMIT_LOCK_MENTIONS=",
        commit_mentions,
    )


    if commit_mentions > 0:

        record(
            "PASS",
            "COMMIT_LOCK_BRIDGE_PRESENT",
        )

    else:

        record(
            "WARN",
            "COMMIT_LOCK_BRIDGE_PRESENT",
            "nenhuma integração encontrada no diversity guard",
        )


    lock_src = load_source(
        "visual_scene_commit_lock_v1.py"
    )


    if "COMMITTED" in lock_src:

        record(
            "PASS",
            "COMMIT_LOCK_COMMIT_PATH",
        )

    else:

        record(
            "WARN",
            "COMMIT_LOCK_COMMIT_PATH",
        )


    if "BLOCKED" in lock_src:

        record(
            "PASS",
            "COMMIT_LOCK_BLOCK_PATH",
        )

    else:

        record(
            "WARN",
            "COMMIT_LOCK_BLOCK_PATH",
        )


except Exception as exc:

    record(
        "WARN",
        "COMMIT_LOCK_AUDIT",
        str(exc),
    )


# ============================================================
# 15. CURRENT SHORT MEDIA INTEGRITY
# ============================================================

section(
    "15. CURRENT SHORT MEDIA INTEGRITY"
)


media_dir = (
    ROOT
    / "imagens"
    / f"short_{SHORT_ID}"
)


if media_dir.is_dir():

    total = 0
    bad_scenes = []
    extensions = {}
    hashes = {}


    for i in range(
        1,
        13,
    ):

        matches = list(
            media_dir.glob(
                f"scene_{i:02d}.*"
            )
        )

        total += len(matches)


        if len(matches) != 1:

            bad_scenes.append(
                (
                    i,
                    len(matches),
                )
            )


        for path in matches:

            ext = path.suffix.lower()

            extensions[
                ext
            ] = (
                extensions.get(
                    ext,
                    0,
                )
                +
                1
            )

            file_hash = sha256(
                path
            )

            hashes.setdefault(
                file_hash,
                []
            ).append(
                path.name
            )


    print(
        "MEDIA_TOTAL=",
        total,
    )

    print(
        "MEDIA_TYPES=",
        extensions,
    )


    if (
        total == 12
        and
        not bad_scenes
    ):

        record(
            "PASS",
            "MEDIA_12_OF_12",
        )

    else:

        record(
            "FAIL",
            "MEDIA_12_OF_12",
            str(bad_scenes),
        )


    duplicate_hashes = {
        h:
            names

        for h, names in hashes.items()

        if len(names) > 1
    }


    if duplicate_hashes:

        record(
            "WARN",
            "DUPLICATE_MEDIA_SHA",
            json.dumps(
                duplicate_hashes,
                ensure_ascii=False,
            ),
        )

    else:

        record(
            "PASS",
            "DUPLICATE_MEDIA_SHA",
            "nenhum",
        )


else:

    record(
        "WARN",
        "CURRENT_MEDIA_DIR",
        f"ausente: {media_dir}",
    )


# ============================================================
# 16. RENDER GUARD SAFETY
# ============================================================

section(
    "16. FRESH RENDER GUARD SAFETY"
)


try:

    guard = runpy.run_path(
        str(
            ROOT
            / "fresh_render_guard_v1.py"
        ),
        run_name="visual_master_guard_v3",
    )

    clean = guard[
        "clean"
    ]


    fake_id = (
        "AUDIT_V3_"
        +
        str(
            os.getpid()
        )
    )


    fake_temp = (
        ROOT
        / "temp"
        / fake_id
    )

    fake_temp.mkdir(
        parents=True,
        exist_ok=True,
    )


    fake_ass = (
        ROOT
        / "videos"
        / f"short_{fake_id}.ass"
    )

    fake_audio = (
        fake_temp
        / "audit.mp3"
    )

    fake_temp_video = (
        fake_temp
        / "video_sem_audio.mp4"
    )

    fake_final = (
        ROOT
        / "videos"
        / f"short_v6_{fake_id}.mp4"
    )


    fake_ass.write_text(
        "ASS_PROTECTED",
        encoding="utf-8",
    )

    fake_audio.write_bytes(
        b"AUDIO_PROTECTED"
    )

    fake_temp_video.write_bytes(
        b"TEMP_VIDEO"
    )

    fake_final.write_bytes(
        b"FINAL_VIDEO"
    )


    clean(
        fake_id
    )


    checks = {
        "ASS":
            fake_ass.exists(),

        "AUDIO":
            fake_audio.exists(),

        "TEMP_VIDEO_REMOVED":
            not fake_temp_video.exists(),

        "FINAL_REMOVED":
            not fake_final.exists(),
    }


    for name, ok in checks.items():

        record(
            (
                "PASS"
                if ok
                else "FAIL"
            ),
            f"RENDER_GUARD_{name}",
        )


    try:
        fake_ass.unlink(
            missing_ok=True
        )
    except Exception:
        pass


    try:
        shutil.rmtree(
            fake_temp,
            ignore_errors=True,
        )
    except Exception:
        pass


    try:
        fake_final.unlink(
            missing_ok=True
        )
    except Exception:
        pass


except Exception as exc:

    record(
        "FAIL",
        "RENDER_GUARD_TEST",
        f"{type(exc).__name__}: {exc}",
    )


# ============================================================
# 17. SUSPICIOUS STATIC PATTERNS
# ============================================================

section(
    "17. SUSPICIOUS STATIC PATTERNS"
)


patterns = {

    "MIDIA_BLIND_FIRST_CANDIDATE":
        r"\[\s*0\s*\]",

    "MIDIA_RANDOM_CHOICE":
        r"random\.choice",

    "MIDIA_HARDCODED_PIXABAY":
        r"provider.{0,30}pixabay",

    "BARE_EXCEPT":
        r"except\s*:",

}


for name, pattern in patterns.items():

    matches = re.findall(
        pattern,
        midia_src,
        flags=re.I,
    )


    count = len(matches)


    print(
        f"{name}_COUNT="
        f"{count}"
    )


    if name == "BARE_EXCEPT":

        if count == 0:

            record(
                "PASS",
                name,
            )

        else:

            record(
                "WARN",
                name,
                str(count),
            )

    else:

        # Estes padrões não são automaticamente bugs.
        # Apenas sinalizamos para inspeção.
        if count:

            record(
                "WARN",
                name,
                str(count),
            )

        else:

            record(
                "PASS",
                name,
            )


# ============================================================
# 18. FINAL SUMMARY
# ============================================================

section(
    "18. MASTER VISUAL AUDIT V3 SUMMARY"
)


print(
    f"PASS_COUNT={PASS}"
)

print(
    f"WARN_COUNT={WARN}"
)

print(
    f"FAIL_COUNT={FAIL}"
)


critical_failures = [
    r
    for r in RESULTS
    if r[
        "level"
    ] == "FAIL"
]


warnings = [
    r
    for r in RESULTS
    if r[
        "level"
    ] == "WARN"
]


print()
print(
    "===== FAILURES ====="
)


if critical_failures:

    for item in critical_failures:

        print(
            "FAIL "
            f"{item['name']} "
            f"{item['detail']}"
        )

else:

    print(
        "NONE"
    )


print()
print(
    "===== WARNINGS ====="
)


if warnings:

    for item in warnings:

        print(
            "WARN "
            f"{item['name']} "
            f"{item['detail']}"
        )

else:

    print(
        "NONE"
    )


report = {
    "short_id":
        SHORT_ID,

    "timestamp":
        time.time(),

    "pass":
        PASS,

    "warn":
        WARN,

    "fail":
        FAIL,

    "results":
        RESULTS,
}


manifest_dir = (
    ROOT
    / "manifests"
)

manifest_dir.mkdir(
    parents=True,
    exist_ok=True,
)


json_path = (
    manifest_dir
    / f"visual_master_audit_v3_{SHORT_ID}.json"
)


json_path.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)


print()
print(
    f"JSON_REPORT={json_path}"
)


if FAIL == 0:

    if WARN == 0:

        print(
            "VISUAL_MASTER_AUDIT_V3="
            "CERTIFIED"
        )

    else:

        print(
            "VISUAL_MASTER_AUDIT_V3="
            "PASS_WITH_WARNINGS"
        )

else:

    print(
        "VISUAL_MASTER_AUDIT_V3="
        "FAIL"
    )


print(
    "NETWORK_EXECUTED=NO"
)

print(
    "MEDIA_DOWNLOADED=NO"
)

print(
    "VIDEO_RENDERED=NO"
)

print(
    "CORE_FILES_MODIFIED=NO"
)


raise SystemExit(
    1
    if FAIL
    else 0
)
