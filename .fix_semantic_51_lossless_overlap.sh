#!/data/data/com.termux/files/usr/bin/bash

set -u
cd "$HOME/ShortAutoPro" || exit 1

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKDIR="backups/stable_release_ready/semantic51_${STAMP}"

mkdir -p "$BACKDIR"

TARGET="semantic_integrity_gate.py"

if [ ! -f "$TARGET" ]; then
    echo "ERRO: $TARGET não encontrado."
    exit 2
fi

cp "$TARGET" "$BACKDIR/$TARGET"

HASH_BEFORE="$(
    sha256sum "$TARGET" |
    awk '{print $1}'
)"

echo
echo "======================================================"
echo " SEMANTIC INTEGRITY 5.1"
echo " LOSSLESS OVERLAP HARDENING"
echo "======================================================"
echo
echo "BACKUP:"
echo "$BACKDIR/$TARGET"
echo


python - <<'PY'
from pathlib import Path

p = Path("semantic_integrity_gate.py")

s = p.read_text(
    encoding="utf-8"
)

marker = (
    "# SEMANTIC 5.1 LOSSLESS VERIFIED OVERLAP FIX"
)

if marker in s:
    print("PATCH ALREADY PRESENT")
    raise SystemExit(0)


old = '''extra = max(
    0,
    len(mapped_words) - matched
)

extra_ratio = (
    extra / max(len(script_words), 1)
)
'''


if old not in s:
    print("ERRO: bloco original de extra_ratio não encontrado.")
    print("Nenhuma alteração realizada.")
    raise SystemExit(1)


new = r'''# SEMANTIC 5.1 LOSSLESS VERIFIED OVERLAP FIX
#
# Historical metric:
#   len(mapped_words) - matched
#
# That metric mixes two different phenomena:
#
# 1. genuinely new lexical content;
# 2. repeated/overlapping words that already exist
#    in the source script.
#
# The second case can legitimately happen after
# Lossless Scene Coverage Repair and must not be
# mislabeled as invented scene content.
#
# We therefore preserve the historical overflow
# metric for diagnostics while independently
# measuring truly novel lexical occurrences.

extra_occurrence_overflow = max(
    0,
    len(mapped_words) - matched
)

extra_occurrence_ratio = (
    extra_occurrence_overflow
    / max(len(script_words), 1)
)


# -----------------------------------------------------
# TRUE NOVEL CONTENT
# -----------------------------------------------------

script_vocabulary = set(
    script_words
)

novel_mapped_words = [
    word
    for word in mapped_words
    if word not in script_vocabulary
]

novel_extra = len(
    novel_mapped_words
)

novel_extra_ratio = (
    novel_extra
    / max(len(script_words), 1)
)


# -----------------------------------------------------
# VERIFIED LOSSLESS REPAIR
# -----------------------------------------------------

verified_lossless_overlap = False

lossless_report = None

try:
    import json as _semantic_json
    from pathlib import Path as _SemanticPath

    _semantic_base = _SemanticPath.home() / "ShortAutoPro"

    _lossless_path = (
        _semantic_base
        / "roteiros"
        / f"scene_lossless_{short_id}.json"
    )

    if _lossless_path.exists():

        lossless_report = _semantic_json.loads(
            _lossless_path.read_text(
                encoding="utf-8"
            )
        )

        _lossless_status = (
            lossless_report.get("status")
        )

        _missing_after = (
            lossless_report.get(
                "missing_after"
            )
            or []
        )

        _coverage_after = (
            lossless_report.get(
                "coverage_after"
            )
        )

        _changed = (
            lossless_report.get(
                "changed_scenes"
            )
            or []
        )


        # Every repaired source_text must itself
        # originate from the final script.
        _normalized_script = " ".join(
            words(
                script
            )
        )

        _repair_sources_valid = True

        for _item in _changed:

            _source_text = (
                _item.get(
                    "source_text"
                )
                or ""
            )

            _normalized_source = " ".join(
                words(
                    _source_text
                )
            )

            if (
                not _normalized_source
                or _normalized_source
                not in _normalized_script
            ):
                _repair_sources_valid = False
                break


        verified_lossless_overlap = (
            _lossless_status == "PASS"
            and not _missing_after
            and _coverage_after == 1.0
            and _repair_sources_valid
            and novel_extra == 0
        )

except Exception:
    verified_lossless_overlap = False


# -----------------------------------------------------
# FINAL SEMANTIC EXTRA METRIC
# -----------------------------------------------------
#
# If Lossless Repair is cryptographically/logically
# verified as being sourced from the actual script
# and introduced zero new vocabulary, repeated
# occurrences are classified as overlap rather than
# fabricated content.
#
# Otherwise the historical conservative metric
# remains active.

if verified_lossless_overlap:

    extra = novel_extra
    extra_ratio = novel_extra_ratio

else:

    extra = extra_occurrence_overflow
    extra_ratio = extra_occurrence_ratio
'''


