#!/usr/bin/env python3

import importlib.util
import inspect
import os
from pathlib import Path


ROOT = (
    Path.home()
    / "ShortAutoPro"
)

ENGINE_FILE = ROOT / 'visual_quality_engine_v5.py'


_STATE = {
    "providers": [],
    "groups": [],
    "types": [],
    "keys": [],
}


def _load_engine():

    spec = importlib.util.spec_from_file_location(
        "shortautopro_vqe5_active",
        ENGINE_FILE,
    )

    if (
        spec is None
        or spec.loader is None
    ):

        raise RuntimeError(
            f"não foi possível carregar {ENGINE_FILE}"
        )

    module = importlib.util.module_from_spec(
        spec
    )

    spec.loader.exec_module(
        module
    )

    return module


ENGINE = _load_engine()


def _enabled():

    return (
        os.getenv(
            "SAP_VQE5",
            "1",
        )
        !=
        "0"
    )


def _get(scope, *names):

    for name in names:

        if name not in scope:
            continue

        value = scope.get(
            name
        )

        if value is not None:
            return value

    return None


def _scene_from_scope(scope):

    existing = _get(
        scope,
        "scene",
        "cena",
        "scene_data",
    )

    if isinstance(
        existing,
        dict,
    ):
        return existing


    text = _get(
        scope,
        "texto",
        "texto_cena",
        "narracao",
        "trecho",
        "segmento",
    )


    query = _get(
        scope,
        "busca",
        "visual_query",
        "query",
        "search_query",
    )


    must = _get(
        scope,
        "must_have",
        "must",
        "must_terms",
    )


    avoid = _get(
        scope,
        "avoid",
        "avoid_terms",
        "evitar",
    )


    location = _get(
        scope,
        "location",
        "local",
        "geo",
        "geography",
    )


    return {
        "texto":
            text or "",

        "visual_query":
            query or "",

        "must_have":
            must or [],

        "avoid":
            avoid or [],

        "location":
            location or "",
    }


def _key(candidate):

    fn = getattr(
        ENGINE,
        "candidate_key",
        None,
    )

    if callable(fn):

        try:
            return str(
                fn(candidate)
            )
        except Exception:
            pass


    if isinstance(
        candidate,
        dict,
    ):

        for key in (
            "id",
            "url",
            "source_url",
            "download_url",
            "local_path",
            "path",
            "title",
        ):

            value = candidate.get(
                key
            )

            if value:
                return (
                    f"{key}:{value}"
                )


    return repr(
        candidate
    )


