#!/usr/bin/env python3

import inspect
import os
from collections import Counter

import visual_selection_engine_v4 as vse


_SUCCESS_HISTORY = {}


TRANSLATIONS = {
    "investigacao": "police investigation",
    "investigação": "police investigation",
    "policia": "police",
    "polícia": "police",
    "apartamento": "apartment",
    "predio": "building",
    "prédio": "building",
    "laudo": "forensic report",
    "pericia": "forensic investigation",
    "perícia": "forensic investigation",
    "indicios": "evidence clues",
    "indícios": "evidence clues",
    "evidencia": "evidence",
    "evidência": "evidence",
    "tribunal": "courtroom",
    "julgamento": "court trial",
    "condenacao": "court conviction",
    "condenação": "court conviction",
    "hospital": "hospital emergency",
    "incendio": "fire emergency",
    "incêndio": "fire emergency",
    "aviao": "aircraft",
    "avião": "aircraft",
    "navio": "ship",
    "guerra": "war military",
    "cientista": "scientist laboratory",
    "laboratorio": "laboratory",
    "laboratório": "laboratory",
    "espaco": "space",
    "espaço": "space",
    "foguete": "rocket",
    "enchente": "flood",
    "inundacao": "flood",
    "inundação": "flood",
}


def enabled():

    return (
        os.getenv(
            "SAP_VSE42",
            "1",
        )
        !=
        "0"
    )


def _short_id():

    return os.getenv(
        "SHORT_ID",
        "default",
    )


def _candidate_like(value):

    if isinstance(value, dict):

        return bool(
            set(value)
            &
            {
                "provider",
                "url",
                "source_url",
                "title",
                "tipo",
                "type",
                "score",
                "id",
                "download_url",
            }
        )

    return False


def collect_candidates(ctx):

    result = []
    seen = set()

    preferred = (
        "candidatos",
        "todos",
        "alternativas",
        "resultados",
        "candidates",
        "wiki_aprovados",
    )

    values = []

    for name in preferred:

        if name in ctx:
            values.append(
                ctx[name]
            )

    for value in values:

        flat = vse.flatten_candidates(
            value
        )

        for candidate in flat:

            if not _candidate_like(candidate):
                continue

            key = vse.candidate_key(
                candidate
            )

            if key in seen:
                continue

            seen.add(key)
            result.append(candidate)

    chosen = ctx.get(
        "escolhido"
    )

    if _candidate_like(chosen):

        key = vse.candidate_key(chosen)

        if key not in seen:
            result.append(chosen)

    return result


def scene_from_context(ctx):

    for key in (
        "scene",
        "cena",
        "segmento",
        "scene_data",
    ):

        value = ctx.get(key)

        if isinstance(
            value,
            (str, dict),
        ):
            return value


    scene = {}

    mapping = {
        "texto":
            ("texto", "text", "narration"),

        "visual_query":
            ("visual_query", "busca", "query"),

        "must_have":
            ("must_have",),

        "avoid":
            ("avoid",),

        "location":
            ("location", "localizacao"),
    }


    for target, names in mapping.items():

        for name in names:

            if name in ctx:
                scene[target] = ctx[name]
                break


    return scene


def _history_state():

    sid = _short_id()

    history = _SUCCESS_HISTORY.setdefault(
        sid,
        [],
    )

    return {
        "providers": [
            x["provider"]
            for x in history
        ],
        "groups": [
            x["group"]
            for x in history
        ],
        "types": [
            x["type"]
            for x in history
        ],
        "keys": [
            x["key"]
            for x in history
        ],
    }


def note_success(candidate, destination=None):

    if not _candidate_like(candidate):
        return

    sid = _short_id()

    history = _SUCCESS_HISTORY.setdefault(
        sid,
        [],
    )

    history.append(
        {
            "provider":
                vse.provider(candidate),

            "group":
                vse.source_group(candidate),

            "type":
                vse.media_type(candidate),

            "key":
                vse.candidate_key(candidate),

            "destination":
                str(destination or ""),
        }
    )


def _translate(text):

    if not text:
        return ""

    result = str(text)

    low = result.casefold()

    additions = []

    for src, dst in TRANSLATIONS.items():

        if src in low:
            additions.append(dst)

    if additions:
        result += " " + " ".join(additions)

    return " ".join(
        result.split()
    )


def query_variants(scene, ctx=None):

    ctx = ctx or {}

    parts = []

    if isinstance(scene, str):

        parts.append(scene)

    elif isinstance(scene, dict):

        for key in (
            "visual_query",
            "busca",
            "location",
            "must_have",
            "texto",
            "text",
        ):

            value = scene.get(key)

            if isinstance(value, str):
                parts.append(value)

            elif isinstance(value, (list, tuple)):
                parts.extend(
                    str(x)
                    for x in value
                    if x
                )


    for key in (
        "busca",
        "visual_query",
        "location",
    ):

        value = ctx.get(key)

        if isinstance(value, str):
            parts.append(value)


    must = ctx.get(
        "must_have",
        [],
    )

    if isinstance(must, str):
        parts.append(must)

    elif isinstance(must, (list, tuple)):
        parts.extend(
            str(x)
            for x in must
            if x
        )


    base = " ".join(parts)

    base = " ".join(
        base.split()
    )

    translated = _translate(base)


    concepts = sorted(
        vse.concept_hits(
            base
        )
    )


    variants = []

    for q in (
        base,
        translated,
        (
            "documentary "
            + " ".join(concepts)
            + " "
            + translated
        ),
    ):

        q = " ".join(
            str(q).split()
        )

        if (
            q
            and
            q.casefold()
            not in {
                x.casefold()
                for x in variants
            }
        ):
            variants.append(q)


    return variants[:3]


