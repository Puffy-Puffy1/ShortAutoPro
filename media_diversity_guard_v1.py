#!/usr/bin/env python3

"""
ShortAutoPro
Media Diversity Guard / VSE4 Runtime V2.1

Funções:
- reranqueia o pool FINAL de candidatos;
- aplica score_candidate() do VSE4;
- hard mismatch vai para o final;
- mantém fallback, sem eliminar todas as alternativas;
- histórico de provider/source_group/type/key;
- integra Scene Commit Lock V2.1;
- fail-open.
"""

import os


_ENABLED = (
    os.getenv(
        "SAP_VISUAL_STACK_V2",
        "1",
    )
    !=
    "0"
)


_current_sid = None

_state = {
    "providers": [],
    "groups": [],
    "types": [],
    "keys": [],
}


def _sid():

    return (
        os.getenv(
            "SHORT_ID",
            ""
        ).strip()
        or
        "unknown"
    )


def _ensure_state():

    global _current_sid

    sid = _sid()

    if sid != _current_sid:

        _current_sid = sid

        for key in _state:
            _state[
                key
            ].clear()

    return _state


def _safe_text(value):

    if value is None:
        return ""

    if isinstance(
        value,
        str,
    ):
        return value.strip()

    if isinstance(
        value,
        (
            int,
            float,
        ),
    ):
        return str(value)

    if isinstance(
        value,
        (
            list,
            tuple,
            set,
        ),
    ):

        return " ".join(
            _safe_text(x)
            for x in value
            if _safe_text(x)
        )

    if isinstance(
        value,
        dict,
    ):

        parts = []

        for key in (
            "texto",
            "text",
            "description",
            "visual_query",
            "query",
            "busca",
            "segmento",
            "title",
            "topic",
            "location",
            "local",
        ):

            if key in value:

                text = _safe_text(
                    value.get(key)
                )

                if text:
                    parts.append(
                        text
                    )

        return " ".join(
            parts
        )

    return ""


def build_scene_context(context):

    if not isinstance(
        context,
        dict,
    ):

        return {
            "description":
                _safe_text(
                    context
                )
        }


    positive_keys = (
        "scene",
        "cena",
        "segmento",
        "texto",
        "text",
        "visual_query",
        "busca",
        "query",
        "search_query",
        "topic",
        "tema",
        "location",
        "local",
        "must_have",
    )


    parts = []


    for key in positive_keys:

        if key not in context:
            continue

        text = _safe_text(
            context.get(key)
        )

        if text:
            parts.append(
                text
            )


    scene = {
        "description":
            " ".join(
                parts
            ),

        "must_have":
            context.get(
                "must_have",
                []
            ),

        "avoid":
            context.get(
                "avoid",
                []
            ),

        "location":
            (
                context.get(
                    "location"
                )
                or
                context.get(
                    "local"
                )
                or
                ""
            ),

        "topic":
            (
                context.get(
                    "topic"
                )
                or
                context.get(
                    "tema"
                )
                or
                ""
            ),
    }


    return scene


def _score(
    candidate,
    scene,
):

    from visual_selection_engine_v4 import (
        score_candidate,
    )


    state = _ensure_state()


    result = score_candidate(
        candidate,
        scene,
        state,
    )


    if not isinstance(
        result,
        dict,
    ):

        result = {
            "effective":
                float(
                    result
                    or
                    0
                ),

            "hard_mismatch":
                False,
        }


    return result


def _float(
    value,
    default=0.0,
):

    try:
        return float(
            value
        )
    except Exception:
        return default


def _effective(result):

    for key in (
        "effective",
        "effective_score",
        "score",
        "final_score",
    ):

        if key in result:
            return _float(
                result.get(key)
            )

    return 0.0