def _unique(candidates):

    result = []
    seen = set()

    for candidate in candidates:

        if candidate is None:
            continue

        key = _key(
            candidate
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        result.append(
            candidate
        )

    return result


def _score(candidate, scene):

    fn = getattr(
        ENGINE,
        "score_candidate",
        None,
    )

    if not callable(fn):
        return {}


    attempts = (
        (
            candidate,
            scene,
            _STATE,
        ),
        (
            candidate,
            scene,
        ),
    )


    last = None


    for args in attempts:

        try:

            result = fn(
                *args
            )

            if isinstance(
                result,
                dict,
            ):
                return result

            return {
                "effective":
                    result
            }

        except TypeError as exc:
            last = exc


    if last:
        raise last


    return {}


def _effective(result):

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
            return float(
                value
            )

    return 0.0


def _hard(result):

    return bool(
        result.get(
            "hard_mismatch",
            False,
        )
    )


def _must(candidate, scene):

    fn = getattr(
        ENGINE,
        "must_tier",
        None,
    )

    if not callable(fn):
        return 0


    for args in (
        (
            candidate,
            scene,
        ),
        (
            candidate,
        ),
    ):

        try:

            value = fn(
                *args
            )

            if isinstance(
                value,
                bool,
            ):
                return int(value)

            if isinstance(
                value,
                (
                    int,
                    float,
                ),
            ):
                return int(
                    value
                )

        except TypeError:
            continue

        except Exception:
            return 0


    return 0


def _choose(candidates, scene):

    fn = getattr(
        ENGINE,
        "choose_best",
        None,
    )

    if not callable(fn):

        ranked = sorted(
            candidates,
            key=lambda c:
                _effective(
                    _score(
                        c,
                        scene,
                    )
                ),
            reverse=True,
        )

        return (
            ranked[0]
            if ranked
            else None
        )


    attempts = (
        (
            candidates,
            scene,
            _STATE,
        ),
        (
            candidates,
            scene,
        ),
        (
            scene,
            candidates,
            _STATE,
        ),
        (
            scene,
            candidates,
        ),
    )


    last = None


    for args in attempts:

        try:

            result = fn(
                *args
            )


            if isinstance(
                result,
                tuple,
            ):

                if result:
                    return result[0]


            if isinstance(
                result,
                dict,
            ):

                for key in (
                    "candidate",
                    "chosen",
                    "winner",
                    "best",
                    "escolhido",
                ):

                    if key in result:
                        return result[key]


                # Pode ser o próprio candidato.
                if _key(result) in {
                    _key(x)
                    for x in candidates
                }:
                    return result


            if result is not None:
                return result


        except TypeError as exc:

            last = exc


    if last:
        raise last


    return None


def _rerank(candidates, scene):

    fn = getattr(
        ENGINE,
        "rerank",
        None,
    )


    if callable(fn):

        for args in (
            (
                candidates,
                scene,
                _STATE,
            ),
            (
                candidates,
                scene,
            ),
        ):

            try:

                result = fn(
                    *args
                )

                if isinstance(
                    result,
                    (
                        list,
                        tuple,
                    ),
                ):

                    return _unique(
                        list(result)
                    )

            except TypeError:
                continue

            except Exception:
                break


    return sorted(
        candidates,
        key=lambda c:
            _effective(
                _score(
                    c,
                    scene,
                )
            ),
        reverse=True,
    )


def final_gate_from_scope(
    scope,
    reference,
    pool,
):

    if not _enabled():

        print(
            "VQE5_FINAL_GATE=DISABLED"
        )

        return (
            reference,
            pool,
        )


    scene = _scene_from_scope(
        scope
    )


    candidates = _unique(
        [
            reference,
            *list(
                pool or []
            ),
        ]
    )


    if not candidates:

        print(
            "VQE5_FINAL_GATE=NO_CANDIDATES"
        )

        return (
            reference,
            pool,
        )


    ref_score = _score(
        reference,
        scene,
    )


    ranked = _rerank(
        candidates,
        scene,
    )


    proposed = _choose(
        ranked,
        scene,
    )


    if proposed is None:

        print(
            "VQE5_FINAL_GATE=NO_PROPOSAL"
        )

        return (
            reference,
            ranked,
        )


    known = {
        _key(c):
            c
        for c in candidates
    }


    proposed_key = _key(
        proposed
    )


    if proposed_key not in known:

        print(
            "VQE5_FINAL_GATE=REJECT_UNKNOWN"
        )

        return (
            reference,
            ranked,
        )


    proposed = known[
        proposed_key
    ]


    new_score = _score(
        proposed,
        scene,
    )


    ref_hard = _hard(
        ref_score
    )

    new_hard = _hard(
        new_score
    )

    ref_must = _must(
        reference,
        scene,
    )

    new_must = _must(
        proposed,
        scene,
    )

    ref_eff = _effective(
        ref_score
    )

    new_eff = _effective(
        new_score
    )


    override = False
    reason = "REFERENCE_PRESERVED"


    if new_hard:

        override = False
        reason = "PROPOSED_HARD_MISMATCH"


    elif ref_hard and not new_hard:

        override = True
        reason = "REFERENCE_HARD_MISMATCH"


    elif new_must < ref_must:

        override = False
        reason = "MUST_DOWNGRADE_BLOCKED"


    elif proposed_key == _key(
        reference
    ):

        override = False
        reason = "REFERENCE_STILL_BEST"


    elif new_eff >= (
        ref_eff + 5.0
    ):

        override = True
        reason = "MEANINGFUL_QUALITY_GAIN"


    else:

        override = False
        reason = "INSUFFICIENT_GAIN"


    chosen = (
        proposed
        if override
        else reference
    )


    ranked = _unique(
        [
            chosen,
            *ranked,
        ]
    )


    print()
    print(
        "VQE5 FINAL GATE:"
    )

    print(
        "  VQE5_REFERENCE_KEY=",
        _key(reference),
    )

    print(
        "  VQE5_PROPOSED_KEY=",
        proposed_key,
    )

    print(
        "  VQE5_REFERENCE="
        f"effective={ref_eff:.2f} "
        f"must={ref_must} "
        f"hard={ref_hard}"
    )

    print(
        "  VQE5_PROPOSED="
        f"effective={new_eff:.2f} "
        f"must={new_must} "
        f"hard={new_hard}"
    )

    print(
        "  VQE5_OVERRIDE="
        + (
            "YES"
            if override
            else "NO"
        )
    )

    print(
        "  VQE5_REASON="
        + reason
    )


    return (
        chosen,
        ranked,
    )


def _note_success(candidate):

    fn = getattr(
        ENGINE,
        "note_success",
        None,
    )

    if not callable(fn):
        return


    for args in (
        (
            candidate,
            _STATE,
        ),
        (
            candidate,
        ),
    ):

        try:

            fn(
                *args
            )

            return

        except TypeError:
            continue

        except Exception:
            return


def _update_local_state(candidate):

    try:

        provider_fn = getattr(
            ENGINE,
            "provider",
            None,
        )

        group_fn = getattr(
            ENGINE,
            "source_group",
            None,
        )

        type_fn = getattr(
            ENGINE,
            "media_type",
            None,
        )


        if callable(provider_fn):

            _STATE[
                "providers"
            ].append(
                provider_fn(
                    candidate
                )
            )


        if callable(group_fn):

            _STATE[
                "groups"
            ].append(
                group_fn(
                    candidate
                )
            )


        if callable(type_fn):

            _STATE[
                "types"
            ].append(
                type_fn(
                    candidate
                )
            )


        _STATE[
            "keys"
        ].append(
            _key(
                candidate
            )
        )


        # Estado limitado.
        for key in (
            "providers",
            "groups",
            "types",
            "keys",
        ):

            _STATE[key] = (
                _STATE[key][-24:]
            )


    except Exception:
        pass


def cleanup_scene_siblings(
    destination,
):

    if not destination:
        return []


    path = Path(
        str(destination)
    )


    try:

        resolved = path.resolve()
        media_root = (
            ROOT
            / "imagens"
        ).resolve()


        if (
            media_root
            not in resolved.parents
        ):

            return []


    except Exception:

        return []


    allowed = {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
        ".mp4",
        ".mov",
        ".webm",
    }


    removed = []


    stem = path.stem


    for sibling in path.parent.glob(
        stem + ".*"
    ):

        try:

            if (
                sibling.resolve()
                ==
                resolved
            ):
                continue


            if (
                sibling.suffix.casefold()
                not in allowed
            ):
                continue


            if sibling.is_file():

                sibling.unlink()

                removed.append(
                    str(sibling)
                )


        except Exception:
            continue


    return removed


def post_download_commit(
    scope,
    destination,
    candidate,
):

    removed = cleanup_scene_siblings(
        destination
    )


    _note_success(
        candidate
    )


    _update_local_state(
        candidate
    )


    print(
        "VQE5_SCENE_COMMIT=PASS"
    )

    print(
        "VQE5_SCENE_DESTINATION=",
        destination,
    )

    print(
        "VQE5_SCENE_SIBLINGS_REMOVED=",
        len(removed),
    )


    return removed
