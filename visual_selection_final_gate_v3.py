#!/usr/bin/env python3

import os

from collections import Counter

from visual_selection_engine_v2 import (
    quality_breakdown,
    must_info,
    must_tier,
    avoid_hits,
    candidate_provider,
    candidate_group,
    candidate_key,
    media_type,
)


ENABLED = (
    os.environ.get(
        "SAP_VSE_V3",
        "1",
    ).strip().lower()
    not in {
        "0",
        "false",
        "off",
        "no",
    }
)


SAME_TIER_MARGIN = float(
    os.environ.get(
        "SAP_VSE_V3_MARGIN",
        "10",
    )
)


def _identity(candidate):
    if not isinstance(candidate, dict):
        return ""

    key = candidate_key(candidate)

    if key:
        return key

    return "|".join(
        [
            str(
                candidate.get(
                    "fonte",
                    ""
                )
            ),
            str(
                candidate.get(
                    "tipo",
                    ""
                )
            ),
            str(
                candidate.get(
                    "id",
                    ""
                )
            ),
            str(
                candidate.get(
                    "url",
                    ""
                )
            ),
        ]
    )


def _truth_safe(candidate):
    if not isinstance(candidate, dict):
        return False

    truth = candidate.get(
        "_vi6_truth_ok",
        None,
    )

    if truth is False:
        return False

    if isinstance(truth, str):

        if truth.strip().lower() in {
            "false",
            "0",
            "no",
            "fail",
            "blocked",
        }:
            return False


    risk = str(
        candidate.get(
            "_vi6_risk",
            ""
        )
    ).strip().upper()


    if risk in {
        "HIGH",
        "CRITICAL",
        "BLOCK",
        "BLOCKED",
    }:
        return False


    return True


def _deduplicate(reference, candidates):
    output = []
    seen = set()

    source = []

    if isinstance(reference, dict):
        source.append(reference)

    if isinstance(candidates, list):
        source.extend(candidates)


    for candidate in source:

        if not isinstance(candidate, dict):
            continue

        key = _identity(candidate)

        if not key:
            key = f"OBJECT:{id(candidate)}"

        if key in seen:
            continue

        seen.add(key)
        output.append(candidate)

    return output


def _eligible(
    candidate,
    reference,
    scorer=None,
    preserve_fn=None,
):
    if not _truth_safe(candidate):
        return False, "TRUTH_OR_RISK"


    info = quality_breakdown(
        candidate,
        scorer,
    )


    # ZERO MUST ou menos de metade nunca sobe
    # para o vencedor principal.
    if info["tier"] <= 1:
        return False, "MUST_TOO_LOW"


    if info["avoid_hits"] > 0:
        return False, "AVOID_HIT"


    if (
        candidate is not reference
        and
        callable(preserve_fn)
    ):

        try:
            preserved = bool(
                preserve_fn(candidate)
            )

        except Exception:
            preserved = False


        if not preserved:
            return False, "QUALITY_NOT_PRESERVED"


    return True, "PASS"


def choose_final_candidate_v3(
    reference,
    candidates,
    scorer=None,
    preserve_fn=None,
):

    if (
        not ENABLED
        or
        not isinstance(reference, dict)
    ):
        return reference, {
            "override": False,
            "reason": "DISABLED_OR_NO_REFERENCE",
        }


    pool = _deduplicate(
        reference,
        candidates,
    )


    reference_info = quality_breakdown(
        reference,
        scorer,
    )


    accepted = []


    for candidate in pool:

        ok, reason = _eligible(
            candidate,
            reference,
            scorer,
            preserve_fn,
        )


        info = quality_breakdown(
            candidate,
            scorer,
        )


        if ok:

            accepted.append(
                (
                    candidate,
                    info,
                )
            )


    if not accepted:

        return reference, {
            "override": False,
            "reason": "NO_ELIGIBLE_ALTERNATIVE",
            "reference":
                reference_info,
        }


    accepted.sort(
        key=lambda row: (
            row[1]["tier"],
            -row[1]["avoid_hits"],
            -row[1]["mismatch_penalty"],
            row[1]["effective_score"],
            row[1]["base"],
        ),
        reverse=True,
    )


    best, best_info = accepted[0]


    if _identity(best) == _identity(reference):

        return reference, {
            "override": False,
            "reason": "REFERENCE_STILL_BEST",
            "reference":
                reference_info,
            "best":
                best_info,
        }


    # Regra mais importante:
    # MUST tier superior sempre ganha se preserva qualidade.
    if (
        best_info["tier"]
        >
        reference_info["tier"]
    ):

        return best, {
            "override": True,
            "reason": "HIGHER_MUST_TIER",
            "reference":
                reference_info,
            "best":
                best_info,
        }


    # Nunca piora MUST.
    if (
        best_info["tier"]
        <
        reference_info["tier"]
    ):

        return reference, {
            "override": False,
            "reason": "WOULD_DOWNGRADE_MUST",
            "reference":
                reference_info,
            "best":
                best_info,
        }


    # Mesmo tier: precisa ser visivelmente melhor.
    if (
        best_info["effective_score"]
        >=
        reference_info["effective_score"]
        +
        SAME_TIER_MARGIN
        and
        best_info["mismatch_penalty"]
        <=
        reference_info["mismatch_penalty"]
        and
        best_info["avoid_hits"]
        <=
        reference_info["avoid_hits"]
    ):

        return best, {
            "override": True,
            "reason": "SAME_TIER_BETTER_VISUAL",
            "reference":
                reference_info,
            "best":
                best_info,
        }


    return reference, {
        "override": False,
        "reason": "IMPROVEMENT_TOO_SMALL",
        "reference":
            reference_info,
        "best":
            best_info,
    }


def _summary(candidate, scorer=None):
    if not isinstance(candidate, dict):
        return "NONE"

    hits, total, ratio = must_info(
        candidate
    )

    info = quality_breakdown(
        candidate,
        scorer,
    )

    return (
        f"{candidate.get('fonte', '?')}/"
        f"{candidate.get('tipo', '?')} "
        f"must={hits}/{total} "
        f"base={info['base']:.1f} "
        f"effective={info['effective_score']:.1f} "
        f"mismatch={info['mismatch_penalty']:.1f} "
        f"provider={candidate_provider(candidate) or '?'}"
    )


def telemetry_lines_v3(
    reference,
    final,
    meta,
    candidates,
    scorer=None,
):
    providers = Counter()

    if isinstance(candidates, list):

        for candidate in candidates:

            if not isinstance(candidate, dict):
                continue

            provider = (
                candidate_provider(candidate)
                or
                str(
                    candidate.get(
                        "fonte",
                        "UNKNOWN",
                    )
                ).lower()
            )

            providers[
                provider
            ] += 1


    provider_text = ",".join(
        f"{name}:{count}"
        for name, count
        in sorted(
            providers.items()
        )
    )


    return [
        "VSE3_POOL_PROVIDERS="
        +
        (
            provider_text
            or "NONE"
        ),

        "VSE3_BEFORE="
        +
        _summary(
            reference,
            scorer,
        ),

        "VSE3_AFTER="
        +
        _summary(
            final,
            scorer,
        ),

        "VSE3_OVERRIDE="
        +
        (
            "YES"
            if meta.get(
                "override"
            )
            else "NO"
        ),

        "VSE3_REASON="
        +
        str(
            meta.get(
                "reason",
                "?",
            )
        ),
    ]


if __name__ == "__main__":
    print(
        "SHORTAUTOPRO VISUAL SELECTION FINAL GATE V3"
    )
    print(
        "ENABLED=",
        ENABLED,
    )