def rerank_pool(
    pool,
    context=None,
    chosen=None,
):

    if not _ENABLED:
        return list(
            pool
            or
            []
        )


    original = list(
        pool
        or
        []
    )


    if len(original) <= 1:
        return original


    scene = build_scene_context(
        context
    )


    scored = []


    for index, candidate in enumerate(
        original
    ):

        try:

            result = _score(
                candidate,
                scene,
            )

            hard = bool(
                result.get(
                    "hard_mismatch",
                    False,
                )
            )

            effective = _effective(
                result
            )


            scored.append(
                (
                    1 if hard else 0,
                    -effective,
                    index,
                    candidate,
                    result,
                )
            )


        except Exception as exc:

            # Fail-open:
            # candidato continua no pool,
            # mas após candidatos avaliados.
            scored.append(
                (
                    0,
                    0.0,
                    index,
                    candidate,
                    {
                        "runtime_error":
                            (
                                f"{type(exc).__name__}:"
                                f"{exc}"
                            )
                    },
                )
            )


    scored.sort(
        key=lambda row: (
            row[0],
            row[1],
            row[2],
        )
    )


    # Deduplicação semântica pelo VSE4.
    try:

        from visual_selection_engine_v4 import (
            candidate_key,
        )

    except Exception:

        candidate_key = None


    final = []
    seen = set()


    for (
        _hard,
        _neg_effective,
        _index,
        candidate,
        _result,
    ) in scored:

        key = None

        if callable(
            candidate_key
        ):

            try:
                key = candidate_key(
                    candidate
                )
            except Exception:
                key = None


        if key:

            if key in seen:
                continue

            seen.add(
                key
            )


        final.append(
            candidate
        )


    print(
        "VSE4_FINAL_POOL="
        f"{len(original)}->{len(final)}"
    )


    for rank, row in enumerate(
        scored[:3],
        start=1,
    ):

        hard = bool(
            row[0]
        )

        effective = -row[1]

        candidate = row[3]


        try:

            from visual_selection_engine_v4 import (
                provider,
                media_type,
            )

            p = provider(
                candidate
            )

            t = media_type(
                candidate
            )

        except Exception:

            p = "unknown"
            t = "unknown"


        print(
            f"VSE4_RANK_{rank}="
            f"{p}/{t} "
            f"effective={effective:.1f} "
            f"hard_mismatch={'YES' if hard else 'NO'}"
        )


    return final


def note_success(candidate):

    if candidate is None:
        return


    state = _ensure_state()


    try:

        from visual_selection_engine_v4 import (
            provider,
            source_group,
            media_type,
            candidate_key,
        )


        p = provider(
            candidate
        )

        g = source_group(
            candidate
        )

        t = media_type(
            candidate
        )

        k = candidate_key(
            candidate
        )


        if p:
            state[
                "providers"
            ].append(
                p
            )

        if g:
            state[
                "groups"
            ].append(
                g
            )

        if t:
            state[
                "types"
            ].append(
                t
            )

        if k:
            state[
                "keys"
            ].append(
                k
            )


        # Limita memória.
        for name in state:

            if len(
                state[name]
            ) > 40:

                state[name][
                    :
                    len(
                        state[name]
                    )
                    -
                    40
                ] = []


        print(
            "VISUAL_HISTORY="
            f"provider={p} "
            f"group={g} "
            f"type={t}"
        )


    except Exception as exc:

        print(
            "VISUAL_HISTORY_FAILOPEN="
            f"{type(exc).__name__}"
        )


def install_runtime(namespace):

    if not _ENABLED:

        print(
            "VISUAL_STACK_V2=DISABLED"
        )

        return False


    try:

        from visual_scene_commit_lock_v1 import (
            install_runtime as
            install_commit,
        )


        install_commit(
            namespace
        )


        print(
            "VISUAL_STACK_RUNTIME=PASS"
        )

        return True


    except Exception as exc:

        print(
            "VISUAL_STACK_RUNTIME=FAILOPEN "
            f"{type(exc).__name__}: {exc}"
        )

        return False


if __name__ == "__main__":

    print(
        "MEDIA_DIVERSITY_GUARD_V21=READY"
    )
