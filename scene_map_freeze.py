#!/usr/bin/env python3
"""Freeze the final SceneMap into the canonical immutable bridge artifact."""
from __future__ import annotations
import argparse, hashlib, json, os
from datetime import datetime, timezone
from pathlib import Path

BASE=Path(os.getenv("SHORTAUTOPRO_BASE",Path.home()/"ShortAutoPro")).resolve()

def canonical_bytes(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--short-id",required=True)
    args=ap.parse_args()
    sid=args.short_id.strip()
    source=BASE/"roteiros"/f"scene_map_{sid}.json"
    target=BASE/"manifests"/f"scene_map_{sid}.json"
    if not source.is_file():
        raise RuntimeError("SCENE_MAP_FREEZE_SOURCE_MISSING")
    data=json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(data,dict) or not isinstance(data.get("scenes"),list) or not data["scenes"]:
        raise RuntimeError("SCENE_MAP_FREEZE_INVALID")
    scenes=data["scenes"]
    for i,scene in enumerate(scenes,1):
        if not isinstance(scene,dict) or not str(scene.get("segment","")).strip():
            raise RuntimeError(f"SCENE_MAP_FREEZE_INVALID_SCENE:{i}")
        if not str(scene.get("query","")).strip():
            raise RuntimeError(f"SCENE_MAP_FREEZE_QUERY_MISSING:{i}")
    payload=dict(data)
    payload["schema_version"]="SCENE_MAP_FROZEN_1.0"
    payload["short_id"]=sid
    payload["frozen_at"]=datetime.now(timezone.utc).isoformat()
    payload["source_path"]=str(source)
    payload["source_sha256"]=hashlib.sha256(canonical_bytes(data)).hexdigest()
    payload["mutable_upstream_closed"]=True
    target.parent.mkdir(parents=True,exist_ok=True)
    tmp=target.with_suffix(target.suffix+".tmp")
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    os.replace(tmp,target)
    print(json.dumps({"status":"PASS","short_id":sid,"path":str(target),"scene_count":len(scenes),
                      "source_sha256":payload["source_sha256"]},ensure_ascii=False))
    return 0
if __name__=="__main__": raise SystemExit(main())
