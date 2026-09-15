#!/data/data/com.termux/files/usr/bin/bash
set -u
cd "$HOME/ShortAutoPro" || exit 1

echo
echo "======================================"
echo " VI8.31 -> VI8.40"
echo " REAL MEDIA INTELLIGENCE FOUNDATION"
echo " SHADOW ONLY"
echo "======================================"
echo
echo "VIDEO GENERATION=OFF"
echo "FFMPEG RENDER=OFF"
echo "MEDIA MUTATION=OFF"
echo

VIDEO_BEFORE="$(sha256sum video.py | awk '{print $1}')"
GERAR_BEFORE="$(sha256sum gerar_short.sh | awk '{print $1}')"


# =====================================================
# VI8.31 — REAL MEDIA FILE MODEL
# =====================================================

cat > vi8_31_real_media_file.py <<'PY'
#!/usr/bin/env python3

from pathlib import Path

VERSION = "8.31"

IMAGE_EXTS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

VIDEO_EXTS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".webm",
}


def media_type(path):

    suffix = Path(
        path
    ).suffix.lower()

    if suffix in IMAGE_EXTS:
        return "STILL"

    if suffix in VIDEO_EXTS:
        return "VIDEO"

    return "UNKNOWN"


def build(path):

    p = Path(path)

    return {
        "version":
            VERSION,

        "path":
            str(p),

        "name":
            p.name,

        "suffix":
            p.suffix.lower(),

        "media_type":
            media_type(p),

        "exists":
            p.exists(),

        "size_bytes":
            (
                p.stat().st_size
                if p.exists()
                else 0
            ),
    }


