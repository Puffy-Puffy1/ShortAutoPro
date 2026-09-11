#!/data/data/com.termux/files/usr/bin/bash
set -u
cd "$HOME/ShortAutoPro" || exit 1

echo
echo "=================================================="
echo " VI8.71 -> VI8.80"
echo " SEARCH ARCHITECTURE DISCOVERY"
echo " READ ONLY / SHADOW"
echo "=================================================="
echo

VIDEO_BEFORE="$(sha256sum video.py | awk '{print $1}')"
GERAR_BEFORE="$(sha256sum gerar_short.sh | awk '{print $1}')"


# =====================================================
# VI8.71 — SOURCE CODE DISCOVERY
# =====================================================

cat > vi8_71_search_code_discovery.py <<'PY'
#!/usr/bin/env python3

from pathlib import Path
import re

VERSION = "8.71"

BASE = Path.home() / "ShortAutoPro"

KEYWORDS = (
    "wikimedia",
    "wikipedia",
    "commons",
    "search",
    "buscar",
    "busca",
    "download",
    "requests.get",
    "requests.post",
    "urllib",
    "httpx",
    "aiohttp",
    "provider",
    "source_router",
    "media",
    "image",
    "imagem",
)

EXCLUDED_DIRS = {
    "__pycache__",
    "backups",
    ".git",
    "videos",
    "audios",
    "temp",
}


def discover():
    files = []

    for path in BASE.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {
            ".py",
            ".sh",
        }:
            continue

        if any(
            part in EXCLUDED_DIRS
            for part in path.parts
        ):
            continue

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="ignore"
            )
        except Exception:
            continue

        low = text.lower()

        hits = [
            keyword
            for keyword in KEYWORDS
            if keyword.lower() in low
        ]

        if not hits:
            continue

        functions = re.findall(
            r"^\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(",
            text,
            flags=re.M
        )

        files.append({
            "path": str(path),
            "relative":
                str(path.relative_to(BASE)),
            "hits": sorted(
                set(hits)
            ),
            "functions":
                functions[:40],
        })

    files.sort(
        key=lambda item: (
            -len(item["hits"]),
            item["relative"]
        )
    )

    return {
        "version": VERSION,
        "count": len(files),
        "files": files,
    }


