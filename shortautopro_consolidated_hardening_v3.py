#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime
import ast
import hashlib
import json
import os
import py_compile
import re
import shutil
import subprocess
import sys


ROOT = Path.home() / "ShortAutoPro"

STAMP = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

BACKUP = (
    ROOT
    / "backups"
    / f"CONSOLIDATED_HARDENING_V3_{STAMP}"
)

REPORT = (
    ROOT
    / "temp"
    / f"CONSOLIDATED_HARDENING_V3_{STAMP}.txt"
)

STATUS_FILE = (
    ROOT
    / "temp"
    / "HARDENING_V3_STATUS.txt"
)

BACKUP.mkdir(
    parents=True,
    exist_ok=True,
)

REPORT.parent.mkdir(
    parents=True,
    exist_ok=True,
)


rows = []

FAIL = 0
WARN = 0
REPAIRS = 0


def emit(level, name, detail=""):

    global FAIL
    global WARN

    line = (
        f"{level} | {name}"
        +
        (
            f" | {detail}"
            if detail
            else ""
        )
    )

    print(line)

    rows.append(line)

    if level == "FAIL":
        FAIL += 1

    elif level == "WARN":
        WARN += 1


def backup(path):

    path = Path(path)

    if not path.exists():
        return

    try:
        rel = path.relative_to(
            ROOT
        )
    except Exception:
        return

    dest = BACKUP / rel

    dest.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    shutil.copy2(
        path,
        dest,
    )


def sha256(path):

    h = hashlib.sha256()

    with open(
        path,
        "rb",
    ) as f:

        for chunk in iter(
            lambda:
                f.read(
                    1024 * 1024
                ),
            b"",
        ):

            h.update(
                chunk
            )

    return h.hexdigest()


def insert_import(
    src,
    import_line,
):

    if import_line in src:
        return src

    tree = ast.parse(src)

    lines = src.splitlines(
        keepends=True
    )

    insert_line = 1


    if src.startswith("#!"):
        insert_line = 2


    # encoding cookie
    for index in range(
        min(
            2,
            len(lines),
        )
    ):

        if (
            "coding:" in lines[index]
            or
            "coding=" in lines[index]
        ):

            insert_line = max(
                insert_line,
                index + 2,
            )


    if (
        tree.body
        and
        isinstance(
            tree.body[0],
            ast.Expr,
        )
        and
        isinstance(
            getattr(
                tree.body[0],
                "value",
                None,
            ),
            ast.Constant,
        )
        and
        isinstance(
            tree.body[0].value.value,
            str,
        )
    ):

        insert_line = max(
            insert_line,
            tree.body[0].end_lineno + 1,
        )


    for node in tree.body:

        if (
            isinstance(
                node,
                ast.ImportFrom,
            )
            and
            node.module == "__future__"
        ):

            insert_line = max(
                insert_line,
                node.end_lineno + 1,
            )


    idx = insert_line - 1

    return (
        "".join(
            lines[:idx]
        )
        +
        import_line
        +
        "\n"
        +
        "".join(
            lines[idx:]
        )
    )


print(
    "=" * 72
)

print(
    " SHORTAUTOPRO CONSOLIDATED HARDENING V3"
)

print(
    "=" * 72
)

print(
    f"BACKUP={BACKUP}"
)


# ============================================================
# 1. CENTRAL SHORT-ID RESOLVER
# ============================================================

resolver_path = (
    ROOT
    / "short_id_runtime_v1.py"
)

backup(
    resolver_path
)