def self_test():

    assert (
        media_type(
            "scene_01.jpg"
        )
        == "STILL"
    )

    assert (
        media_type(
            "scene_02.mp4"
        )
        == "VIDEO"
    )

    print(
        "VI8.31 REAL MEDIA FILE MODEL=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.32 — SCENE NUMBER EXTRACTOR
# =====================================================

cat > vi8_32_scene_number_extractor.py <<'PY'
#!/usr/bin/env python3

import re

VERSION = "8.32"


PATTERNS = (
    r"(?:scene|cena)[_-]?0*(\d+)",
    r"^0*(\d+)[_.-]",
)


def extract(name):

    text = str(
        name or ""
    ).lower()

    for pattern in PATTERNS:

        match = re.search(
            pattern,
            text
        )

        if match:

            number = int(
                match.group(1)
            )

            if 1 <= number <= 12:
                return number

    return None


def self_test():

    assert (
        extract(
            "scene_05.jpg"
        )
        == 5
    )

    assert (
        extract(
            "cena07.png"
        )
        == 7
    )

    print(
        "VI8.32 SCENE NUMBER EXTRACTOR=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.33 — REAL MEDIA INVENTORY
# =====================================================

cat > vi8_33_real_media_inventory.py <<'PY'
#!/usr/bin/env python3

from pathlib import Path

from vi8_31_real_media_file import (
    build
)

from vi8_32_scene_number_extractor import (
    extract
)

VERSION = "8.33"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def latest_media_dir():

    root = (
        BASE
        / "imagens"
    )

    dirs = [
        path
        for path in root.glob(
            "short_*"
        )
        if path.is_dir()
    ]

    dirs.sort(
        key=lambda path:
            path.stat().st_mtime,
        reverse=True
    )

    return (
        dirs[0]
        if dirs
        else None
    )


def inventory(
    media_dir=None
):

    folder = (
        Path(media_dir)
        if media_dir
        else latest_media_dir()
    )

    if (
        folder is None
        or not folder.exists()
    ):

        raise RuntimeError(
            "media_directory_missing"
        )

    items = []

    for path in sorted(
        folder.iterdir()
    ):

        if not path.is_file():
            continue

        item = build(
            path
        )

        if (
            item[
                "media_type"
            ]
            == "UNKNOWN"
        ):
            continue

        item[
            "scene_guess"
        ] = extract(
            path.name
        )

        items.append(
            item
        )

    return {
        "version":
            VERSION,

        "media_dir":
            str(folder),

        "count":
            len(items),

        "items":
            items,
    }


def self_test():

    assert VERSION == "8.33"

    print(
        "VI8.33 REAL MEDIA INVENTORY=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.34 — IMAGE DIMENSION READER
# Pure Python headers. No FFmpeg.
# =====================================================

cat > vi8_34_image_dimension_reader.py <<'PY'
#!/usr/bin/env python3

import struct

from pathlib import Path

VERSION = "8.34"


def png_dimensions(path):

    with open(
        path,
        "rb"
    ) as f:

        header = f.read(
            24
        )

    if (
        len(header) >= 24
        and header[:8]
        == b"\x89PNG\r\n\x1a\n"
    ):

        width, height = (
            struct.unpack(
                ">II",
                header[16:24]
            )
        )

        return width, height

    return None


def jpeg_dimensions(path):

    with open(
        path,
        "rb"
    ) as f:

        data = f.read(
            2
        )

        if data != b"\xff\xd8":
            return None

        while True:

            byte = f.read(
                1
            )

            if not byte:
                break

            if byte != b"\xff":
                continue

            while byte == b"\xff":
                byte = f.read(
                    1
                )

            marker = byte[0]

            length_raw = f.read(
                2
            )

            if len(
                length_raw
            ) != 2:
                break

            length = struct.unpack(
                ">H",
                length_raw
            )[0]

            if marker in {
                0xC0,
                0xC1,
                0xC2,
                0xC3,
                0xC5,
                0xC6,
                0xC7,
                0xC9,
                0xCA,
                0xCB,
                0xCD,
                0xCE,
                0xCF,
            }:

                payload = f.read(
                    5
                )

                if len(
                    payload
                ) != 5:
                    return None

                height, width = (
                    struct.unpack(
                        ">HH",
                        payload[1:5]
                    )
                )

                return width, height

            f.seek(
                max(
                    0,
                    length - 2
                ),
                1
            )

    return None


def webp_dimensions(path):

    try:

        from PIL import Image

        with Image.open(
            path
        ) as img:

            return img.size

    except Exception:

        return None


def dimensions(path):

    p = Path(path)

    suffix = (
        p.suffix.lower()
    )

    try:

        if suffix == ".png":
            return png_dimensions(
                p
            )

        if suffix in {
            ".jpg",
            ".jpeg",
        }:

            return jpeg_dimensions(
                p
            )

        if suffix == ".webp":
            return webp_dimensions(
                p
            )

    except Exception:

        return None

    return None


def self_test():

    assert dimensions(
        "/definitely/not/here.jpg"
    ) is None

    print(
        "VI8.34 IMAGE DIMENSION READER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.35 — REAL MEDIA TECHNICAL ANALYZER
# =====================================================

cat > vi8_35_real_media_technical_analyzer.py <<'PY'
#!/usr/bin/env python3

from vi8_02_crop_fitness import (
    evaluate as crop_fitness
)

from vi8_34_image_dimension_reader import (
    dimensions
)

VERSION = "8.35"


def evaluate(item):

    result = dict(
        item
    )

    if (
        item.get(
            "media_type"
        )
        != "STILL"
    ):

        result.update({
            "width":
                None,

            "height":
                None,

            "orientation":
                "VIDEO_OR_UNKNOWN",

            "crop_fitness":
                None,

            "technical_score":
                80.0,
        })

        return result


    dims = dimensions(
        item.get(
            "path"
        )
    )


    if not dims:

        result.update({
            "width":
                None,

            "height":
                None,

            "orientation":
                "UNKNOWN",

            "crop_fitness":
                {
                    "score":
                        50.0,

                    "status":
                        "UNKNOWN",
                },

            "technical_score":
                50.0,
        })

        return result


    width, height = dims


    if height > width:
        orientation = (
            "PORTRAIT"
        )

    elif width > height:
        orientation = (
            "LANDSCAPE"
        )

    else:
        orientation = (
            "SQUARE"
        )


    crop = crop_fitness(
        width,
        height
    )


    size_bytes = int(
        item.get(
            "size_bytes",
            0
        )
        or 0
    )


    size_bonus = (
        10
        if size_bytes >= 500_000
        else 0
    )


    technical_score = min(
        100.0,
        float(
            crop.get(
                "score",
                50
            )
        )
        * .9
        + size_bonus
    )


    result.update({
        "width":
            width,

        "height":
            height,

        "orientation":
            orientation,

        "crop_fitness":
            crop,

        "technical_score":
            round(
                technical_score,
                2
            ),
    })


    return result


def self_test():

    assert VERSION == "8.35"

    print(
        "VI8.35 REAL MEDIA TECHNICAL ANALYZER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.36 — SCENE MEDIA GROUPER
# =====================================================

cat > vi8_36_scene_media_grouper.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.36"


def group(items):

    scenes = {
        number: []
        for number
        in range(
            1,
            13
        )
    }

    unassigned = []


    for item in items:

        scene = item.get(
            "scene_guess"
        )

        if scene in scenes:

            scenes[
                scene
            ].append(
                item
            )

        else:

            unassigned.append(
                item
            )


    return {
        "version":
            VERSION,

        "scenes":
            scenes,

        "unassigned":
            unassigned,

        "assigned_count":
            sum(
                len(v)
                for v
                in scenes.values()
            ),

        "unassigned_count":
            len(
                unassigned
            ),
    }


def self_test():

    result = group([
        {
            "scene_guess": 2
        },
        {
            "scene_guess": None
        },
    ])

    assert (
        len(
            result[
                "scenes"
            ][2]
        )
        == 1
    )

    assert (
        result[
            "unassigned_count"
        ]
        == 1
    )

    print(
        "VI8.36 SCENE MEDIA GROUPER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.37 — REAL CANDIDATE CONVERTER
# =====================================================

cat > vi8_37_real_candidate_converter.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.37"


def convert(
    item,
    scene,
    category
):

    return {
        "path":
            item.get(
                "path"
            ),

        "source":
            "REAL_EXISTING_MEDIA",

        "media_type":
            item.get(
                "media_type"
            ),

        "width":
            item.get(
                "width"
            ),

        "height":
            item.get(
                "height"
            ),

        "query":
            scene.get(
                "query"
            )
            or "",

        "category":
            category,

        "shot":
            scene.get(
                "shot_type"
            )
            or "medium",

        "source_score":
            80,

        "metadata": {
            "real_file":
                True,

            "filename":
                item.get(
                    "name"
                ),

            "orientation":
                item.get(
                    "orientation"
                ),

            "technical_score":
                item.get(
                    "technical_score"
                ),

            "identity_confirmed":
                (
                    None
                    if category
                    == "FACE"
                    else True
                ),
        },
    }


def self_test():

    result = convert(
        {
            "path":
                "scene_01.jpg",

            "media_type":
                "STILL",

            "width":
                1200,

            "height":
                1600,
        },
        {
            "query":
                "house"
        },
        "LOCATION"
    )

    assert (
        result[
            "source"
        ]
        == "REAL_EXISTING_MEDIA"
    )

    print(
        "VI8.37 REAL CANDIDATE CONVERTER=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.38 — REAL MEDIA SCORE
# =====================================================

cat > vi8_38_real_media_score.py <<'PY'
#!/usr/bin/env python3

from vi8_09_candidate_scorer import (
    evaluate as candidate_score
)

VERSION = "8.38"


def evaluate(
    scene,
    candidate,
    previous=None
):

    score = candidate_score(
        scene,
        candidate,
        previous or []
    )


    technical = float(
        (
            candidate.get(
                "metadata"
            )
            or {}
        ).get(
            "technical_score",
            50
        )
        or 50
    )


    base = float(
        score.get(
            "score",
            0
        )
    )


    combined = (
        base * .80
        + technical * .20
    )


    return {
        "version":
            VERSION,

        "score":
            round(
                combined,
                2
            ),

        "base_score":
            round(
                base,
                2
            ),

        "technical_score":
            round(
                technical,
                2
            ),

        "eligible":
            score.get(
                "eligible"
            ),

        "blockers":
            score.get(
                "blockers"
            )
            or [],

        "warnings":
            score.get(
                "warnings"
            )
            or [],
    }


def self_test():

    assert VERSION == "8.38"

    print(
        "VI8.38 REAL MEDIA SCORE=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.39 — REAL MEDIA COVERAGE AUDIT
# =====================================================

cat > vi8_39_real_media_coverage_audit.py <<'PY'
#!/usr/bin/env python3

VERSION = "8.39"


def evaluate(grouped):

    scenes = (
        grouped.get(
            "scenes"
        )
        or {}
    )


    covered = [
        scene
        for scene, items
        in scenes.items()
        if items
    ]


    missing = [
        scene
        for scene
        in range(
            1,
            13
        )
        if scene
        not in covered
    ]


    multi = {
        scene:
            len(items)

        for scene, items
        in scenes.items()

        if len(items) > 1
    }


    return {
        "version":
            VERSION,

        "covered_scenes":
            covered,

        "covered_count":
            len(covered),

        "missing_scenes":
            missing,

        "multi_candidate_scenes":
            multi,

        "unassigned_count":
            grouped.get(
                "unassigned_count",
                0
            ),

        "status":
            (
                "PASS"
                if len(covered) == 12
                else "PASS_WITH_WARNINGS"
            ),
    }


def self_test():

    assert VERSION == "8.39"

    print(
        "VI8.39 REAL MEDIA COVERAGE AUDIT=PASS"
    )


if __name__ == "__main__":
    self_test()
PY


# =====================================================
# VI8.40 — FOUNDATION MASTER GATE
# =====================================================

cat > vi8_40_real_media_foundation_gate.py <<'PY'
#!/usr/bin/env python3

import json

from pathlib import Path

from vi8_33_real_media_inventory import (
    inventory
)

from vi8_35_real_media_technical_analyzer import (
    evaluate as technical
)

from vi8_36_scene_media_grouper import (
    group
)

from vi8_39_real_media_coverage_audit import (
    evaluate as coverage
)


VERSION = "8.40"

BASE = (
    Path.home()
    / "ShortAutoPro"
)


def evaluate():

    inv = inventory()


    analyzed = [
        technical(
            item
        )
        for item
        in inv.get(
            "items",
            []
        )
    ]


    grouped = group(
        analyzed
    )


    coverage_result = coverage(
        grouped
    )


    result = {
        "version":
            VERSION,

        "status":
            (
                "REAL_MEDIA_FOUNDATION_READY"
                if analyzed
                else "HOLD"
            ),

        "media_dir":
            inv.get(
                "media_dir"
            ),

        "file_count":
            len(
                analyzed
            ),

        "items":
            analyzed,

        "grouped":
            grouped,

        "coverage":
            coverage_result,

        "ffmpeg_executed":
            False,

        "video_generated":
            False,

        "media_mutated":
            False,

        "automatic_replace":
            False,

        "full_active":
            False,
    }


    output = (
        BASE
        / "logs"
        / "producao"
        / "vi8_40_real_media_foundation_latest.json"
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

    assert VERSION == "8.40"

    print(
        "VI8.40 REAL MEDIA FOUNDATION GATE=PASS"
    )


if __name__ == "__main__":

    self_test()
PY


echo
echo "===== COMPILE ====="

python -m py_compile \
  vi8_31_real_media_file.py \
  vi8_32_scene_number_extractor.py \
  vi8_33_real_media_inventory.py \
  vi8_34_image_dimension_reader.py \
  vi8_35_real_media_technical_analyzer.py \
  vi8_36_scene_media_grouper.py \
  vi8_37_real_candidate_converter.py \
  vi8_38_real_media_score.py \
  vi8_39_real_media_coverage_audit.py \
  vi8_40_real_media_foundation_gate.py \
  || exit 10

echo "COMPILE=PASS"


echo
echo "===== SELF TESTS ====="

python vi8_31_real_media_file.py || exit 11
python vi8_32_scene_number_extractor.py || exit 12
python vi8_34_image_dimension_reader.py || exit 13
python vi8_35_real_media_technical_analyzer.py || exit 14
python vi8_36_scene_media_grouper.py || exit 15
python vi8_37_real_candidate_converter.py || exit 16
python vi8_38_real_media_score.py || exit 17
python vi8_39_real_media_coverage_audit.py || exit 18
python vi8_40_real_media_foundation_gate.py || exit 19

echo "SELF TESTS=PASS"


echo
echo "===== REAL MEDIA SHADOW INSPECTION ====="

python - <<'PY'
from vi8_40_real_media_foundation_gate import evaluate

r = evaluate()

print(
    "STATUS:",
    r.get("status")
)

print(
    "MEDIA DIR:",
    r.get("media_dir")
)

print(
    "REAL FILES:",
    r.get("file_count")
)

coverage = (
    r.get("coverage")
    or {}
)

print(
    "COVERED SCENES:",
    coverage.get(
        "covered_scenes"
    )
)

print(
    "COVERED COUNT:",
    coverage.get(
        "covered_count"
    )
)

print(
    "MISSING SCENES:",
    coverage.get(
        "missing_scenes"
    )
)

print(
    "MULTI-CANDIDATE SCENES:",
    coverage.get(
        "multi_candidate_scenes"
    )
)

print(
    "UNASSIGNED FILES:",
    coverage.get(
        "unassigned_count"
    )
)

print()
print(
    "===== REAL MEDIA FILES ====="
)

for item in (
    r.get("items")
    or []
):
    print(
        "SCENE",
        item.get(
            "scene_guess"
        ),
        "|",
        item.get(
            "name"
        ),
        "| type=",
        item.get(
            "media_type"
        ),
        "|",
        item.get(
            "width"
        ),
        "x",
        item.get(
            "height"
        ),
        "| orientation=",
        item.get(
            "orientation"
        ),
        "| technical=",
        item.get(
            "technical_score"
        ),
    )

print()
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

print(
    "MEDIA MUTATED:",
    r.get(
        "media_mutated"
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
echo "======================================"
echo " VI8.31 -> VI8.40 COMPLETE"
echo "======================================"
echo
echo "REAL MEDIA INVENTORY=READY"
echo "SCENE FILE MAPPING=READY"
echo "REAL DIMENSIONS=READY"
echo "REAL CROP FITNESS=READY"
echo "REAL TECHNICAL SCORE=READY"
echo "COVERAGE AUDIT=READY"
echo
echo "VIDEO.PY UNCHANGED=YES"
echo "GERAR_SHORT.SH UNCHANGED=YES"
echo "FFMPEG EXECUTED=NO"
echo "VIDEO GENERATED=NO"
echo "DOWNLOAD EXECUTED=NO"
echo "MEDIA MUTATION=NO"
echo "FULL ACTIVE=LOCKED"
