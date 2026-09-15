#!/data/data/com.termux/files/usr/bin/bash
set -u
cd "$HOME/ShortAutoPro" || exit 1

cat > vi7_31_visual_ontology.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.31"

RULES = {
    "FACE": (
        "portrait","girl","boy","woman","man","father",
        "mother","person","face","child"
    ),
    "DOCUMENT": (
        "document","letter","note","paper","newspaper",
        "clipping","passport","file","archive","calendar"
    ),
    "EVIDENCE": (
        "evidence","dna","cash","money","weapon",
        "forensic","crime scene","police tape"
    ),
    "LOCATION": (
        "house","building","street","basement",
        "corridor","hallway","room","city",
        "landscape","exterior","interior"
    ),
    "OBJECT": (
        "object","microphone","phone","camera",
        "equipment","notepad"
    ),
}

def classify(scene):
    text = " ".join(
        str(scene.get(k) or "")
        for k in (
            "segment","query","visual_mode","shot_type"
        )
    ).lower()

    scores = {
        category: sum(
            1 for token in tokens
            if token in text
        )
        for category, tokens in RULES.items()
    }

    best = max(scores, key=scores.get)

    if scores[best] == 0:
        mode = str(
            scene.get("visual_mode") or ""
        ).lower()

        fallback = {
            "document": "DOCUMENT",
            "evidence": "EVIDENCE",
            "location": "LOCATION",
            "architecture": "LOCATION",
            "object": "OBJECT",
            "abstract_context": "ABSTRACT",
        }

        return fallback.get(
            mode,
            "GENERAL"
        )

    return best

def self_test():
    assert classify({
        "query": "handwritten ransom note paper"
    }) == "DOCUMENT"

    assert classify({
        "query": "young girl portrait"
    }) == "FACE"

    print("VI7.31 VISUAL ONTOLOGY=PASS")

if __name__ == "__main__":
    self_test()
PY


cat > vi7_34_shot_language.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.34"

PREFERRED = {
    "FACE": ("medium","close_up"),
    "DOCUMENT": ("close_up","medium"),
    "EVIDENCE": ("close_up","medium"),
    "LOCATION": ("wide","medium"),
    "OBJECT": ("close_up","medium"),
    "ABSTRACT": ("medium","wide"),
    "GENERAL": ("medium",),
}

def normalize(value):
    value = str(value or "").lower().strip()

    aliases = {
        "closeup": "close_up",
        "close-up": "close_up",
        "close": "close_up",
    }

    return aliases.get(
        value,
        value
    )

def evaluate(category, shot):
    shot = normalize(shot)

    preferred = PREFERRED.get(
        category,
        ("medium",)
    )

    return {
        "version": VERSION,
        "category": category,
        "shot": shot,
        "preferred": preferred,
        "match": shot in preferred,
    }

def self_test():
    assert evaluate(
        "LOCATION",
        "wide"
    )["match"]

    print("VI7.34 SHOT LANGUAGE=PASS")

if __name__ == "__main__":
    self_test()
PY


cat > vi7_37_motion_safety.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.37"

SAFE = {
    "FACE": (
        "FACE_SAFE_PUSH",
        "SLOW_PUSH",
        "MICRO_HOLD",
    ),
    "DOCUMENT": (
        "DOCUMENT_SCAN",
        "SLOW_PUSH",
        "DETAIL_PUSH",
    ),
    "EVIDENCE": (
        "DETAIL_PUSH",
        "MICRO_DISCOVERY",
        "SLOW_PUSH",
    ),
    "LOCATION": (
        "HORIZONTAL_DISCOVERY",
        "ARCHITECTURE_DRIFT",
        "SLOW_PUSH",
    ),
    "OBJECT": (
        "DETAIL_PUSH",
        "MICRO_DISCOVERY",
        "SLOW_PUSH",
    ),
    "ABSTRACT": (
        "SLOW_PUSH",
        "REVERSE_DRIFT",
        "MICRO_HOLD",
    ),
    "GENERAL": (
        "SLOW_PUSH",
        "DETAIL_PUSH",
        "HORIZONTAL_DISCOVERY",
    ),
}

def profiles(category):
    return SAFE.get(
        category,
        SAFE["GENERAL"]
    )

def self_test():
    assert (
        "FACE_SAFE_PUSH"
        in profiles("FACE")
    )

    assert (
        "HORIZONTAL_DISCOVERY"
        not in profiles("FACE")
    )

    print("VI7.37 MOTION SAFETY=PASS")

if __name__ == "__main__":
    self_test()
PY


cat > vi7_40_visual_repetition.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.40"

def detect(sequence):
    warnings = []

    categories = [
        x.get("category")
        for x in sequence
    ]

    shots = [
        x.get("shot")
        for x in sequence
    ]

    for index in range(
        len(sequence) - 2
    ):
        c = categories[index:index+3]
        s = shots[index:index+3]

        if len(set(c)) == 1 and c[0]:
            warnings.append({
                "type": "category_triple",
                "scenes": [
                    sequence[index+j]["scene"]
                    for j in range(3)
                ],
                "value": c[0],
            })

        if len(set(s)) == 1 and s[0]:
            warnings.append({
                "type": "shot_triple",
                "scenes": [
                    sequence[index+j]["scene"]
                    for j in range(3)
                ],
                "value": s[0],
            })

    return {
        "version": VERSION,
        "warnings": warnings,
        "count": len(warnings),
    }

def self_test():
    sample = [
        {
            "scene": 1,
            "category": "DOCUMENT",
            "shot": "medium",
        },
        {
            "scene": 2,
            "category": "DOCUMENT",
            "shot": "medium",
        },
        {
            "scene": 3,
            "category": "DOCUMENT",
            "shot": "medium",
        },
    ]

    assert detect(sample)["count"] == 2

    print("VI7.40 VISUAL REPETITION=PASS")

if __name__ == "__main__":
    self_test()
PY


cat > vi7_43_narrative_energy.py <<'PY'
#!/usr/bin/env python3

VERSION = "7.43"

def energy(scene):
    if scene == 1:
        return 3

    if scene in {2,3}:
        return 2

    if scene in {4,5,6,7,8}:
        return 1

    if scene in {9,10,11}:
        return 3

    if scene == 12:
        return 0

    return 1

def role(scene):
    if scene == 1:
        return "HOOK"

    if scene == 12:
        return "CTA"

    if scene in {9,10,11}:
        return "CLIMAX"

    return "CONTEXT"

def self_test():
    assert energy(10) == 3
    assert energy(12) == 0

    print("VI7.43 NARRATIVE ENERGY=PASS")

if __name__ == "__main__":
    self_test()
PY


python -m py_compile \
  vi7_31_visual_ontology.py \
  vi7_34_shot_language.py \
  vi7_37_motion_safety.py \
  vi7_40_visual_repetition.py \
  vi7_43_narrative_energy.py || exit 1

python vi7_31_visual_ontology.py || exit 1
python vi7_34_shot_language.py || exit 1
python vi7_37_motion_safety.py || exit 1
python vi7_40_visual_repetition.py || exit 1
python vi7_43_narrative_energy.py || exit 1

echo
echo "======================================"
echo " VI8 BLOCK 1/4 COMPLETE"
echo "======================================"
echo "VIDEO GENERATED=NO"
echo "FFMPEG EXECUTED=NO"
echo "RENDERER MODIFIED=NO"