def _call_search(search_fn, query, ctx):

    sig = inspect.signature(
        search_fn
    )

    kwargs = {}

    aliases = {
        "busca": query,
        "query": query,
        "search": query,
        "visual_query": query,

        "must_have":
            ctx.get("must_have", []),

        "avoid":
            ctx.get("avoid", []),

        "rota_fonte":
            ctx.get("rota_fonte"),

        "segmento":
            ctx.get("segmento"),

        "visual_mode":
            ctx.get("visual_mode"),
    }


    for name, param in sig.parameters.items():

        if name in aliases:

            value = aliases[name]

            if value is not None:
                kwargs[name] = value

            continue


        if (
            param.default
            is
            inspect.Parameter.empty
        ):

            return None


    try:

        return search_fn(
            **kwargs
        )

    except Exception as exc:

        print(
            "VSE42_RESCUE_SEARCH_ERROR="
            f"{type(exc).__name__}:{exc}"
        )

        return None


def rank_candidates(
    candidates,
    scene,
    reference=None,
):

    state = _history_state()

    scored = []

    for candidate in candidates:

        try:

            result = vse.score_candidate(
                candidate,
                scene,
                state,
            )

        except Exception as exc:

            print(
                "VSE42_SCORE_ERROR="
                f"{type(exc).__name__}:{exc}"
            )

            continue


        scored.append(
            (
                candidate,
                result,
            )
        )


    if not scored:
        return reference, None


    non_hard = [
        x
        for x in scored
        if not x[1].get(
            "hard_mismatch",
            False,
        )
    ]


    working = (
        non_hard
        if non_hard
        else scored
    )


    ref_result = None

    if reference is not None:

        for candidate, result in scored:

            if (
                vse.candidate_key(candidate)
                ==
                vse.candidate_key(reference)
            ):

                ref_result = result
                break


    reference_hard = bool(
        ref_result
        and
        ref_result.get(
            "hard_mismatch",
            False,
        )
    )


    ref_must = (
        vse.must_tier(
            reference,
            scene,
        )
        if reference is not None
        else 0
    )


    if (
        reference is not None
        and
        not reference_hard
    ):

        protected = [
            x
            for x in working
            if (
                vse.must_tier(
                    x[0],
                    scene,
                )
                >=
                ref_must
            )
        ]

        if protected:
            working = protected


    working.sort(
        key=lambda pair: (
            vse.must_tier(
                pair[0],
                scene,
            ),
            pair[1].get(
                "effective",
                0,
            ),
        ),
        reverse=True,
    )


    return working[0]


def final_gate_from_context(
    ctx,
    global_ctx,
):

    reference = ctx.get(
        "escolhido"
    )

    if not enabled():
        return reference


    scene = scene_from_context(
        ctx
    )

    candidates = collect_candidates(
        ctx
    )


    if reference is not None:

        keys = {
            vse.candidate_key(c)
            for c in candidates
        }

        if (
            vse.candidate_key(reference)
            not in keys
        ):
            candidates.append(
                reference
            )


    if not candidates:
        return reference


    best, best_score = rank_candidates(
        candidates,
        scene,
        reference,
    )


    reference_score = None

    if reference is not None:

        reference_score = vse.score_candidate(
            reference,
            scene,
            _history_state(),
        )


    need_rescue = False

    if reference is None:
        need_rescue = True

    elif reference_score:

        need_rescue = (
            reference_score.get(
                "hard_mismatch",
                False,
            )
            or
            vse.must_tier(
                reference,
                scene,
            )
            < 2
        )


    rescue_enabled = (
        os.getenv(
            "SAP_VSE42_RESCUE",
            "1",
        )
        !=
        "0"
    )


    search_fn = global_ctx.get(
        "buscar_todos_candidatos"
    )


    if (
        need_rescue
        and
        rescue_enabled
        and
        callable(search_fn)
    ):

        print(
            "VSE42_RESCUE=START"
        )

        existing = {
            vse.candidate_key(c)
            for c in candidates
        }

        for query in query_variants(
            scene,
            ctx,
        ):

            print(
                "VSE42_RESCUE_QUERY="
                + query
            )

            extra = _call_search(
                search_fn,
                query,
                ctx,
            )

            if extra is None:
                continue

            for candidate in vse.flatten_candidates(
                extra
            ):

                if not _candidate_like(
                    candidate
                ):
                    continue

                key = vse.candidate_key(
                    candidate
                )

                if key in existing:
                    continue

                existing.add(key)
                candidates.append(
                    candidate
                )


        best, best_score = rank_candidates(
            candidates,
            scene,
            reference,
        )


    if best is None:
        return reference


    print(
        "VSE42_FINAL="
        f"{vse.provider(best)}/"
        f"{vse.media_type(best)} "
        f"must={vse.must_tier(best, scene)} "
        f"effective="
        f"{best_score.get('effective', 0):.1f} "
        f"hard="
        f"{best_score.get('hard_mismatch', False)}"
    )


    if best_score.get(
        "hard_reasons"
    ):

        print(
            "VSE42_REASONS="
            +
            ",".join(
                best_score[
                    "hard_reasons"
                ]
            )
        )


    if reference is not None:

        changed = (
            vse.candidate_key(best)
            !=
            vse.candidate_key(reference)
        )

        print(
            "VSE42_OVERRIDE="
            +
            (
                "YES"
                if changed
                else "NO"
            )
        )


    return best
