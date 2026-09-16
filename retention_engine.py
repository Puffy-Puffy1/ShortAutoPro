#!/usr/bin/env python3
"""Pre-render retention analysis for ShortAutoPro.

Never invents or rewrites facts. Repair mode only changes pacing metadata in the
professional edit plan so factual narration remains untouched.
"""
from __future__ import annotations
import argparse, json, math, os, re, tempfile
from datetime import date
from pathlib import Path
from typing import Any

BASE=Path(os.getenv("SHORTAUTOPRO_BASE",os.path.expanduser("~/ShortAutoPro"))).resolve()
SID=os.getenv("SHORT_ID",date.today().isoformat()).strip()
R=BASE/"roteiros"; SCRIPT=R/f"short_{SID}.txt"; MAP=R/f"scene_map_{SID}.json"; PLAN=R/f"pro_edit_plan_{SID}.json"; REPORT=R/f"retention_{SID}.json"


def env_float(name:str,default:float,minimum:float,maximum:float)->float:
    try:value=float(os.getenv(name,str(default)))
    except (TypeError,ValueError):value=default
    if not math.isfinite(value):value=default
    return max(minimum,min(maximum,value))


def atomic(path:Path,payload:Any)->None:
    path.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(prefix=f".{path.name}.",suffix=".tmp",dir=str(path.parent))
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f: json.dump(payload,f,ensure_ascii=False,indent=2); f.write("\n"); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path)
    except Exception:
        try: os.unlink(tmp)
        except OSError: pass
        raise


def load(path:Path)->dict[str,Any]:
    if not path.is_file(): return {}
    try:
        x=json.loads(path.read_text(encoding="utf-8")); return x if isinstance(x,dict) else {}
    except Exception: return {}


def sentences(text:str)->list[str]: return [" ".join(x.split()) for x in re.split(r"(?<=[.!?])\s+|\n+",text) if x.strip()]
def words(text:str)->list[str]: return re.findall(r"[A-Za-zÀ-ÿ0-9'-]+",text)