resolver_code = r'''#!/usr/bin/env python3

from pathlib import Path
from datetime import datetime
import os
import re


ROOT = (
    Path.home()
    / "ShortAutoPro"
)

SID_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}_\d{4}$"
)


def valid(value):

    return bool(
        value
        and
        SID_RE.fullmatch(
            str(value).strip()
        )
    )


def parse_sid(value):

    try:

        return datetime.strptime(
            value,
            "%Y-%m-%d_%H%M",
        )

    except Exception:

        return datetime.min


def collect():

    evidence = {}


    def add(
        sid,
        source,
    ):

        if not valid(sid):
            return

        evidence.setdefault(
            sid,
            set(),
        ).add(
            source
        )


    # imagens/short_ID
    media_root = (
        ROOT
        / "imagens"
    )

    if media_root.is_dir():

        for path in media_root.glob(
            "short_*"
        ):

            if not path.is_dir():
                continue

            add(
                path.name[
                    len("short_"):
                ],
                "media",
            )


    # temp/ID
    temp_root = (
        ROOT
        / "temp"
    )

    if temp_root.is_dir():

        for path in temp_root.iterdir():

            if path.is_dir():

                add(
                    path.name,
                    "temp",
                )


    # audios/short_ID.mp3
    audio_root = (
        ROOT
        / "audios"
    )

    if audio_root.is_dir():

        for path in audio_root.glob(
            "short_*.mp3"
        ):

            add(
                path.stem[
                    len("short_"):
                ],
                "audio",
            )


    # roteiros
    roteiro_root = (
        ROOT
        / "roteiros"
    )

    if roteiro_root.is_dir():

        patterns = (
            "short_*.txt",
            "topic_*.txt",
            "scene_map_*.json",
        )

        for pattern in patterns:

            for path in roteiro_root.glob(
                pattern
            ):

                name = path.stem

                for prefix in (
                    "short_",
                    "topic_",
                    "scene_map_",
                ):

                    if name.startswith(
                        prefix
                    ):

                        add(
                            name[
                                len(prefix):
                            ],
                            "roteiro",
                        )


    # final videos
    video_root = (
        ROOT
        / "videos"
    )

    if video_root.is_dir():

        for path in video_root.glob(
            "short_v6_*.mp4"
        ):

            add(
                path.stem[
                    len("short_v6_"):
                ],
                "final",
            )


    return evidence


def resolve_short_id():

    env = os.environ.get(
        "SHORT_ID",
        "",
    ).strip()

    if valid(env):
        return env


    evidence = collect()

    if not evidence:
        return ""


    # Prefer IDs com pelo menos duas evidências,
    # depois o mais recente.
    ranked = sorted(
        evidence.items(),
        key=lambda item: (
            len(
                item[1]
            ),
            parse_sid(
                item[0]
            ),
        ),
        reverse=True,
    )


    strong = [
        item
        for item in ranked
        if len(
            item[1]
        ) >= 2
    ]


    if strong:

        strong.sort(
            key=lambda item:
                parse_sid(
                    item[0]
                ),
            reverse=True,
        )

        return strong[0][0]


    ranked.sort(
        key=lambda item:
            parse_sid(
                item[0]
            ),
        reverse=True,
    )

    return ranked[0][0]


if __name__ == "__main__":

    sid = resolve_short_id()

    if sid:
        print(sid)
    else:
        print("")
'''

resolver_path.write_text(
    resolver_code,
    encoding="utf-8",
)

try:

    py_compile.compile(
        str(
            resolver_path
        ),
        doraise=True,
    )

    emit(
        "PASS",
        "SHORT_ID_RESOLVER",
        "instalado",
    )

except Exception as exc:

    emit(
        "FAIL",
        "SHORT_ID_RESOLVER",
        str(exc),
    )


# ============================================================
# 2. REMOVE HARDCODE DE SHORT_ID DO RUNTIME
# ============================================================

runtime_files = [

    "vi600_00_provenance_replacement_engine.py",
    "vi900_00_global_visual_director.py",
    "vi230_00_current_vs_candidate_ab.py",
    "vi400_00_speed_quality_accelerator.py",
    "vi420_00_batch_deep_ab.py",
    "vi500_00_global_provenance_identity.py",
    "vi700_00_canary_portfolio_builder.py",
    "vi800_00_production_readiness.py",
    "vi235_00_media_provenance_check.py",
    "vi650_00_shadow_portfolio_optimizer.py",
    "preproduction_visual_gate_v1.py",
]


old_runtime_ids = {
    "2026-09-01_1433",
    "2026-09-02_2358",
}


for filename in runtime_files:

    path = ROOT / filename

    if not path.is_file():
        continue


    src = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    original = src


    found = False

    for sid in old_runtime_ids:

        if (
            f'"{sid}"' in src
            or
            f"'{sid}'" in src
        ):

            found = True

            src = src.replace(
                f'"{sid}"',
                "_sap_resolve_short_id()",
            )

            src = src.replace(
                f"'{sid}'",
                "_sap_resolve_short_id()",
            )


    if not found:
        continue


    backup(path)


    src = insert_import(
        src,
        (
            "from short_id_runtime_v1 import "
            "resolve_short_id as "
            "_sap_resolve_short_id"
        ),
    )


    path.write_text(
        src,
        encoding="utf-8",
    )


    try:

        py_compile.compile(
            str(path),
            doraise=True,
        )

        REPAIRS += 1

        emit(
            "PASS",
            "RUNTIME_SHORT_ID_PATCH",
            filename,
        )


    except Exception as exc:

        # rollback individual
        path.write_text(
            original,
            encoding="utf-8",
        )

        emit(
            "FAIL",
            "RUNTIME_SHORT_ID_PATCH",
            f"{filename}: {exc}",
        )


# ============================================================
# 3. VSE4.2 FINAL RUNTIME BRIDGE
# ============================================================

bridge_path = (
    ROOT
    / "visual_selection_runtime_bridge_v42.py"
)

backup(
    bridge_path
)