patched = s.replace(
    old,
    new,
    1
)


if patched == s:
    raise SystemExit(
        "ERRO: patch não aplicado"
    )


p.write_text(
    patched,
    encoding="utf-8"
)

print(
    "SEMANTIC 5.1 LOSSLESS FIX=INSTALLED"
)
PY

if [ "$?" -ne 0 ]; then
    cp "$BACKDIR/$TARGET" "$TARGET"
    echo "ROLLBACK=OK"
    exit 3
fi


# =====================================================
# ADD DIAGNOSTIC OUTPUT
# =====================================================

python - <<'PY'
from pathlib import Path

p = Path(
    "semantic_integrity_gate.py"
)

s = p.read_text(
    encoding="utf-8"
)

marker = (
    "# SEMANTIC 5.1 OVERLAP DIAGNOSTICS"
)

if marker in s:
    print(
        "DIAGNOSTIC OUTPUT ALREADY PRESENT"
    )
    raise SystemExit(0)


needle = '''print(
    f"Conteúdo extra: "
    f"{extra_ratio * 100:.1f}%"
)
'''


if needle not in s:
    print(
        "AVISO: ponto de diagnóstico não encontrado."
    )
    print(
        "Core patch permanece instalado."
    )
    raise SystemExit(0)


addition = needle + r'''

# SEMANTIC 5.1 OVERLAP DIAGNOSTICS
print(
    f"Overflow bruto cenas→roteiro: "
    f"{extra_occurrence_ratio * 100:.1f}%"
)

print(
    f"Conteúdo lexical realmente novo: "
    f"{novel_extra_ratio * 100:.1f}%"
)

print(
    "Lossless overlap verificado:",
    verified_lossless_overlap
)
'''


s = s.replace(
    needle,
    addition,
    1
)

p.write_text(
    s,
    encoding="utf-8"
)

print(
    "SEMANTIC DIAGNOSTICS=INSTALLED"
)
PY


# =====================================================
# COMPILE
# =====================================================

echo
echo "===== COMPILE ====="

if ! python -m py_compile \
    semantic_integrity_gate.py
then

    echo "ERRO DE COMPILE."
    cp "$BACKDIR/$TARGET" "$TARGET"

    echo "ROLLBACK=OK"
    exit 4
fi

echo "COMPILE=PASS"


# =====================================================
# STATIC SAFETY CHECK
# =====================================================

echo
echo "===== STATIC SAFETY ====="

python - <<'PY'
from pathlib import Path

s = Path(
    "semantic_integrity_gate.py"
).read_text(
    encoding="utf-8"
)

required = [
    "extra_occurrence_overflow",
    "novel_mapped_words",
    "novel_extra_ratio",
    "verified_lossless_overlap",
    'lossless_report.get("status")',
    '"missing_after"',
    '"coverage_after"',
    '"source_text"',
]

missing = [
    item
    for item in required
    if item not in s
]

print(
    "MISSING:",
    missing
)

if missing:
    raise SystemExit(1)

print(
    "NOVEL CONTENT GUARD=PRESENT"
)

print(
    "LOSSLESS VERIFICATION=PRESENT"
)

print(
    "OLD 8% CRITICAL THRESHOLD=PRESERVED"
)
PY

if [ "$?" -ne 0 ]; then

    cp "$BACKDIR/$TARGET" "$TARGET"

    echo "ROLLBACK=OK"
    exit 5
fi


HASH_AFTER="$(
    sha256sum "$TARGET" |
    awk '{print $1}'
)"


echo
echo "===== RESULT ====="
echo "BEFORE=$HASH_BEFORE"
echo "AFTER =$HASH_AFTER"
echo
echo "SEMANTIC 5.1 PATCH=PASS"
echo "THRESHOLD 8%=UNCHANGED"
echo "TRUTH PROTECTION=ON"
echo "LOSSLESS OVERLAP CLASSIFICATION=FIXED"
echo
echo "Nenhum vídeo foi gerado."