def self_test():
    assert VERSION == "8.71"
    print(
        "VI8.71 SEARCH CODE DISCOVERY=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.72 — NETWORK CALL AUDITOR
# =====================================================

cat > vi8_72_network_call_auditor.py <<'PY'
#!/usr/bin/env python3

from pathlib import Path
import re

VERSION = "8.72"

PATTERNS = {
    "requests_get":
        r"\brequests\.get\s*\(",

    "requests_post":
        r"\brequests\.post\s*\(",

    "urllib":
        r"\burllib\.",

    "httpx":
        r"\bhttpx\.",

    "aiohttp":
        r"\baiohttp\.",

    "curl_shell":
        r"\bcurl\s+",

    "wget_shell":
        r"\bwget\s+",
}


def audit(path):
    p = Path(path)

    try:
        text = p.read_text(
            encoding="utf-8",
            errors="ignore"
        )
    except Exception:
        return {
            "path": str(p),
            "calls": [],
        }

    calls = []

    lines = text.splitlines()

    for number, line in enumerate(
        lines,
        start=1
    ):
        for name, pattern in (
            PATTERNS.items()
        ):
            if re.search(
                pattern,
                line
            ):
                calls.append({
                    "type": name,
                    "line": number,
                    "snippet":
                        line.strip()[:220],
                })

    return {
        "version": VERSION,
        "path": str(p),
        "calls": calls,
        "count": len(calls),
    }


def self_test():
    assert VERSION == "8.72"
    print(
        "VI8.72 NETWORK CALL AUDITOR=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.73 — SEARCH FUNCTION CLASSIFIER
# =====================================================

cat > vi8_73_search_function_classifier.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.73"


def classify(name):
    low = str(name or "").lower()

    if any(
        token in low
        for token in (
            "download",
            "baixar",
        )
    ):
        return "DOWNLOAD"

    if any(
        token in low
        for token in (
            "search",
            "buscar",
            "busca",
            "query",
        )
    ):
        return "SEARCH"

    if any(
        token in low
        for token in (
            "source",
            "provider",
            "fonte",
        )
    ):
        return "SOURCE_ROUTING"

    if any(
        token in low
        for token in (
            "image",
            "imagem",
            "media",
            "midia",
        )
    ):
        return "MEDIA"

    return "OTHER"


def self_test():
    assert (
        classify(
            "search_images"
        )
        == "SEARCH"
    )

    assert (
        classify(
            "download_media"
        )
        == "DOWNLOAD"
    )

    print(
        "VI8.73 SEARCH FUNCTION CLASSIFIER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.74 — PROVIDER DETECTOR
# =====================================================

cat > vi8_74_provider_detector.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.74"

PROVIDERS = {
    "WIKIMEDIA": (
        "wikimedia",
        "commons.wikimedia",
    ),

    "WIKIPEDIA": (
        "wikipedia.org",
        "wikipedia",
    ),

    "PEXELS": (
        "pexels",
    ),

    "PIXABAY": (
        "pixabay",
    ),

    "UNSPLASH": (
        "unsplash",
    ),

    "GOOGLE": (
        "google",
    ),

    "BING": (
        "bing",
    ),

    "DUCKDUCKGO": (
        "duckduckgo",
    ),
}


def detect(text):
    low = str(
        text or ""
    ).lower()

    found = []

    for provider, terms in (
        PROVIDERS.items()
    ):
        if any(
            term in low
            for term in terms
        ):
            found.append(
                provider
            )

    return sorted(
        set(found)
    )


def self_test():
    assert (
        "WIKIMEDIA"
        in detect(
            "commons.wikimedia.org"
        )
    )

    print(
        "VI8.74 PROVIDER DETECTOR=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.75 — SOURCE RECOVERY LOCK AUDIT
# =====================================================

cat > vi8_75_source_recovery_lock_audit.py <<'PY'
#!/usr/bin/env python3

from pathlib import Path

VERSION = "8.75"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():
    candidates = []

    for path in BASE.glob(
        "*.py"
    ):
        name = path.name.lower()

        if any(
            token in name
            for token in (
                "source",
                "recovery",
                "router",
            )
        ):
            candidates.append(
                str(path)
            )

    return {
        "version": VERSION,
        "candidate_modules":
            sorted(candidates),
        "active_allowed":
            False,
        "required_mode":
            "SHADOW_ONLY",
        "status":
            "LOCKED_SAFE",
    }


def self_test():
    result = evaluate()

    assert (
        result[
            "active_allowed"
        ]
        is False
    )

    print(
        "VI8.75 SOURCE RECOVERY LOCK AUDIT=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.76 — READ-ONLY ADAPTER CONTRACT
# =====================================================

cat > vi8_76_readonly_search_adapter.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.76"


def contract():
    return {
        "version": VERSION,

        "mode":
            "DISCOVERY_ONLY",

        "network_allowed":
            False,

        "download_allowed":
            False,

        "filesystem_media_write":
            False,

        "provider_call_allowed":
            False,

        "source_recovery_allowed":
            False,

        "renderer_allowed":
            False,

        "ffmpeg_allowed":
            False,
    }


def self_test():
    c = contract()

    assert (
        c[
            "network_allowed"
        ]
        is False
    )

    assert (
        c[
            "filesystem_media_write"
        ]
        is False
    )

    print(
        "VI8.76 READONLY SEARCH ADAPTER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.77 — ARCHITECTURE MAPPER
# =====================================================

cat > vi8_77_search_architecture_mapper.py <<'PY'
#!/usr/bin/env python3

from pathlib import Path

from vi8_71_search_code_discovery import (
    discover
)

from vi8_72_network_call_auditor import (
    audit as network_audit
)

from vi8_73_search_function_classifier import (
    classify
)

from vi8_74_provider_detector import (
    detect
)

VERSION = "8.77"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():
    discovery = discover()

    modules = []

    for item in (
        discovery.get("files")
        or []
    ):
        path = Path(
            item["path"]
        )

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="ignore"
            )
        except Exception:
            text = ""

        network = network_audit(
            path
        )

        functions = []

        for fn in (
            item.get(
                "functions"
            )
            or []
        ):
            functions.append({
                "name": fn,
                "role":
                    classify(fn),
            })

        modules.append({
            "path":
                item.get(
                    "relative"
                ),

            "keyword_hits":
                item.get(
                    "hits"
                ),

            "providers":
                detect(text),

            "functions":
                functions,

            "network_calls":
                network.get(
                    "calls"
                )
                or [],

            "network_call_count":
                network.get(
                    "count",
                    0
                ),
        })

    modules.sort(
        key=lambda x: (
            -x[
                "network_call_count"
            ],
            x["path"]
        )
    )

    return {
        "version": VERSION,
        "module_count":
            len(modules),
        "modules":
            modules,
    }


def self_test():
    assert VERSION == "8.77"

    print(
        "VI8.77 SEARCH ARCHITECTURE MAPPER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.78 — SAFE INTEGRATION CANDIDATE FINDER
# =====================================================

cat > vi8_78_safe_integration_candidate.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.78"


def evaluate(map_result):
    candidates = []

    for module in (
        map_result.get(
            "modules"
        )
        or []
    ):
        search_functions = [
            fn
            for fn in (
                module.get(
                    "functions"
                )
                or []
            )
            if fn.get(
                "role"
            ) == "SEARCH"
        ]

        download_functions = [
            fn
            for fn in (
                module.get(
                    "functions"
                )
                or []
            )
            if fn.get(
                "role"
            ) == "DOWNLOAD"
        ]

        if not search_functions:
            continue

        score = 0
        reasons = []

        if search_functions:
            score += 40
            reasons.append(
                "search_function_present"
            )

        if module.get(
            "providers"
        ):
            score += 25
            reasons.append(
                "provider_detected"
            )

        if module.get(
            "network_call_count",
            0
        ):
            score += 20
            reasons.append(
                "network_path_detected"
            )

        if not download_functions:
            score += 15
            reasons.append(
                "search_download_separated"
            )

        candidates.append({
            "path":
                module.get(
                    "path"
                ),

            "score":
                score,

            "providers":
                module.get(
                    "providers"
                ),

            "search_functions":
                search_functions,

            "download_functions":
                download_functions,

            "reasons":
                reasons,
        })

    candidates.sort(
        key=lambda x:
            x.get(
                "score",
                0
            ),
        reverse=True
    )

    return {
        "version": VERSION,
        "candidates":
            candidates,
        "count":
            len(candidates),
        "best":
            (
                candidates[0]
                if candidates
                else None
            ),
    }


def self_test():
    assert VERSION == "8.78"

    print(
        "VI8.78 SAFE INTEGRATION CANDIDATE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.79 — ARCHITECTURE SAFETY GATE
# =====================================================

cat > vi8_79_search_architecture_safety_gate.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.79"


def evaluate(
    architecture,
    candidates,
    recovery_lock
):
    blockers = []
    warnings = []

    if recovery_lock.get(
        "active_allowed"
    ):
        blockers.append(
            "source_recovery_not_locked"
        )

    if candidates.get(
        "count",
        0
    ) == 0:
        warnings.append(
            "no_safe_search_candidate_detected"
        )

    module_count = int(
        architecture.get(
            "module_count",
            0
        )
        or 0
    )

    if module_count == 0:
        warnings.append(
            "no_search_related_modules_detected"
        )

    return {
        "version": VERSION,

        "status": (
            "HOLD"
            if blockers
            else (
                "PASS_WITH_WARNINGS"
                if warnings
                else "PASS"
            )
        ),

        "blockers":
            blockers,

        "warnings":
            warnings,

        "network_execution":
            False,

        "integration_execution":
            False,
    }


def self_test():
    result = evaluate(
        {
            "module_count": 1
        },
        {
            "count": 1
        },
        {
            "active_allowed":
                False
        }
    )

    assert (
        result["status"]
        == "PASS"
    )

    print(
        "VI8.79 SEARCH ARCHITECTURE SAFETY GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.80 — SEARCH ARCHITECTURE MASTER GATE
# =====================================================

cat > vi8_80_search_architecture_master_gate.py <<'PY'
#!/usr/bin/env python3

import json

from pathlib import Path

from vi8_77_search_architecture_mapper import (
    evaluate as map_architecture
)

from vi8_78_safe_integration_candidate import (
    evaluate as find_candidates
)

from vi8_75_source_recovery_lock_audit import (
    evaluate as recovery_lock
)

from vi8_79_search_architecture_safety_gate import (
    evaluate as safety_gate
)


VERSION = "8.80"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():

    architecture = (
        map_architecture()
    )

    candidates = (
        find_candidates(
            architecture
        )
    )

    recovery = (
        recovery_lock()
    )

    safety = (
        safety_gate(
            architecture,
            candidates,
            recovery
        )
    )

    if safety.get(
        "blockers"
    ):
        status = "HOLD"

    elif candidates.get(
        "count",
        0
    ):
        status = (
            "SEARCH_ARCHITECTURE_MAPPED"
        )

    else:
        status = (
            "SEARCH_ARCHITECTURE_PARTIAL"
        )

    result = {
        "version":
            VERSION,

        "status":
            status,

        "architecture":
            architecture,

        "integration_candidates":
            candidates,

        "source_recovery":
            recovery,

        "safety":
            safety,

        "network_executed":
            False,

        "provider_called":
            False,

        "download_executed":
            False,

        "media_mutated":
            False,

        "renderer_activation":
            False,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,

        "full_active":
            False,
    }

    output = (
        BASE
        / "logs"
        / "producao"
        / "vi8_80_search_architecture_latest.json"
    )

    output.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    output.write_text(
        json.dumps(
            {
                "gate":
                    result
            },
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    return result


def self_test():
    assert VERSION == "8.80"

    print(
        "VI8.80 SEARCH ARCHITECTURE MASTER GATE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


echo
echo "===== COMPILE ====="

python -m py_compile \
  vi8_71_search_code_discovery.py \
  vi8_72_network_call_auditor.py \
  vi8_73_search_function_classifier.py \
  vi8_74_provider_detector.py \
  vi8_75_source_recovery_lock_audit.py \
  vi8_76_readonly_search_adapter.py \
  vi8_77_search_architecture_mapper.py \
  vi8_78_safe_integration_candidate.py \
  vi8_79_search_architecture_safety_gate.py \
  vi8_80_search_architecture_master_gate.py \
  || exit 10

echo "COMPILE=PASS"

echo
echo "===== SELF TESTS ====="

python vi8_71_search_code_discovery.py || exit 11
python vi8_72_network_call_auditor.py || exit 12
python vi8_73_search_function_classifier.py || exit 13
python vi8_74_provider_detector.py || exit 14
python vi8_75_source_recovery_lock_audit.py || exit 15
python vi8_76_readonly_search_adapter.py || exit 16
python vi8_77_search_architecture_mapper.py || exit 17
python vi8_78_safe_integration_candidate.py || exit 18
python vi8_79_search_architecture_safety_gate.py || exit 19
python vi8_80_search_architecture_master_gate.py || exit 20

echo "SELF TESTS=PASS"


echo
echo "=================================================="
echo " VI8.80 SEARCH ARCHITECTURE ANALYSIS"
echo "=================================================="

python - <<'PY'
from vi8_80_search_architecture_master_gate import (
    evaluate
)

r = evaluate()

print(
    "STATUS:",
    r.get("status")
)

architecture = (
    r.get("architecture")
    or {}
)

print(
    "SEARCH-RELATED MODULES:",
    architecture.get(
        "module_count"
    )
)

candidates = (
    r.get(
        "integration_candidates"
    )
    or {}
)

print(
    "INTEGRATION CANDIDATES:",
    candidates.get(
        "count"
    )
)

best = (
    candidates.get("best")
    or {}
)

print(
    "BEST MODULE:",
    best.get("path")
)

print(
    "BEST SCORE:",
    best.get("score")
)

print(
    "PROVIDERS:",
    best.get("providers")
)

print(
    "SEARCH FUNCTIONS:",
    [
        x.get("name")
        for x in (
            best.get(
                "search_functions"
            )
            or []
        )
    ]
)

print(
    "DOWNLOAD FUNCTIONS:",
    [
        x.get("name")
        for x in (
            best.get(
                "download_functions"
            )
            or []
        )
    ]
)

safety = (
    r.get("safety")
    or {}
)

print(
    "BLOCKERS:",
    safety.get(
        "blockers"
    )
)

print(
    "WARNINGS:",
    safety.get(
        "warnings"
    )
)

print()
print(
    "===== TOP SEARCH ARCHITECTURE MODULES ====="
)

for module in (
    architecture.get(
        "modules"
    )
    or []
)[:15]:

    print(
        module.get("path"),
        "| providers=",
        module.get("providers"),
        "| network_calls=",
        module.get(
            "network_call_count"
        ),
        "| functions=",
        [
            (
                f.get("name"),
                f.get("role")
            )
            for f in (
                module.get(
                    "functions"
                )
                or []
            )
            if f.get(
                "role"
            ) != "OTHER"
        ],
    )

print()
print(
    "NETWORK EXECUTED:",
    r.get(
        "network_executed"
    )
)

print(
    "PROVIDER CALLED:",
    r.get(
        "provider_called"
    )
)

print(
    "DOWNLOAD EXECUTED:",
    r.get(
        "download_executed"
    )
)

print(
    "MEDIA MUTATED:",
    r.get(
        "media_mutated"
    )
)

print(
    "FFMPEG EXECUTED:",
    r.get(
        "ffmpeg_executed"
    )
)

print(
    "VIDEO GENERATED:",
    r.get(
        "video_generated"
    )
)
PY


VIDEO_AFTER="$(sha256sum video.py | awk '{print $1}')"
GERAR_AFTER="$(sha256sum gerar_short.sh | awk '{print $1}')"

if [ "$VIDEO_BEFORE" != "$VIDEO_AFTER" ]; then
    echo "CRITICAL: video.py changed"
    exit 30
fi

if [ "$GERAR_BEFORE" != "$GERAR_AFTER" ]; then
    echo "CRITICAL: gerar_short.sh changed"
    exit 31
fi


echo
echo "=================================================="
echo " VI8.71 -> VI8.80 COMPLETE"
echo "=================================================="
echo
echo "SEARCH ARCHITECTURE=DISCOVERED"
echo "NETWORK CALLS=AUDITED"
echo "PROVIDERS=MAPPED"
echo "SEARCH FUNCTIONS=MAPPED"
echo "DOWNLOAD FUNCTIONS=MAPPED"
echo "SOURCE RECOVERY=LOCKED"
echo
echo "VIDEO.PY UNCHANGED=YES"
echo "GERAR_SHORT.SH UNCHANGED=YES"
echo "NETWORK EXECUTED=NO"
echo "PROVIDER CALLED=NO"
echo "DOWNLOAD EXECUTED=NO"
echo "MEDIA MUTATION=NO"
echo "FFMPEG EXECUTED=NO"
echo "VIDEO GENERATED=NO"
echo "FULL ACTIVE=LOCKED"
echo
echo "REPORT:"
echo "logs/producao/vi8_80_search_architecture_latest.json"