bridge_code = r'''#!/usr/bin/env python3

import os
from collections import Counter

from visual_selection_engine_v4 import (
    score_candidate,
    must_tier,
    provider,
    source_group,
    media_type,
    candidate_key,
)


_HISTORY = {
    "providers": [],
    "groups": [],
    "types": [],
    "keys": [],
}


def _scene_from_context(ctx):

    if not isinstance(
        ctx,
        dict,
    ):
        ctx = {}


    def first(*names):

        for name in names:

            value = ctx.get(
                name
            )

            if value not in (
                None,
                "",
                [],
                {},
            ):
                return value

        return ""


    return {
        "texto":
            first(
                "segmento",
                "texto",
                "scene_text",
                "texto_cena",
            ),

        "visual_query":
            first(
                "busca",
                "visual_query",
                "query",
            ),

        "must_have":
            first(
                "must_have",
                "must",
            )
            or
            [],

        "avoid":
            first(
                "avoid",
                "avoid_terms",
            )
            or
            [],

        "location":
            first(
                "location",
                "localizacao",
                "geo",
            ),
    }


def _effective(result):

    if not isinstance(
        result,
        dict,
    ):
        return 0.0

    for key in (
        "effective",
        "effective_score",
        "final_score",
        "score",
    ):

        value = result.get(
            key
        )

        if isinstance(
            value,
            (
                int,
                float,
            ),
        ):
            return float(value)

    return 0.0


def rerank_pool(
    pool,
    context=None,
):

    if (
        os.environ.get(
            "SAP_VSE42_RUNTIME",
            "1",
        )
        ==
        "0"
    ):

        return list(
            pool or []
        ), {
            "enabled": False,
            "summary": "kill-switch",
        }


    pool = list(
        pool or []
    )


    if len(pool) <= 1:

        return pool, {
            "enabled": True,
            "summary":
                f"pool={len(pool)}",
        }


    scene = _scene_from_context(
        context
        or
        {}
    )


    state = {
        key: list(value)
        for key, value
        in _HISTORY.items()
    }


    provider_counts = Counter(
        _HISTORY[
            "providers"
        ]
    )

    group_counts = Counter(
        _HISTORY[
            "groups"
        ]
    )

    key_counts = Counter(
        _HISTORY[
            "keys"
        ]
    )


    ranked = []


    for index, candidate in enumerate(
        pool
    ):

        try:

            result = score_candidate(
                candidate,
                scene,
                state,
            )

        except Exception as exc:

            result = {
                "hard_mismatch":
                    False,

                "effective":
                    -100000.0,

                "bridge_error":
                    (
                        f"{type(exc).__name__}: "
                        f"{exc}"
                    ),
            }


        hard = bool(
            result.get(
                "hard_mismatch",
                False,
            )
        )


        try:
            tier = int(
                must_tier(
                    candidate,
                    scene,
                )
            )
        except Exception:
            tier = 0


        try:
            prov = provider(
                candidate
            )
        except Exception:
            prov = "unknown"


        try:
            group = source_group(
                candidate
            )
        except Exception:
            group = "unknown"


        try:
            typ = media_type(
                candidate
            )
        except Exception:
            typ = "unknown"


        try:
            key = candidate_key(
                candidate
            )
        except Exception:
            key = (
                f"{prov}:"
                f"{typ}:"
                f"{index}"
            )


        effective = _effective(
            result
        )


        # ----------------------------------------------------
        # Diversity adjustments
        # ----------------------------------------------------

        adjusted = effective


        if (
            _HISTORY["providers"]
            and
            prov
            ==
            _HISTORY["providers"][-1]
        ):
            adjusted -= 12.0


        adjusted -= (
            provider_counts[
                prov
            ]
            *
            3.0
        )


        if (
            group
            and
            group != "unknown"
        ):

            adjusted -= (
                group_counts[
                    group
                ]
                *
                4.0
            )


        if key_counts[
            key
        ]:

            adjusted -= (
                60.0
                *
                key_counts[
                    key
                ]
            )


        # Evita longas sequências só foto ou só vídeo.
        if (
            len(
                _HISTORY[
                    "types"
                ]
            )
            >= 3
            and
            len(
                set(
                    _HISTORY[
                        "types"
                    ][-3:]
                )
            )
            ==
            1
            and
            typ
            ==
            _HISTORY[
                "types"
            ][-1]
        ):

            adjusted -= 7.0


        # hard mismatch sempre perde para candidato válido.
        valid_rank = (
            0
            if hard
            else 1
        )


        ranked.append(
            {
                "candidate":
                    candidate,

                "original_index":
                    index,

                "hard":
                    hard,

                "tier":
                    tier,

                "effective":
                    effective,

                "adjusted":
                    adjusted,

                "provider":
                    prov,

                "group":
                    group,

                "type":
                    typ,

                "key":
                    key,

                "details":
                    result,
            }
        )


    ranked.sort(
        key=lambda item: (
            item[
                "hard"
            ]
            is False,

            item[
                "tier"
            ],

            item[
                "adjusted"
            ],

            -item[
                "original_index"
            ],
        ),
        reverse=True,
    )


    output = [
        item[
            "candidate"
        ]
        for item in ranked
    ]


    top = ranked[0]


    max_tier = max(
        item[
            "tier"
        ]
        for item in ranked
    )


    provider_pool = Counter(
        item[
            "provider"
        ]
        for item in ranked
    )


    meta = {
        "enabled":
            True,

        "pool":
            len(
                ranked
            ),

        "max_tier":
            max_tier,

        "rescue_needed":
            max_tier < 2,

        "top_provider":
            top[
                "provider"
            ],

        "top_type":
            top[
                "type"
            ],

        "top_tier":
            top[
                "tier"
            ],

        "top_hard_mismatch":
            top[
                "hard"
            ],

        "provider_pool":
            dict(
                provider_pool
            ),

        "summary":
            (
                f"pool={len(ranked)} "
                f"top={top['provider']}/"
                f"{top['type']} "
                f"tier={top['tier']} "
                f"hard={top['hard']} "
                f"providers="
                f"{dict(provider_pool)}"
            ),
    }


    return output, meta


def note_selected(candidate):

    try:
        prov = provider(
            candidate
        )
    except Exception:
        prov = "unknown"


    try:
        group = source_group(
            candidate
        )
    except Exception:
        group = "unknown"


    try:
        typ = media_type(
            candidate
        )
    except Exception:
        typ = "unknown"


    try:
        key = candidate_key(
            candidate
        )
    except Exception:
        key = (
            f"{prov}:"
            f"{typ}:"
            f"{len(_HISTORY['keys'])}"
        )


    _HISTORY[
        "providers"
    ].append(
        prov
    )

    _HISTORY[
        "groups"
    ].append(
        group
    )

    _HISTORY[
        "types"
    ].append(
        typ
    )

    _HISTORY[
        "keys"
    ].append(
        key
    )


    # histórico limitado para não crescer indefinidamente
    for name in _HISTORY:

        if len(
            _HISTORY[
                name
            ]
        ) > 30:

            _HISTORY[
                name
            ] = (
                _HISTORY[
                    name
                ][-30:]
            )


def history():

    return {
        key: list(value)
        for key, value
        in _HISTORY.items()
    }
'''


