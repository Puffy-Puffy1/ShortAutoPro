#!/usr/bin/env python3
"""Deterministic render planning boundary for Render Engine V2.

This replaces the old Stage-6 editing chain as the producer of pro_edit_plan.
It does not acquire media or render anything.
"""
from __future__ import annotations
import json, os, tempfile
from pathlib import Path
BASE=Path(os.getenv("SHORTAUTOPRO_BASE",Path.home()/"ShortAutoPro")).resolve()

def atomic(path:Path,data:dict):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=f".{path.name}.",suffix=".tmp",dir=str(path.parent))
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(data,f,ensure_ascii=False,indent=2,sort_keys=True); f.write("\n"); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path); tmp=""
    finally:
        if tmp:
            try: os.unlink(tmp)
            except OSError: pass

def main(short_id=None):
    import argparse
    if short_id is None:
        ap=argparse.ArgumentParser()
        ap.add_argument("--short-id",required=True)
        args=ap.parse_args()
        short_id=args.short_id
    sid=short_id
    scene_path=BASE/"roteiros"/f"scene_map_{sid}.json"
    out=BASE/"roteiros"/f"pro_edit_plan_{sid}.json"
    data=json.loads(scene_path.read_text(encoding="utf-8"))
    scenes=data.get("scenes") if isinstance(data,dict) else data
    if not isinstance(scenes,list) or not scenes: raise RuntimeError("RENDER_PLAN_INVALID:scene_map")
    plan={"schema_version":"render-plan-v2","short_id":sid,"scenes":[]}
    for i,scene in enumerate(scenes,1):
        if not isinstance(scene,dict): raise RuntimeError(f"RENDER_PLAN_INVALID:scene_{i:02d}")
        plan["scenes"].append({
            "scene_id":str(scene.get("scene_id",scene.get("scene",i))),
            "pace_multiplier":1.0,
            "zoom_start":1.0,
            "zoom_end":1.04,
            "pan":"center",
            "cut_style":"editorial_cut",
            "transition_duration":0.0,
        })
    atomic(out,plan)
    print(f"RENDER_PLAN_V2=PASS short_id={sid} scenes={len(plan['scenes'])}")
    return 0

if __name__=="__main__": raise SystemExit(main())
