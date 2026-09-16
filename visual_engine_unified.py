#!/usr/bin/env python3

"""
ShortAutoPro Visual Engine Unified V5.1.

Única fachada entre midia.py e o motor visual.

Responsabilidades:
- normalizar contexto estruturado da cena
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


VERSION = "5.1"


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
    """Build one structured scene contract for VSE scoring.

    Previous versions flattened ``must_have`` into a generic text list. That
    prevented ``visual_selection_engine_v4`` from independently verifying each
    explicit MUST against the candidate metadata. Keep semantic fields
    structured so the score printed by Visual Unified matches the evidence
    used to choose the downloaded asset.
    """

    if not isinstance(ctx, dict):
        return {"texto": str(ctx or "")}

    scene = {}

    # Start with the structured scene when it exists.
    for name in ("cena", "scene"):
        value = ctx.get(name)
        if isinstance(value, dict):
            scene.update(value)
            break

    text = _context_value(
        ctx,
        ("texto", "text", "narracao", "narration", "segmento"),
    )
    query = _context_value(
        ctx,
        ("visual_query", "busca", "query"),
    )
    must = _context_value(
        ctx,
        ("must_have", "must"),
    )
    avoid = _context_value(
        ctx,
        ("avoid", "avoid_terms"),
    )
    location = _context_value(
        ctx,
        ("location", "local", "geo"),
    )
    visual_mode = _context_value(
        ctx,
        ("visual_mode", "modo_visual"),
    )
    topic = _context_value(
        ctx,
        ("topic", "tema", "ASSUNTO"),
    )

    if text is not None:
        scene["texto"] = text
    if query is not None:
        scene["visual_query"] = query
    if must is not None:
        scene["must_have"] = must
    if avoid is not None:
        scene["avoid"] = avoid
    if location is not None:
        scene["location"] = location
    if visual_mode is not None:
        scene["visual_mode"] = visual_mode
    if topic is not None:
        scene["topic"] = topic

    return scene


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