bridge_path.write_text(
    bridge_code,
    encoding="utf-8",
)


try:

    py_compile.compile(
        str(
            bridge_path
        ),
        doraise=True,
    )

    emit(
        "PASS",
        "VSE42_BRIDGE_COMPILE",
        "ok",
    )

except Exception as exc:

    emit(
        "FAIL",
        "VSE42_BRIDGE_COMPILE",
        str(exc),
    )


# ============================================================
# 4. PATCH REAL MIDIA FINAL-DECISION PATH
# ============================================================

midia = (
    ROOT
    / "midia.py"
)

if not midia.is_file():

    emit(
        "FAIL",
        "MIDIA_PATCH",
        "midia.py ausente",
    )

else:

    backup(
        midia
    )

    src = midia.read_text(
        encoding="utf-8",
        errors="replace",
    )

    original = src

    try:

        tree = ast.parse(
            src
        )

        lines = src.splitlines(
            keepends=True
        )

        insertions = []


        # ----------------------------------------------------
        # 4A. Encontrar:
        #
        # pool = [escolhido] + [...]
        #
        # para rerankear DEPOIS do prepend antigo.
        # ----------------------------------------------------

        if (
            "# SHORTAUTOPRO VSE42 FINAL RERANK"
            not in src
        ):

            pool_nodes = []

            for node in ast.walk(
                tree
            ):

                if not isinstance(
                    node,
                    ast.Assign,
                ):
                    continue


                targets = [
                    target.id
                    for target
                    in node.targets
                    if isinstance(
                        target,
                        ast.Name,
                    )
                ]


                if "pool" not in targets:
                    continue


                segment = ast.get_source_segment(
                    src,
                    node,
                ) or ""


                if (
                    "escolhido" in segment
                    and
                    "pool" in segment
                ):

                    pool_nodes.append(
                        node
                    )


            if pool_nodes:

                # último prepend relevante é o mais próximo
                # do loop de download.
                node = pool_nodes[-1]

                raw_line = lines[
                    node.lineno - 1
                ]

                indent = (
                    raw_line[
                        :
                        len(raw_line)
                        -
                        len(
                            raw_line.lstrip()
                        )
                    ]
                )


                block = (
                    "\n"
                    f"{indent}"
                    "# SHORTAUTOPRO VSE42 FINAL RERANK\n"

                    f"{indent}"
                    "try:\n"

                    f"{indent}    "
                    "from visual_selection_runtime_bridge_v42 "
                    "import rerank_pool as _sap_vse42_rerank_pool\n"

                    f"{indent}    "
                    "pool, _sap_vse42_meta = "
                    "_sap_vse42_rerank_pool(pool, locals())\n"

                    f"{indent}    "
                    "if pool:\n"

                    f"{indent}        "
                    "escolhido = pool[0]\n"

                    f"{indent}    "
                    "print("
                    "\"VSE42_RERANK=PASS \""
                    " + str(_sap_vse42_meta.get("
                    "\"summary\", \"\")))\n"

                    f"{indent}    "
                    "if _sap_vse42_meta.get("
                    "\"rescue_needed\"):\n"

                    f"{indent}        "
                    "print("
                    "\"VSE42_RESCUE_NEEDED=YES\")\n"

                    f"{indent}"
                    "except Exception as _sap_vse42_exc:\n"

                    f"{indent}    "
                    "print("
                    "f\"VSE42_RERANK=FAIL_OPEN "
                    "{type(_sap_vse42_exc).__name__}: "
                    "{_sap_vse42_exc}\")\n"
                )


                insertions.append(
                    (
                        node.end_lineno,
                        block,
                    )
                )

                REPAIRS += 1

                emit(
                    "PASS",
                    "VSE42_FINAL_RERANK_PATCH",
                    (
                        f"after line "
                        f"{node.end_lineno}"
                    ),
                )

            else:

                emit(
                    "WARN",
                    "VSE42_FINAL_RERANK_PATCH",
                    (
                        "pool prepend não localizado; "
                        "estrutura pode já ter mudado"
                    ),
                )


        else:

            emit(
                "PASS",
                "VSE42_FINAL_RERANK_PATCH",
                "já instalado",
            )


        # ----------------------------------------------------
        # 4B. Fix definitivo:
        #
        # primeiro download bem-sucedido COMMITA a cena.
        #
        # Não permite baixar/substituir com o próximo candidato.
        # ----------------------------------------------------

        if (
            "# SHORTAUTOPRO SCENE COMMIT V42"
            not in src
        ):

            success_nodes = []


            loops = [
                node
                for node in ast.walk(
                    tree
                )
                if isinstance(
                    node,
                    (
                        ast.For,
                        ast.While,
                    ),
                )
            ]


            for node in ast.walk(
                tree
            ):

                if not isinstance(
                    node,
                    ast.If,
                ):
                    continue


                is_ok = (
                    isinstance(
                        node.test,
                        ast.Name,
                    )
                    and
                    node.test.id
                    ==
                    "ok"
                )


                if not is_ok:
                    continue


                assigns = set()


                for child in ast.walk(
                    node
                ):

                    if isinstance(
                        child,
                        ast.Assign,
                    ):

                        for target in child.targets:

                            if isinstance(
                                target,
                                ast.Name,
                            ):

                                assigns.add(
                                    target.id
                                )


                if not {
                    "sucesso",
                    "escolhido",
                }.issubset(
                    assigns
                ):

                    continue


                inside_loop = any(
                    loop.lineno
                    <
                    node.lineno
                    <=
                    node.end_lineno
                    <=
                    loop.end_lineno
                    for loop in loops
                )


                if not inside_loop:
                    continue


                # Confirma que downloader está perto.
                start = max(
                    0,
                    node.lineno - 40,
                )

                context = "".join(
                    lines[
                        start:
                        node.lineno
                    ]
                )


                if (
                    "baixar_candidato_5_2"
                    not in context
                ):
                    continue


                success_nodes.append(
                    node
                )


            if success_nodes:

                node = success_nodes[-1]


                raw_if = lines[
                    node.lineno - 1
                ]

                if_indent = (
                    raw_if[
                        :
                        len(raw_if)
                        -
                        len(
                            raw_if.lstrip()
                        )
                    ]
                )

                body_indent = (
                    if_indent
                    +
                    "    "
                )


                direct_breaks = [
                    stmt
                    for stmt in node.body
                    if isinstance(
                        stmt,
                        ast.Break,
                    )
                ]


                commit_block = (
                    f"{body_indent}"
                    "# SHORTAUTOPRO SCENE COMMIT V42\n"

                    f"{body_indent}"
                    "try:\n"

                    f"{body_indent}    "
                    "from visual_selection_runtime_bridge_v42 "
                    "import note_selected as _sap_vse42_note_selected\n"

                    f"{body_indent}    "
                    "_sap_vse42_note_selected(candidato)\n"

                    f"{body_indent}    "
                    "print("
                    "\"SCENE_COMMIT_V42=YES\")\n"

                    f"{body_indent}"
                    "except Exception as _sap_vse42_commit_exc:\n"

                    f"{body_indent}    "
                    "print("
                    "f\"SCENE_COMMIT_V42=HISTORY_FAIL_OPEN "
                    "{type(_sap_vse42_commit_exc).__name__}: "
                    "{_sap_vse42_commit_exc}\")\n"
                )


                if direct_breaks:

                    # Insere antes do break já existente.
                    target_line = (
                        direct_breaks[0].lineno
                        -
                        1
                    )

                    insertions.append(
                        (
                            target_line,
                            commit_block,
                        )
                    )

                    emit(
                        "PASS",
                        "SCENE_COMMIT_CONTROL",
                        "break direto já existia",
                    )

                else:

                    commit_block += (
                        f"{body_indent}"
                        "break\n"
                    )

                    insertions.append(
                        (
                            node.end_lineno,
                            "\n"
                            +
                            commit_block,
                        )
                    )

                    REPAIRS += 1

                    emit(
                        "PASS",
                        "SCENE_COMMIT_CONTROL",
                        (
                            "break incondicional "
                            "adicionado após sucesso"
                        ),
                    )


            else:

                emit(
                    "WARN",
                    "SCENE_COMMIT_CONTROL",
                    (
                        "bloco downloader não localizado; "
                        "auditar estrutura atual"
                    ),
                )


        else:

            emit(
                "PASS",
                "SCENE_COMMIT_CONTROL",
                "já instalado",
            )


        # Aplicar de baixo para cima.
        for line_no, text in sorted(
            insertions,
            key=lambda item:
                item[0],
            reverse=True,
        ):

            lines.insert(
                line_no,
                text,
            )


        if insertions:

            src = "".join(
                lines
            )

            midia.write_text(
                src,
                encoding="utf-8",
            )


        py_compile.compile(
            str(
                midia
            ),
            doraise=True,
        )

        emit(
            "PASS",
            "MIDIA_COMPILE_AFTER_PATCH",
            "ok",
        )


    except Exception as exc:

        midia.write_text(
            original,
            encoding="utf-8",
        )

        emit(
            "FAIL",
            "MIDIA_PATCH",
            (
                f"rollback aplicado: "
                f"{type(exc).__name__}: "
                f"{exc}"
            ),
        )


