#!/usr/bin/env python3
"""Visual continuity scorer and conservative repair hints."""
from __future__ import annotations
import json, math, os, re, tempfile, unicodedata
from datetime import date
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SHORT_ID = os.getenv("SHORT_ID", date.today().isoformat()).strip()
SCENE_MAP = BASE / "roteiros" / f"scene_map_{SHORT_ID}.json"
REPORT = BASE / "roteiros" / f"visual_continuity_{SHORT_ID}.json"


def norm(v: Any) -> str:
    s = unicodedata.normalize("NFKD", str(v or ""))
    return " ".join("".join(c for c in s if not unicodedata.combining(c)).lower().split())


def toks(v: Any) -> set[str]:
    return {x for x in re.findall(r"[a-z0-9]+", norm(v)) if len(x) >= 3}


def jaccard(a: Any, b: Any) -> float:
    aa, bb = toks(a), toks(b)
    if not aa or not bb:
        return 0.0
    return len(aa & bb) / len(aa | bb)


def atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2); f.write("\n"); f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise


def read() -> dict[str, Any]:
    data = json.loads(SCENE_MAP.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("scenes"), list):
        raise ValueError("scene_map inválido")
    return data


def field(scene: dict[str, Any], *names: str) -> str:
    for name in names:
        value = scene.get(name)
        if isinstance(value, list):
            value = " ".join(map(str, value))
        if str(value or "").strip():
            return str(value)
    return ""


def continuity_pair(prev: dict[str, Any], cur: dict[str, Any]) -> tuple[float, dict[str, float], list[str]]:
    subject = jaccard(field(prev, "main_subject", "must_have"), field(cur, "main_subject", "must_have"))
    location = jaccard(field(prev, "location", "environment"), field(cur, "location", "environment"))
    era = jaccard(field(prev, "era"), field(cur, "era"))
    mood = jaccard(field(prev, "emotion", "mood"), field(cur, "emotion", "mood"))
    query = jaccard(field(prev, "query"), field(cur, "query"))
    same_context = max(subject, location, era) >= 0.34

    # Same narrative context should preserve anchors; context changes should not
    # be punished for healthy visual diversity.
    if same_context:
        score = 42*subject + 25*location + 13*era + 10*mood + 10*min(query, 0.75)/0.75
    else:
        diversity = 1.0 - min(1.0, query)
        score = 70 + 20*diversity + 10*(1.0 if norm(prev.get("shot_type")) != norm(cur.get("shot_type")) else 0.0)
    score = round(max(0.0, min(100.0, score)), 1)
    issues: list[str] = []
    if same_context and subject < 0.2: issues.append("subject_anchor_lost")
    if same_context and location < 0.12 and (field(prev,"location") or field(cur,"location")): issues.append("location_anchor_lost")
    if same_context and era < 0.12 and (field(prev,"era") or field(cur,"era")): issues.append("era_anchor_lost")
    if query > 0.82 and norm(prev.get("shot_type")) == norm(cur.get("shot_type")): issues.append("visual_repetition_risk")
    return score, {"subject":round(subject*100,1),"location":round(location*100,1),"era":round(era*100,1),"mood":round(mood*100,1),"query":round(query*100,1)}, issues


def main() -> int:
    try:
        data = read(); scenes = data["scenes"]
        if len(scenes) < 2: raise ValueError("cenas insuficientes")
        pairs=[]; scores=[]; all_issues=[]
        for i in range(1,len(scenes)):
            score, components, issues = continuity_pair(scenes[i-1], scenes[i])
            pairs.append({"from":i,"to":i+1,"score":score,"components":components,"issues":issues})
            scores.append(score); all_issues.extend(f"scene_{i+1}:{x}" for x in issues)
            scenes[i]["visual_continuity_from_previous"] = score
        avg = round(sum(scores)/len(scores),1)
        data["visual_continuity"]={"version":"1.0","score":avg,"status":"PASS" if avg>=70 else "REVIEW"}
        atomic(SCENE_MAP,data)
        atomic(REPORT,{"short_id":SHORT_ID,"version":"1.0","visual_continuity_score":avg,"status":"PASS" if avg>=70 else "REVIEW","issues":all_issues,"pairs":pairs})
    except Exception as exc:
        print(f"ERRO VISUAL CONTINUITY: {exc}"); return 1
    print(f"VISUAL CONTINUITY SCORE: {avg}/100")
    print("VISUAL CONTINUITY: PASS" if avg>=70 else "VISUAL CONTINUITY: REVIEW")
    return 0

if __name__ == "__main__": raise SystemExit(main())
