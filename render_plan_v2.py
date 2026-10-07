#!/usr/bin/env python3
"""Deterministic render planning boundary for Render Engine V2.

This replaces the old Stage-6 editing chain as the producer of pro_edit_plan.
It does not acquire media or render anything.
"""
from __future__ import annotations
import json, os, tempfile
from pathlib import Path
import re
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

def validate_short_id(value):
    sid = str(value or "").strip()
    if not sid or len(sid) > 96 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", sid) or ".." in sid:
        raise RuntimeError("RENDER_PLAN_INVALID:short_id")
    return sid

def main(short_id=None):
    import argparse
    if short_id is None:
        ap=argparse.ArgumentParser()
        ap.add_argument("--short-id",required=True)
        args=ap.parse_args()
        short_id=args.short_id
    sid=validate_short_id(short_id)
    scene_path=BASE/"roteiros"/f"scene_map_{sid}.json"
    out=BASE/"roteiros"/f"pro_edit_plan_{sid}.json"
    data=json.loads(scene_path.read_text(encoding="utf-8"))
    scenes=data.get("scenes") if isinstance(data,dict) else data
    if not isinstance(scenes,list) or not scenes: raise RuntimeError("RENDER_PLAN_INVALID:scene_map")
    media_path=BASE/"manifests"/f"media_{sid}.json"
    audio_path=BASE/"audios"/f"short_{sid}.mp3"
    caption_path=BASE/"videos"/f"short_{sid}.ass"
    if not media_path.is_file(): raise RuntimeError("RENDER_PLAN_INVALID:media_manifest_missing")
    if not audio_path.is_file(): raise RuntimeError("RENDER_PLAN_INVALID:audio_missing")
    if not caption_path.is_file(): raise RuntimeError("RENDER_PLAN_INVALID:caption_missing")
    media=json.loads(media_path.read_text(encoding="utf-8"))
    if media.get("short_id") != sid or media.get("schema_version") != "media-manifest-v2":
        raise RuntimeError("RENDER_PLAN_INVALID:media_manifest_identity")
    media_rows=media.get("scenes") if isinstance(media,dict) else []
    if not isinstance(media_rows,list) or len(media_rows)!=len(scenes):
        raise RuntimeError("RENDER_PLAN_INVALID:media_manifest_scene_count")
    plan={"schema_version":"render-plan-v2","short_id":sid,
          "inputs":{"media_manifest":str(media_path),"audio":str(audio_path),"captions":str(caption_path)},
          "scenes":[]}
    seen_ids=set()
    for i,scene in enumerate(scenes,1):
        if not isinstance(scene,dict): raise RuntimeError(f"RENDER_PLAN_INVALID:scene_{i:02d}")
        scene_id=str(scene.get("scene_id",scene.get("scene",i))).strip()
        if not scene_id or scene_id in seen_ids:
            raise RuntimeError(f"RENDER_PLAN_INVALID:scene_id_{i:02d}")
        seen_ids.add(scene_id)
        media_row=media_rows[i-1]
        asset=media_row.get("asset",{}) if isinstance(media_row,dict) else {}
        if not isinstance(asset,dict) or asset.get("validated") is not True:
            raise RuntimeError(f"RENDER_PLAN_INVALID:scene_{i:02d}:media_not_validated")
        plan["scenes"].append({
            "scene_id":scene_id,
            "media":{"path":str(asset.get("path") or ""),"checksum_sha256":str(asset.get("checksum_sha256") or ""),
                     "provider":str(asset.get("source") or ""),"asset_id":str(asset.get("asset_id") or "")},
            "audio":{"path":str(audio_path)},
            "caption":{"path":str(caption_path),"required":True},
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