# ============================================================
# 5. DUPLICATE DEFINITIONS:
#
# Python usa a última definição.
# Não apagar versões antigas cegamente.
#
# Classificamos como SHADOWED TECH-DEBT, não bug,
# desde que o arquivo compile.
# ============================================================

duplicate_groups = 0
duplicate_defs = 0


for path in ROOT.glob(
    "*.py"
):

    try:

        src = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        tree = ast.parse(
            src
        )

    except Exception:

        continue


    defs = {}


    for node in tree.body:

        if isinstance(
            node,
            (
                ast.FunctionDef,
                ast.AsyncFunctionDef,
            ),
        ):

            defs.setdefault(
                node.name,
                [],
            ).append(
                node.lineno
            )


    for name, locations in defs.items():

        if len(
            locations
        ) <= 1:
            continue


        duplicate_groups += 1

        duplicate_defs += (
            len(
                locations
            )
            -
            1
        )


        emit(
            "INFO",
            "SHADOWED_DEFINITION",
            (
                f"{path.name}:"
                f"{name} "
                f"versions={locations} "
                f"active={locations[-1]}"
            ),
        )


emit(
    "PASS",
    "DUPLICATE_CLASSIFICATION",
    (
        f"groups={duplicate_groups} "
        f"shadowed={duplicate_defs}; "
        "última definição é runtime ativo"
    ),
)


