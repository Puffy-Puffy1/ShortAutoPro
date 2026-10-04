#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, re, tempfile
from pathlib import Path
from media_v3.acquisition import MediaAcquisitionV3
from media_validator_v2 import validate as validate_media

BASE=Path(os.getenv("SHORTAUTOPRO_BASE",Path.home()/"ShortAutoPro")).resolve()
ENGINE_VERSION="3.0.0"

def atomic_json(path,payload):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=f".{path.name}.",suffix=".tmp",dir=str(path.parent))
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as fh:
            json.dump(payload,fh,ensure_ascii=False,indent=2,sort_keys=True)
            fh.write("\n"); fh.flush(); os.fsync(fh.fileno())
        os.replace(tmp,path); tmp=""
    finally:
        if tmp:
            try: os.unlink(tmp)
            except OSError: pass

def digest(payload):
    unsigned=dict(payload); unsigned.pop("integrity_sha256",None)
    return hashlib.sha256(json.dumps(unsigned,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def validate_sid(value):
    sid=str(value or "").strip()
    if not sid or len(sid)>96 or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*",sid) or ".." in sid:
        raise RuntimeError("MEDIA_INPUT_INVALID:short_id")
    return sid

def load_scenes(sid):
    path=BASE/"roteiros"/f"scene_map_{sid}.json"
    if not path.is_file(): raise RuntimeError("MEDIA_INPUT_INVALID:scene_map_missing")
    raw=json.loads(path.read_text(encoding="utf-8")); scenes=raw.get("scenes") if isinstance(raw,dict) else raw
    if not isinstance(scenes,list) or not scenes: raise RuntimeError("MEDIA_INPUT_INVALID:scene_map_empty")
    seen=set()
    for i,scene in enumerate(scenes,1):
        if not isinstance(scene,dict): raise RuntimeError(f"MEDIA_INPUT_INVALID:scene_{i:02d}:not_object")
        scene_id=str(scene.get("scene_id",scene.get("scene",i))).strip()
        if not scene_id or scene_id in seen: raise RuntimeError(f"MEDIA_INPUT_INVALID:scene_{i:02d}:identity")
        seen.add(scene_id)
    return scenes

def _existing_record(base,sid,number,scene):
    media=base/"imagens"/f"short_{sid}"; sidecar=media/f"scene_{number:02d}.json"
    if not sidecar.is_file(): return None
    try:
        row=json.loads(sidecar.read_text(encoding="utf-8"))
        path=Path(str(row.get("path") or "")).resolve()
        root=media.resolve(); path.relative_to(root)
        expected_scene_id=str(scene.get("scene_id",scene.get("scene",number))).strip()
        if (row.get("short_id")!=sid or int(row.get("scene_number",0))!=number
                or str(row.get("scene_id","")).strip()!=expected_scene_id
                or row.get("validated") is not True):
            return None
        if any(x in path.name.casefold() for x in ("slate","placeholder","neutral_editorial","editorial_reuse")):
            return None
        expected=str(row.get("sha256") or row.get("checksum_sha256") or "")
        if not expected or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=expected:
            return None
        validated=validate_media(path)
        if validated.get("sha256")!=expected: return None
        if len(scene.get("must_have") or []) != int(row.get("must_total",0) or 0):
            return None
        row["path"]=str(path); row["sha256"]=expected; row["checksum_sha256"]=expected; row["validated"]=True; row["probe"]=validated["probe"]
        return row
    except Exception:
        return None

def build_manifest(short_id, engine=None):
    sid=validate_sid(short_id); scenes=load_scenes(sid); engine=engine or MediaAcquisitionV3(BASE)
    records=[]; diagnostics=[]
    for number,scene in enumerate(scenes,1):
        existing=_existing_record(BASE,sid,number,scene)
        if existing is not None:
            records.append(existing)
            diagnostics.append({"scene_id":str(scene.get("scene_id",scene.get("scene",number))),"query":str(scene.get("query") or scene.get("busca") or scene.get("segment") or ""),"final_status":"RESUMED","selected_provider":existing.get("provider",""),"selected_asset_id":existing.get("asset_id",""),"rejections":[],"fallbacks":[]})
            continue
        record,diag=engine.acquire_scene(sid,number,scene)
        diagnostics.append(diag.to_dict())
        if record is None:
            report={"schema_version":"media-diagnostics-v3","short_id":sid,"engine_version":ENGINE_VERSION,"scenes":diagnostics,"final_status":"FAILED"}
            atomic_json(BASE/"reports"/"media"/f"acquisition_{sid}.json",report)
            raise RuntimeError(f"MEDIA_ACQUISITION_V3_FAILED:scene_{number:02d}:{diag.error}")
        record.update({"short_id":sid,"scene_number":number,"scene_id":str(scene.get("scene_id",scene.get("scene",number))).strip(),"must_total":len(diag.must),"validated":True,"checksum_sha256":record.get("sha256","")})
        atomic_json(BASE/"imagens"/f"short_{sid}"/f"scene_{number:02d}.json",record)
        records.append(record)
    manifest={"schema_version":"media-manifest-v2","engine_version":ENGINE_VERSION,"short_id":sid,"immutable":True,"scene_count":len(records),
              "scenes":[{"scene_id":str(scene.get("scene_id",scene.get("scene",i))),"scene_number":i,
                         "asset":{"path":record["path"],"checksum_sha256":record["sha256"],"validated":True,
                                  "source":record["provider"],"asset_id":record["asset_id"],"probe":record["probe"],
                                  "verification_mode":record.get("verification_mode",""),"provenance":record.get("provenance",{})}}
                        for i,(scene,record) in enumerate(zip(scenes,records),1)]}
    manifest["integrity_sha256"]=digest(manifest)
    atomic_json(BASE/"manifests"/f"media_{sid}.json",manifest)
    report={"schema_version":"media-diagnostics-v3","short_id":sid,"engine_version":ENGINE_VERSION,"scenes":diagnostics,"final_status":"RESOLVED"}
    atomic_json(BASE/"reports"/"media"/f"acquisition_{sid}.json",report)
    return manifest

def main(short_id=None):
    if short_id is None:
        p=argparse.ArgumentParser(); p.add_argument("--short-id",required=True); short_id=p.parse_args().short_id
    manifest=build_manifest(short_id)
    print(f"MEDIA_ACQUISITION_V3=PASS short_id={short_id} scenes={manifest['scene_count']}")
    return 0

if __name__=="__main__": raise SystemExit(main())