def score()->dict[str,Any]:
    text=SCRIPT.read_text(encoding="utf-8").strip() if SCRIPT.is_file() else ""
    scene_map=load(MAP); scenes=scene_map.get("scenes",[]) if isinstance(scene_map.get("scenes"),list) else []
    plan=load(PLAN); pscenes=plan.get("scenes",[]) if isinstance(plan.get("scenes"),list) else []
    sents=sentences(text); issues=[]
    if not text or not scenes: return {"retention_score":0.0,"status":"BLOCK","issues":["missing_script_or_scenes"]}

    # Hook: short, immediate and curiosity-bearing without requiring clickbait.
    first=" ".join(words(text)[:26]); hook_words=len(words(first))
    hook=100.0
    if hook_words>24: hook-=18
    curiosity_terms=("mas","porém","entretanto","ninguém","mistério","descobriu","então","até que","o que","como","por que","quando")
    if not any(t in first.lower() for t in curiosity_terms): hook-=12
    if len(words(text))>0 and len(words(first))/len(words(text))>0.32: hook-=8

    lengths=[len(words(x)) for x in sents] or [0]
    long=sum(1 for n in lengths if n>24); very_long=sum(1 for n in lengths if n>34)
    language=max(0.0,100.0-long*7.0-very_long*9.0)
    if very_long: issues.append(f"very_long_sentences:{very_long}")

    roles=[str(x.get("narrative_role","")).lower() for x in scenes if isinstance(x,dict)]
    micro=sum(1 for x in roles[1:-1] if x in {"turn","turning_point","reveal","escalation","climax","evidence"})
    micro_score=min(100.0,55.0+micro*12.0)
    if micro<2: issues.append("micro_hooks_low")
    payoff=100.0 if any(x in {"payoff","conclusion","reveal","aftermath"} for x in roles[-3:]) else 72.0

    queries=[str(x.get("query","")).lower() for x in scenes if isinstance(x,dict)]
    shots=[str(x.get("shot_type","")).lower() for x in scenes if isinstance(x,dict)]
    unique_q=len(set(queries))/max(1,len(queries)); unique_s=len(set(shots))/max(1,len(shots))
    visual=min(100.0,55.0+35.0*unique_q+20.0*unique_s)
    repeated=sum(1 for i in range(1,len(queries)) if queries[i]==queries[i-1] and queries[i])
    visual=max(0.0,visual-repeated*12.0)
    if repeated: issues.append(f"repeated_visual_beats:{repeated}")

    pace=88.0
    if pscenes:
        vals=[]
        for x in pscenes:
            try:
                value=float(x.get("pace_multiplier",1.0))
                if math.isfinite(value):vals.append(round(value,2))
            except (TypeError,ValueError):pass
        if len(set(vals))<3: pace-=18; issues.append("pacing_variety_low")
        runs=0
        for i in range(2,len(vals)):
            if vals[i]==vals[i-1]==vals[i-2]: runs+=1
        pace-=min(20,runs*5)

    total=round(0.22*hook+0.16*language+0.18*micro_score+0.12*payoff+0.20*visual+0.12*pace,1)
    minimum=env_float("SAP_RETENTION_MIN_SCORE",78.0,60.0,95.0)
    status="PASS" if total>=minimum else "REVIEW" if total>=70 else "BLOCK"
    return {"short_id":SID,"version":"1.1","retention_score":total,"threshold":minimum,"status":status,"components":{"hook":round(hook,1),"language":round(language,1),"micro_hooks":round(micro_score,1),"payoff":round(payoff,1),"visual_change":round(visual,1),"pacing":round(pace,1)},"metrics":{"sentence_count":len(sents),"long_sentences":long,"very_long_sentences":very_long,"micro_hooks":micro,"visual_query_uniqueness":round(unique_q,3)},"issues":issues}


def repair_pacing(report:dict[str,Any])->list[str]:
    plan=load(PLAN); scenes=plan.get("scenes",[]) if isinstance(plan.get("scenes"),list) else []
    if not scenes: return []
    changes=[]
    pattern=(0.88,1.04,0.94,1.08,0.91,1.02)
    for i,item in enumerate(scenes):
        if not isinstance(item,dict): continue
        role=str(item.get("narrative_role","")).lower()
        try:current=float(item.get("pace_multiplier",1.0) or 1.0)
        except (TypeError,ValueError):current=1.0
        if not math.isfinite(current):current=1.0
        target=current
        if role in {"hook","cold_open","escalation"}: target=min(current,0.94)
        elif role in {"evidence","reveal","payoff","conclusion"}: target=max(current,1.04)
        elif "pacing_variety_low" in report.get("issues",[]): target=pattern[i%len(pattern)]
        target=round(max(0.80,min(1.12,target)),3)
        if abs(target-current)>=0.015:
            item["pace_multiplier"]=target; changes.append(f"scene_{i+1}:{current:.2f}->{target:.2f}")
    if changes:
        plan["retention_repair"]={"version":"1.1","changes":changes}; atomic(PLAN,plan)
    return changes


def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument("--repair",action="store_true"); ap.add_argument("--enforce",action="store_true"); args=ap.parse_args()
    try:
        report=score(); changes=[]
        if args.repair and report.get("retention_score",0)<report.get("threshold",78):
            changes=repair_pacing(report); report=score(); report["repair_changes"]=changes
        atomic(REPORT,report)
    except Exception as exc: print(f"ERRO RETENTION ENGINE: {exc}"); return 1
    print(f"RETENTION SCORE: {report['retention_score']}/100 | {report['status']}")
    if args.enforce and report["status"]!="PASS": return 20 if report["status"]=="REVIEW" else 1
    return 0

if __name__=="__main__": raise SystemExit(main())