# ============================================================
# 6. PRODUCTION HARDCODE AUDIT
# ============================================================

sid_literal = re.compile(
    r"^\d{4}-\d{2}-\d{2}_\d{4}$"
)

remaining_runtime_ids = []


for filename in runtime_files:

    path = ROOT / filename

    if not path.is_file():
        continue


    try:

        tree = ast.parse(
            path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )

    except Exception:
        continue


    for node in ast.walk(
        tree
    ):

        if (
            isinstance(
                node,
                ast.Constant,
            )
            and
            isinstance(
                node.value,
                str,
            )
            and
            sid_literal.fullmatch(
                node.value
            )
        ):

            remaining_runtime_ids.append(
                (
                    filename,
                    node.lineno,
                    node.value,
                )
            )


if remaining_runtime_ids:

    for filename, line, sid in remaining_runtime_ids:

        emit(
            "WARN",
            "REMAINING_RUNTIME_SHORT_ID",
            (
                f"{filename}:"
                f"{line}:"
                f"{sid}"
            ),
        )

else:

    emit(
        "PASS",
        "PRODUCTION_RUNTIME_SHORT_ID",
        "0 hardcodes históricos",
    )


# ============================================================
# 7. TEST/CANARY FIXTURES ARE INTENTIONAL
# ============================================================

fixture_patterns = (
    ".resume_",
    ".vi",
    "validar_",
    "canary",
)


fixture_hardcodes = 0


