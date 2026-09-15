#!/usr/bin/env python3

from pathlib import Path
import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import time


ROOT = Path.home() / "ShortAutoPro"

MIDIA = ROOT / "midia.py"
VSE = ROOT / "visual_selection_engine_v4.py"
UNIFIED = ROOT / "visual_engine_unified.py"

STAMP = time.strftime("%Y%m%d_%H%M%S")

BACKUP = (
    ROOT
    / "backups"
    / f"visual_consolidation_v5_{STAMP}"
)

BACKUP.mkdir(
    parents=True,
    exist_ok=True,
)


def sha256(path):

    h = hashlib.sha256()

    with path.open("rb") as f:

        for chunk in iter(
            lambda: f.read(1024 * 1024),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()


def backup(path):

    if not path.exists():
        return

    target = (
        BACKUP
        / path.name
    )

    shutil.copy2(
        path,
        target,
    )

    print(
        f"BACKUP={path.name}"
    )


def compile_file(path):

    result = subprocess.run(
        [
            "python",
            "-m",
            "py_compile",
            str(path),
        ],
        cwd=ROOT,
    )

    return result.returncode == 0


def replace_top_function(src, name, replacement):
    """
    Normaliza uma função top-level.

    - aceita 1 ou várias definições existentes;
    - remove todas as versões antigas;
    - instala exatamente uma implementação;
    - preserva o restante do arquivo;
    - suporta decorators;
    - valida o resultado com AST.
    """

    import ast
    import textwrap

    if not isinstance(src, str):
        raise TypeError(
            "src must be str"
        )

    if not isinstance(name, str) or not name.strip():
        raise ValueError(
            "name inválido"
        )

    if not isinstance(replacement, str):
        raise TypeError(
            "replacement must be str"
        )

    name = name.strip()

    replacement = (
        textwrap.dedent(
            replacement
        )
        .strip("\n")
        + "\n\n"
    )

    # Valida implementação nova antes de tocar no source.
    replacement_tree = ast.parse(
        replacement
    )

    replacement_defs = [
        n
        for n in replacement_tree.body
        if (
            isinstance(
                n,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
            and n.name == name
        )
    ]

    if len(replacement_defs) != 1:
        raise ValueError(
            f"replacement de {name!r} "
            f"deve possuir exatamente uma função; "
            f"encontradas={len(replacement_defs)}"
        )

    tree = ast.parse(
        src
    )

    matches = [
        n
        for n in tree.body
        if (
            isinstance(
                n,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
            and n.name == name
        )
    ]

    # Se não existir, adiciona ao final.
    if not matches:

        result = (
            src.rstrip()
            + "\n\n"
            + replacement
        )

        ast.parse(
            result
        )

        return result


    lines = src.splitlines(
        keepends=True
    )

    spans = []

    for fn in matches:

        start_candidates = [
            fn.lineno
        ]

        for decorator in getattr(
            fn,
            "decorator_list",
            [],
        ):
            start_candidates.append(
                decorator.lineno
            )

        start_index = (
            min(start_candidates)
            - 1
        )

        end_index = fn.end_lineno

        spans.append(
            (
                start_index,
                end_index,
            )
        )


    spans.sort()


    output = []

    cursor = 0
    inserted = False


    for start_index, end_index in spans:

        if start_index < cursor:
            raise RuntimeError(
                f"overlapping function spans "
                f"for {name}"
            )

        output.append(
            "".join(
                lines[
                    cursor:start_index
                ]
            )
        )

        if not inserted:

            output.append(
                replacement
            )

            inserted = True

        cursor = end_index


    output.append(
        "".join(
            lines[cursor:]
        )
    )


    result = "".join(
        output
    )


    # Validação estrutural pós-substituição.
    result_tree = ast.parse(
        result
    )

    remaining = [
        n
        for n in result_tree.body
        if (
            isinstance(
                n,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                ),
            )
            and n.name == name
        )
    ]


    if len(remaining) != 1:

        raise RuntimeError(
            f"normalização falhou para {name}: "
            f"remaining={len(remaining)}"
        )


    return result





print("=" * 70)
print("SHORTAUTOPRO VISUAL CONSOLIDATION V5")
print("=" * 70)

for path in (
    MIDIA,
    VSE,
    ROOT / "media_diversity_guard_v1.py",
    ROOT / "gerar_short.sh",
    ROOT / "video.py",
    ROOT / "v6.py",
):
    backup(path)


if not MIDIA.exists():
    raise RuntimeError(
        "midia.py ausente"
    )

if not VSE.exists():
    raise RuntimeError(
        "visual_selection_engine_v4.py ausente"
    )


# ============================================================
# 1. CANDIDATE_TEXT DEFINITIVO
# ============================================================

src = VSE.read_text(
    encoding="utf-8",
)


candidate_text_impl = r'''
def candidate_text(candidate):
    """
    Extrai texto semântico de:
    - strings diretas
    - cenas estruturadas
    - candidatos de mídia
    - metadata/provenance
    - listas e tuples

    Função read-only.
    """

    if candidate is None:
        return ""


    parts = []


    def add(value):

        if value is None:
            return


        if isinstance(
            value,
            str,
        ):

            value = value.strip()

            if value:
                parts.append(value)

            return


        if isinstance(
            value,
            (
                int,
                float,
                bool,
            ),
        ):

            parts.append(
                str(value)
            )

            return


        if isinstance(
            value,
            (
                list,
                tuple,
                set,
            ),
        ):

            for item in value:
                add(item)

            return


        if isinstance(
            value,
            dict,
        ):

            preferred = (
                "texto",
                "text",
                "scene_text",
                "narration",
                "narração",
                "visual_query",
                "query",
                "search_query",
                "must_have",
                "avoid",
                "location",
                "local",
                "title",
                "name",
                "description",
                "caption",
                "alt",
                "alt_text",
                "tags",
                "keywords",
                "terms",
                "subject",
                "topic",
                "category",
                "provider",
                "source_group",
                "media_type",
                "type",
                "filename",
            )

            used = False

            for key in preferred:

                if key in value:

                    add(
                        value.get(key)
                    )

                    used = True


            if not used:

                for child in value.values():
                    add(child)

            return


        try:

            add(
                str(value)
            )

        except Exception:

            return


    if isinstance(
        candidate,
        (
            str,
            list,
            tuple,
            set,
        ),
    ):

        add(candidate)


    elif isinstance(
        candidate,
        dict,
    ):

        add(candidate)


        for nested_name in (
            "metadata",
            "meta",
            "source_metadata",
            "provenance",
        ):

            nested = candidate.get(
                nested_name
            )

            if nested is not None:
                add(nested)


    else:

        fields = (
            "texto",
            "text",
            "scene_text",
            "narration",
            "visual_query",
            "query",
            "search_query",
            "must_have",
            "avoid",
            "location",
            "title",
            "name",
            "description",
            "caption",
            "alt",
            "alt_text",
            "tags",
            "keywords",
            "terms",
            "subject",
            "topic",
            "category",
            "provider",
            "source_group",
            "media_type",
            "type",
            "filename",
        )

        for field in fields:

            try:

                add(
                    getattr(
                        candidate,
                        field,
                        None,
                    )
                )

            except Exception:

                pass


    clean = []
    seen = set()

    for part in parts:

        text = str(part).strip()

        if not text:
            continue

        key = text.casefold()

        if key in seen:
            continue

        seen.add(key)
        clean.append(text)


    return " ".join(
        clean
    ).casefold()
'''


src = replace_top_function(
    src,
    "candidate_text",
    candidate_text_impl,
)


VSE.write_text(
    src,
    encoding="utf-8",
)

print(
    "CANDIDATE_TEXT_V5=INSTALLED"
)


if not compile_file(VSE):

    raise RuntimeError(
        "VSE compile falhou após candidate_text"
    )


# ============================================================
# 2. SAFETY LAYER
# ============================================================

src = VSE.read_text(
    encoding="utf-8",
)

MARKER = (
    "# SHORTAUTOPRO "
    "SEMANTIC SAFETY V5"
)


if MARKER not in src:

    anchor = "def self_test("

    if anchor not in src:

        raise RuntimeError(
            "self_test não encontrado"
        )


    safety = r'''
# SHORTAUTOPRO SEMANTIC SAFETY V5

_VSE5_SCORE_CORE = score_candidate


_VSE5_GEO_PARENT = {

    "sao_paulo": "brazil",
    "rio_de_janeiro": "brazil",
    "brasilia": "brazil",

    "new_york": "usa",
    "los_angeles": "usa",
    "washington_dc": "usa",

    "london": "united_kingdom",

    "paris": "france",

    "rome": "italy",

    "tokyo": "japan",
}


_VSE5_COUNTRIES = {

    "brazil",
    "usa",
    "united_kingdom",
    "france",
    "italy",
    "germany",
    "spain",
    "portugal",
    "japan",
    "china",
    "russia",
    "ukraine",
    "mexico",
    "argentina",
    "canada",
    "australia",
    "india",
    "south_korea",
    "egypt",
}


_VSE5_DOCUMENTARY = {

    "police",
    "investigation",
    "crime_scene",
    "evidence",
    "forensics",
    "court",
    "law",
    "prison",
    "news",
    "archive",
    "military",
    "war",
    "laboratory",
    "hospital",
    "space",
    "rocket",
}


def _vse5_geo_roots(groups):

    roots = set()

    for group in groups:

        if group in _VSE5_COUNTRIES:

            roots.add(group)

            continue


        parent = _VSE5_GEO_PARENT.get(
            group
        )

        if parent:
            roots.add(parent)


    return roots


def _vse5_geo_conflict(
    scene_groups,
    candidate_groups,
):

    if (
        not scene_groups
        or
        not candidate_groups
    ):

        return False


    sr = _vse5_geo_roots(
        scene_groups
    )

    cr = _vse5_geo_roots(
        candidate_groups
    )


    if (
        sr
        and
        cr
        and
        sr.isdisjoint(cr)
    ):

        return True


    scene_specific = {
        x
        for x in scene_groups
        if x in _VSE5_GEO_PARENT
    }

    candidate_specific = {
        x
        for x in candidate_groups
        if x in _VSE5_GEO_PARENT
    }


    if (
        scene_specific
        and
        candidate_specific
    ):

        scene_parents = {
            _VSE5_GEO_PARENT[x]
            for x in scene_specific
        }

        candidate_parents = {
            _VSE5_GEO_PARENT[x]
            for x in candidate_specific
        }

        if scene_parents.isdisjoint(
            candidate_parents
        ):
            return True


    return False


def score_candidate(
    candidate,
    scene,
    state=None,
    *args,
    **kwargs
):

    result = _VSE5_SCORE_CORE(
        candidate,
        scene,
        state,
        *args,
        **kwargs
    )


    if not isinstance(
        result,
        dict,
    ):
        return result


    scene_text = candidate_text(
        scene
    )

    media_text = candidate_text(
        candidate
    )


    scene_geo = set(
        geo_hits(
            scene_text
        )
    )

    media_geo = set(
        geo_hits(
            media_text
        )
    )


    scene_tokens = set(
        tokens(
            scene_text
        )
    )

    media_tokens = set(
        tokens(
            media_text
        )
    )


    scene_concepts = set(
        concept_hits(
            scene_text
        )
    )


    reasons = list(
        result.get(
            "safety_reasons",
            [],
        )
        or
        []
    )


    hard = bool(
        result.get(
            "hard_mismatch",
            False,
        )
    )


    penalty = 0.0


    # --------------------------------------------------------
    # Geografia incompatível.
    # --------------------------------------------------------

    if _vse5_geo_conflict(
        scene_geo,
        media_geo,
    ):

        hard = True

        reasons.append(
            "GEO_CONTRADICTION"
        )


    # --------------------------------------------------------
    # Medicamento sem contexto médico.
    # --------------------------------------------------------

    medicine = {
        norm(x)
        for x in MEDICINE_TERMS
    }

    medicine_hits = (
        media_tokens
        &
        medicine
    )

    scene_medicine = (
        scene_tokens
        &
        medicine
    )


    if (
        medicine_hits
        and
        not scene_medicine
        and
        (
            scene_concepts
            &
            _VSE5_DOCUMENTARY
        )
    ):

        hard = True

        reasons.append(
            "FALSE_MEDICAL_ASSOCIATION"
        )


    # --------------------------------------------------------
    # Stock lifestyle genérico.
    # Soft penalty, não bloqueio absoluto.
    # --------------------------------------------------------

    lifestyle = {
        norm(x)
        for x in GENERIC_LIFESTYLE
    }

    lifestyle_hits = (
        media_tokens
        &
        lifestyle
    )


    if (
        lifestyle_hits
        and
        (
            scene_concepts
            &
            _VSE5_DOCUMENTARY
        )
    ):

        penalty += (
            85.0
            +
            min(
                45.0,
                12.0
                *
                len(
                    lifestyle_hits
                ),
            )
        )

        reasons.append(
            "GENERIC_LIFESTYLE"
        )


    result[
        "hard_mismatch"
    ] = hard


    result[
        "safety_reasons"
    ] = sorted(
        set(reasons)
    )


    current_effective = result.get(
        "effective",
        result.get(
            "score",
            0.0,
        ),
    )


    try:
        current_effective = float(
            current_effective
        )

    except Exception:
        current_effective = 0.0


    current_effective -= penalty


    if hard:

        current_effective -= 10000.0


    result[
        "effective"
    ] = current_effective


    result[
        "safety_penalty"
    ] = penalty


    return result


'''

    src = src.replace(
        anchor,
        safety
        +
        "\n\n"
        +
        anchor,
        1,
    )


    VSE.write_text(
        src,
        encoding="utf-8",
    )


    print(
        "SEMANTIC_SAFETY_V5=INSTALLED"
    )

else:

    print(
        "SEMANTIC_SAFETY_V5=ALREADY_PRESENT"
    )


if not compile_file(VSE):

    raise RuntimeError(
        "VSE compile falhou após safety"
    )


# ============================================================
# 3. VSE SELF TEST - BLOQUEIA INTEGRAÇÃO SE FALHAR
# ============================================================

print()
print("=" * 70)
print("VSE SELF TEST")
print("=" * 70)


test = subprocess.run(
    [
        "python",
        str(VSE),
    ],
    cwd=ROOT,
    text=True,
    capture_output=True,
)


print(
    test.stdout
)

if test.stderr:
    print(
        test.stderr
    )


if test.returncode != 0:

    print(
        "VSE_SELF_TEST=FAIL"
    )

    raise RuntimeError(
        "VSE não certificado; "
        "midia.py permanece sem integração V5"
    )


print(
    "VSE_SELF_TEST=PASS"
)


# ============================================================
# 4. SINGLE VISUAL FACADE
# ============================================================

unified_source = r'''#!/usr/bin/env python3

"""
ShortAutoPro Visual Engine Unified V5.

Única fachada entre midia.py e o motor visual.

Responsabilidades:
- normalizar contexto da cena
- reranquear pool
- bloquear mismatch forte
- diversidade entre cenas
- persistir commits
- fail-open

Não baixa mídia.
Não renderiza vídeo.
"""

from pathlib import Path
import json
import os
import tempfile


ROOT = (
    Path.home()
    / "ShortAutoPro"
)


import visual_selection_engine_v4 as vse


VERSION = "5.0"


def _sid(ctx=None):

    if isinstance(
        ctx,
        dict,
    ):

        for key in (
            "SHORT_ID",
            "short_id",
        ):

            value = ctx.get(
                key
            )

            if value:
                return str(value)


    return os.getenv(
        "SHORT_ID",
        "default",
    )


def _state_path(sid):

    return (
        ROOT
        / "temp"
        / f"visual_unified_state_{sid}.json"
    )


def _empty_state():

    return {
        "providers": [],
        "groups": [],
        "types": [],
        "keys": [],
    }


def _load_state(sid):

    path = _state_path(
        sid
    )

    if not path.is_file():
        return _empty_state()


    try:

        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )

    except Exception:

        return _empty_state()


    state = _empty_state()

    for key in state:

        value = data.get(
            key,
            []
        )

        if isinstance(
            value,
            list,
        ):
            state[key] = value[-24:]


    return state


def _save_state(
    sid,
    state,
):

    path = _state_path(
        sid
    )

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    payload = {
        key:
            list(
                state.get(
                    key,
                    [],
                )
            )[-24:]
        for key in (
            "providers",
            "groups",
            "types",
            "keys",
        )
    }


    fd, tmp_name = tempfile.mkstemp(
        prefix=path.name + ".",
        suffix=".tmp",
        dir=str(path.parent),
    )


    try:

        with os.fdopen(
            fd,
            "w",
            encoding="utf-8",
        ) as f:

            json.dump(
                payload,
                f,
                ensure_ascii=False,
                indent=2,
            )


        os.replace(
            tmp_name,
            path,
        )


    finally:

        try:

            if os.path.exists(
                tmp_name
            ):
                os.unlink(
                    tmp_name
                )

        except Exception:

            pass


def _context_value(
    ctx,
    names,
):

    if not isinstance(
        ctx,
        dict,
    ):
        return None


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


    return None


def scene_from_runtime(ctx):

    pieces = []


    candidates = (

        (
            "segmento",
            "scene",
            "cena",
        ),

        (
            "texto",
            "text",
            "narracao",
            "narration",
        ),

        (
            "visual_query",
            "busca",
            "query",
        ),

        (
            "must_have",
            "must",
        ),

        (
            "location",
            "local",
            "geo",
        ),

    )


    for group in candidates:

        value = _context_value(
            ctx,
            group,
        )

        if value is not None:
            pieces.append(
                value
            )


    return {
        "texto":
            pieces,
    }


def _score(
    candidate,
    scene,
    state,
):

    try:

        result = vse.score_candidate(
            candidate,
            scene,
            state,
        )


        if not isinstance(
            result,
            dict,
        ):
            result = {}


    except Exception as exc:

        return {
            "hard_mismatch":
                False,

            "effective":
                vse.base_score(
                    candidate
                ),

            "must":
                vse.must_tier(
                    candidate,
                    scene,
                ),

            "error":
                (
                    type(exc).__name__
                    +
                    ": "
                    +
                    str(exc)
                ),
        }


    if "must" not in result:

        result[
            "must"
        ] = vse.must_tier(
            candidate,
            scene,
        )


    return result


def rerank_pool_runtime(
    pool,
    ctx=None,
):

    if os.getenv(
        "SAP_VISUAL_UNIFIED",
        "1",
    ) != "1":

        return pool


    if not isinstance(
        pool,
        list,
    ):

        try:
            pool = list(pool)
        except Exception:
            return pool


    if len(pool) <= 1:
        return pool


    scene = scene_from_runtime(
        ctx or {}
    )


    sid = _sid(
        ctx
    )


    state = _load_state(
        sid
    )


    ranked = []


    for index, candidate in enumerate(
        pool
    ):

        result = _score(
            candidate,
            scene,
            state,
        )


        hard = bool(
            result.get(
                "hard_mismatch",
                False,
            )
        )


        must = result.get(
            "must",
            0,
        )


        try:
            must = int(
                float(must)
            )
        except Exception:
            must = 0


        effective = result.get(
            "effective",
            0.0,
        )


        try:
            effective = float(
                effective
            )
        except Exception:
            effective = 0.0


        ranked.append(
            (
                hard,
                -must,
                -effective,
                index,
                candidate,
                result,
            )
        )


    # Se todos forem hard mismatch,
    # mantém o comportamento anterior.
    if all(
        item[0]
        for item in ranked
    ):

        print(
            "VISUAL_UNIFIED="
            "ALL_HARD_FAIL_OPEN"
        )

        return pool


    ranked.sort(
        key=lambda item:
            (
                item[0],
                item[1],
                item[2],
                item[3],
            )
    )


    result_pool = [
        item[4]
        for item in ranked
    ]


    winner = ranked[0]

    winner_result = winner[5]


    print(
        "VISUAL_UNIFIED_V5=ACTIVE"
    )

    print(
        "VISUAL_UNIFIED_POOL="
        f"{len(pool)}"
    )

    print(
        "VISUAL_UNIFIED_WINNER="
        f"{vse.provider(winner[4])}/"
        f"{vse.media_type(winner[4])}"
    )

    print(
        "VISUAL_UNIFIED_MUST="
        f"{winner_result.get('must', 0)}"
    )

    print(
        "VISUAL_UNIFIED_EFFECTIVE="
        f"{winner_result.get('effective', 0)}"
    )

    print(
        "VISUAL_UNIFIED_HARD="
        f"{winner_result.get('hard_mismatch', False)}"
    )

    reasons = winner_result.get(
        "safety_reasons",
        [],
    )

    if reasons:

        print(
            "VISUAL_UNIFIED_REASONS="
            +
            ",".join(
                map(
                    str,
                    reasons,
                )
            )
        )


    return result_pool


def note_commit_runtime(
    candidate,
    ctx=None,
):

    sid = _sid(
        ctx
    )


    state = _load_state(
        sid
    )


    values = {

        "providers":
            vse.provider(
                candidate
            ),

        "groups":
            vse.source_group(
                candidate
            ),

        "types":
            vse.media_type(
                candidate
            ),

        "keys":
            vse.candidate_key(
                candidate
            ),
    }


    for bucket, value in values.items():

        if value in (
            None,
            "",
            "unknown",
        ):
            continue

        state[
            bucket
        ].append(
            value
        )

        state[
            bucket
        ] = state[
            bucket
        ][-24:]


    _save_state(
        sid,
        state,
    )


    print(
        "VISUAL_UNIFIED_COMMIT=PASS"
    )


def reset_state(
    sid,
):

    path = _state_path(
        sid
    )

    try:

        path.unlink()

    except FileNotFoundError:

        pass


if __name__ == "__main__":

    print(
        "VISUAL_ENGINE_UNIFIED_V5=PASS"
    )

    print(
        f"VERSION={VERSION}"
    )
'''


UNIFIED.write_text(
    unified_source,
    encoding="utf-8",
)


if not compile_file(
    UNIFIED
):

    raise RuntimeError(
        "visual_engine_unified.py compile FAIL"
    )


print(
    "VISUAL_ENGINE_UNIFIED=CREATED"
)


# ============================================================
# 5. SYNTHETIC UNIFIED TEST
# ============================================================

synthetic = subprocess.run(
    [
        "python",
        "-c",
        r'''
import visual_engine_unified as u

wrong = {
    "provider": "Pixabay",
    "tipo": "foto",
    "title":
        "Empire State Building New York",
    "must": "2/2",
    "score": 220,
    "width": 1920,
    "height": 1080,
}

correct = {
    "provider": "Wikimedia",
    "tipo": "foto",
    "title":
        "Apartment building Sao Paulo Brazil",
    "must": "1/2",
    "score": 120,
    "width": 1920,
    "height": 1080,
}

ctx = {
    "SHORT_ID": "SYNTHETIC_V5",
    "texto":
        "Investigação em apartamento "
        "na cidade de São Paulo",
}

pool = u.rerank_pool_runtime(
    [
        wrong,
        correct,
    ],
    ctx,
)

winner = pool[0]

print(
    "SYNTHETIC_WINNER="
    +
    winner["title"]
)

assert (
    "Sao Paulo"
    in winner["title"]
)

print(
    "UNIFIED_SYNTHETIC=PASS"
)
''',
    ],
    cwd=ROOT,
    text=True,
    capture_output=True,
)


print(
    synthetic.stdout
)

if synthetic.stderr:
    print(
        synthetic.stderr
    )


if synthetic.returncode != 0:

    raise RuntimeError(
        "Unified synthetic test falhou"
    )


# ============================================================
# 6. PATCH MIDIA ACTIVE PATH
# ============================================================

midia_original = MIDIA.read_text(
    encoding="utf-8",
)

midia_src = midia_original


RERANK_MARKER = (
    "# SHORTAUTOPRO "
    "VISUAL UNIFIED V5 RERANK"
)

COMMIT_MARKER = (
    "# SHORTAUTOPRO "
    "VISUAL UNIFIED V5 COMMIT"
)


if RERANK_MARKER not in midia_src:

    anchor_start = midia_src.find(
        "if escolhido:"
    )

    if anchor_start < 0:

        raise RuntimeError(
            "if escolhido: não encontrado"
        )


    pool_start = midia_src.find(
        "pool = ordenar_failover_5_2(",
        anchor_start,
    )

    if pool_start < 0:

        raise RuntimeError(
            "ordenar_failover_5_2 "
            "ativo não encontrado"
        )


    line_start = (
        midia_src.rfind(
            "\n",
            0,
            pool_start,
        )
        +
        1
    )


    indentation = (
        midia_src[
            line_start:pool_start
        ]
    )


    # Detecta fim da chamada balanceando parênteses.
    pos = pool_start
    depth = 0
    seen_open = False
    quote = None
    escaped = False


    while pos < len(
        midia_src
    ):

        ch = midia_src[
            pos
        ]


        if quote is not None:

            if escaped:
                escaped = False

            elif ch == "\\":
                escaped = True

            elif ch == quote:
                quote = None


        else:

            if ch in (
                "'",
                '"',
            ):
                quote = ch

            elif ch == "(":
                depth += 1
                seen_open = True

            elif ch == ")":
                depth -= 1

                if (
                    seen_open
                    and
                    depth == 0
                ):

                    end = pos + 1

                    while (
                        end
                        <
                        len(
                            midia_src
                        )
                        and
                        midia_src[
                            end
                        ]
                        in " \t"
                    ):
                        end += 1

                    if (
                        end
                        <
                        len(
                            midia_src
                        )
                        and
                        midia_src[
                            end
                        ]
                        == "\n"
                    ):
                        end += 1

                    break

        pos += 1

    else:

        raise RuntimeError(
            "fim da chamada "
            "ordenar_failover_5_2 "
            "não encontrado"
        )


    rerank_patch = (
        indentation
        +
        "# SHORTAUTOPRO "
        "VISUAL UNIFIED V5 RERANK\n"
        +
        indentation
        +
        "try:\n"
        +
        indentation
        +
        "    from visual_engine_unified "
        "import rerank_pool_runtime "
        "as _sap_visual_rerank\n"
        +
        indentation
        +
        "    pool = _sap_visual_rerank("
        "pool, locals())\n"
        +
        indentation
        +
        "except Exception as "
        "_sap_visual_error:\n"
        +
        indentation
        +
        "    print("
        "f\"VISUAL_UNIFIED_RERANK="
        "FAIL_OPEN "
        "{type(_sap_visual_error).__name__}: "
        "{_sap_visual_error}\")\n"
    )


    midia_src = (
        midia_src[:end]
        +
        rerank_patch
        +
        midia_src[end:]
    )


    print(
        "MIDIA_RERANK_PATCH=INSTALLED"
    )

else:

    print(
        "MIDIA_RERANK_PATCH="
        "ALREADY_PRESENT"
    )


if COMMIT_MARKER not in midia_src:

    rerank_pos = midia_src.find(
        RERANK_MARKER
    )

    search_end = min(
        len(
            midia_src
        ),
        rerank_pos + 9000,
    )

    region = midia_src[
        rerank_pos:search_end
    ]


    loop_rel = region.find(
        "for candidato in pool:"
    )

    if loop_rel < 0:

        raise RuntimeError(
            "for candidato in pool "
            "não encontrado após rerank"
        )


    loop_abs = (
        rerank_pos
        +
        loop_rel
    )


    match = re.search(
        r"(?m)^([ \t]*)"
        r"escolhido\s*=\s*candidato"
        r"[ \t]*$",
        midia_src[
            loop_abs:search_end
        ],
    )


    if not match:

        raise RuntimeError(
            "escolhido = candidato "
            "não encontrado no success path"
        )


    assignment_start = (
        loop_abs
        +
        match.start()
    )

    assignment_end = (
        loop_abs
        +
        match.end()
    )


    line_end = midia_src.find(
        "\n",
        assignment_end,
    )

    if line_end < 0:
        line_end = assignment_end
    else:
        line_end += 1


    indent = match.group(
        1
    )


    commit_patch = (
        indent
        +
        "# SHORTAUTOPRO "
        "VISUAL UNIFIED V5 COMMIT\n"
        +
        indent
        +
        "try:\n"
        +
        indent
        +
        "    from visual_engine_unified "
        "import note_commit_runtime "
        "as _sap_visual_commit\n"
        +
        indent
        +
        "    _sap_visual_commit("
        "candidato, locals())\n"
        +
        indent
        +
        "except Exception as "
        "_sap_visual_commit_error:\n"
        +
        indent
        +
        "    print("
        "f\"VISUAL_UNIFIED_COMMIT="
        "FAIL_OPEN "
        "{type(_sap_visual_commit_error).__name__}: "
        "{_sap_visual_commit_error}\")\n"
        +
        indent
        +
        "# Primeiro download válido vence.\n"
        +
        indent
        +
        "# Impede foto -> vídeo ou "
        "vídeo -> foto depois do sucesso.\n"
        +
        indent
        +
        "break\n"
    )


    midia_src = (
        midia_src[:line_end]
        +
        commit_patch
        +
        midia_src[line_end:]
    )


    print(
        "MIDIA_COMMIT_PATCH=INSTALLED"
    )

else:

    print(
        "MIDIA_COMMIT_PATCH="
        "ALREADY_PRESENT"
    )


MIDIA.write_text(
    midia_src,
    encoding="utf-8",
)


# ============================================================
# 7. FINAL COMPILE + AUTO ROLLBACK
# ============================================================

if not compile_file(
    MIDIA
):

    print(
        "MIDIA_COMPILE=FAIL"
    )

    backup_file = (
        BACKUP
        / "midia.py"
    )

    if backup_file.exists():

        shutil.copy2(
            backup_file,
            MIDIA,
        )

        print(
            "MIDIA_ROLLBACK=PASS"
        )


    raise RuntimeError(
        "midia integration compile FAIL"
    )


print(
    "MIDIA_COMPILE=PASS"
)


if not compile_file(
    VSE
):

    raise RuntimeError(
        "VSE final compile FAIL"
    )


if not compile_file(
    UNIFIED
):

    raise RuntimeError(
        "Unified final compile FAIL"
    )


manifest = {

    "version":
        "5.0",

    "timestamp":
        STAMP,

    "backup":
        str(BACKUP),

    "files": {

        "midia.py":
            sha256(
                MIDIA
            ),

        "visual_selection_engine_v4.py":
            sha256(
                VSE
            ),

        "visual_engine_unified.py":
            sha256(
                UNIFIED
            ),
    },

    "features": {

        "semantic":
            True,

        "geography":
            True,

        "false_medical":
            True,

        "generic_lifestyle":
            True,

        "provider_diversity":
            True,

        "type_diversity":
            True,

        "single_scene_commit":
            True,

        "fail_open":
            True,
    },
}


manifest_path = (
    ROOT
    / "manifests"
    / "visual_stack_v5.json"
)

manifest_path.parent.mkdir(
    parents=True,
    exist_ok=True,
)

manifest_path.write_text(
    json.dumps(
        manifest,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)


print()
print("=" * 70)
print("VISUAL CONSOLIDATION V5 COMPLETE")
print("=" * 70)

print(
    "BACKUP_PATH=",
    BACKUP,
)

print(
    "VSE_SELF_TEST=PASS"
)

print(
    "UNIFIED_SYNTHETIC=PASS"
)

print(
    "MIDIA_COMPILE=PASS"
)

print(
    "VISUAL_STACK_V5=INSTALLED"
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