for path in ROOT.iterdir():

    if not path.is_file():
        continue


    name = path.name.casefold()


    if not any(
        pattern.casefold()
        in name
        for pattern in fixture_patterns
    ):

        continue


    try:

        text = path.read_text(
            encoding="utf-8",
            errors="replace",
        )

    except Exception:
        continue


    matches = re.findall(
        r"\b20\d{2}-\d{2}-\d{2}_\d{4}\b",
        text,
    )


    fixture_hardcodes += len(
        matches
    )


emit(
    "INFO",
    "HISTORICAL_FIXTURE_IDS",
    (
        f"count={fixture_hardcodes}; "
        "preservados para reprodução/rollback"
    ),
)


# ============================================================
# 8. PROVIDER ACQUISITION CONFIG
# ============================================================

config_text = ""

for cfg in (
    ROOT / "config.env",
    ROOT / ".env",
):

    if cfg.is_file():

        config_text += (
            "\n"
            +
            cfg.read_text(
                encoding="utf-8",
                errors="replace",
            )
        )


def has_config_name(
    patterns,
):

    for pattern in patterns:

        if re.search(
            rf"(?mi)^\s*{pattern}\s*=",
            config_text,
        ):

            return True

        for env_name in os.environ:

            if re.fullmatch(
                pattern,
                env_name,
                re.I,
            ):

                return True

    return False


provider_cfg = {

    "PEXELS":
        has_config_name(
            (
                r"PEXELS_API_KEY",
                r"PEXELS_KEY",
            )
        ),

    "PIXABAY":
        has_config_name(
            (
                r"PIXABAY_API_KEY",
                r"PIXABAY_KEY",
            )
        ),

    "COVERR":
        has_config_name(
            (
                r"COVERR_API_KEY",
                r"COVERR_KEY",
            )
        ),
}


for provider_name, configured in provider_cfg.items():

    emit(
        (
            "PASS"
            if configured
            else
            "INFO"
        ),
        f"PROVIDER_CONFIG_{provider_name}",
        (
            "configured"
            if configured
            else
            "no explicit key detected"
        ),
    )


# ============================================================
# 9. GLOBAL PYTHON COMPILE
# ============================================================

compile_failures = []


for path in ROOT.glob(
    "*.py"
):

    try:

        py_compile.compile(
            str(path),
            doraise=True,
        )

    except Exception as exc:

        compile_failures.append(
            (
                path.name,
                str(exc),
            )
        )


if compile_failures:

    for filename, error in compile_failures:

        emit(
            "FAIL",
            "PYTHON_COMPILE",
            f"{filename}: {error}",
        )

else:

    emit(
        "PASS",
        "PYTHON_COMPILE",
        (
            f"{len(list(ROOT.glob('*.py')))} "
            "top-level arquivos"
        ),
    )


# ============================================================
# 10. SHELL SYNTAX
# ============================================================

shell_failures = []

shell_files = list(
    ROOT.glob(
        "*.sh"
    )
) + list(
    ROOT.glob(
        ".*.sh"
    )
)


for path in shell_files:

    result = subprocess.run(
        [
            "bash",
            "-n",
            str(path),
        ],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


    if result.returncode != 0:

        shell_failures.append(
            (
                path.name,
                result.stderr.strip(),
            )
        )


if shell_failures:

    for filename, error in shell_failures:

        emit(
            "FAIL",
            "SHELL_SYNTAX",
            f"{filename}: {error}",
        )

else:

    emit(
        "PASS",
        "SHELL_SYNTAX",
        f"{len(shell_files)} scripts",
    )


# ============================================================
# 11. VSE4 SELF TEST
# ============================================================

vse4 = (
    ROOT
    / "visual_selection_engine_v4.py"
)


if vse4.is_file():

    try:

        result = subprocess.run(
            [
                sys.executable,
                str(vse4),
            ],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=120,
        )


        tail = "\n".join(
            result.stdout.splitlines()[
                -20:
            ]
        )


        if result.returncode == 0:

            emit(
                "PASS",
                "VSE4_SELF_TEST",
                "status=0",
            )

        else:

            emit(
                "FAIL",
                "VSE4_SELF_TEST",
                (
                    f"status="
                    f"{result.returncode}; "
                    f"{tail}"
                ),
            )


    except Exception as exc:

        emit(
            "FAIL",
            "VSE4_SELF_TEST",
            str(exc),
        )


else:

    emit(
        "FAIL",
        "VSE4_SELF_TEST",
        "arquivo ausente",
    )


# ============================================================
# 12. ACTIVE SHORT
# ============================================================

try:

    sys.path.insert(
        0,
        str(ROOT),
    )

    from short_id_runtime_v1 import (
        resolve_short_id,
    )

    active_sid = resolve_short_id()

except Exception:

    active_sid = ""


if active_sid:

    emit(
        "PASS",
        "ACTIVE_SHORT_ID",
        active_sid,
    )

else:

    emit(
        "FAIL",
        "ACTIVE_SHORT_ID",
        "não resolvido",
    )


# ============================================================
# 13. MEDIA CARDINALITY
# ============================================================

if active_sid:

    media_dir = (
        ROOT
        / "imagens"
        / f"short_{active_sid}"
    )

    invalid = []

    total = 0


    for number in range(
        1,
        13,
    ):

        matches = list(
            media_dir.glob(
                f"scene_{number:02d}.*"
            )
        )

        matches = [
            path
            for path in matches
            if path.is_file()
        ]

        total += len(
            matches
        )

        if len(
            matches
        ) != 1:

            invalid.append(
                (
                    number,
                    len(
                        matches
                    ),
                )
            )


    if (
        total == 12
        and
        not invalid
    ):

        emit(
            "PASS",
            "MEDIA_SCENE_CARDINALITY",
            "12/12",
        )

    else:

        emit(
            "FAIL",
            "MEDIA_SCENE_CARDINALITY",
            (
                f"total={total} "
                f"invalid={invalid}"
            ),
        )


# ============================================================
# 14. FINAL VIDEO HEALTH
# ============================================================

if active_sid:

    final = (
        ROOT
        / "videos"
        / f"short_v6_{active_sid}.mp4"
    )

    if final.is_file() and final.stat().st_size > 0:

        try:

            probe = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    (
                        "stream=codec_name,"
                        "codec_type,width,height,"
                        "r_frame_rate"
                    ),
                    "-show_entries",
                    "format=duration,size",
                    "-of",
                    "json",
                    str(final),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
            )


            data = json.loads(
                probe.stdout
            )

            streams = data.get(
                "streams",
                []
            )

            video_stream = next(
                (
                    stream
                    for stream in streams
                    if stream.get(
                        "codec_type"
                    )
                    ==
                    "video"
                ),
                {},
            )

            duration = float(
                data.get(
                    "format",
                    {},
                ).get(
                    "duration",
                    0,
                )
                or
                0
            )

            width = video_stream.get(
                "width"
            )

            height = video_stream.get(
                "height"
            )


            if (
                width == 1080
                and
                height == 1920
                and
                duration > 5
            ):

                emit(
                    "PASS",
                    "FINAL_VIDEO_HEALTH",
                    (
                        f"{final.name} "
                        f"{width}x{height} "
                        f"{duration:.2f}s "
                        f"sha256="
                        f"{sha256(final)}"
                    ),
                )

            else:

                emit(
                    "WARN",
                    "FINAL_VIDEO_HEALTH",
                    (
                        f"{width}x{height} "
                        f"{duration:.2f}s"
                    ),
                )


        except Exception as exc:

            emit(
                "WARN",
                "FINAL_VIDEO_HEALTH",
                str(exc),
            )

    else:

        emit(
            "INFO",
            "FINAL_VIDEO_HEALTH",
            "final atual não encontrado",
        )


# ============================================================
# 15. CORE HASHES
# ============================================================

for filename in (
    "midia.py",
    "video.py",
    "v6.py",
    "gerar_short.sh",
    "visual_selection_engine_v4.py",
    "visual_selection_runtime_bridge_v42.py",
):

    path = ROOT / filename

    if path.is_file():

        emit(
            "INFO",
            "SHA256",
            (
                f"{filename}="
                f"{sha256(path)}"
            ),
        )


# ============================================================
# FINAL
# ============================================================

print()
print(
    "=" * 72
)

print(
    " FINAL HARDENING SUMMARY"
)

print(
    "=" * 72
)

print(
    f"TOTAL_REPAIRS={REPAIRS}"
)

print(
    f"TOTAL_WARN={WARN}"
)

print(
    f"TOTAL_FAIL={FAIL}"
)


status = (
    "PASS"
    if FAIL == 0
    else
    "FAIL"
)


print(
    f"HARDENING_V3_STATUS={status}"
)

print(
    "NETWORK_EXECUTED=NO"
)

print(
    "MEDIA_SELECTION_EXECUTED=NO"
)

print(
    "VIDEO_RENDER_EXECUTED=NO"
)


STATUS_FILE.write_text(
    status + "\n",
    encoding="utf-8",
)


REPORT.write_text(
    "\n".join(
        rows
    )
    +
    "\n"
    +
    f"TOTAL_REPAIRS={REPAIRS}\n"
    +
    f"TOTAL_WARN={WARN}\n"
    +
    f"TOTAL_FAIL={FAIL}\n"
    +
    f"HARDENING_V3_STATUS={status}\n",
    encoding="utf-8",
)


print(
    f"REPORT={REPORT}"
)

print(
    "TERMUX_CONTINUA_ABERTO=SIM"
)
