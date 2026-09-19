#!/usr/bin/env python3
from __future__ import annotations
import json, os, subprocess, sys
from pathlib import Path

BASE=Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
SID=os.getenv("SHORT_ID","").strip()
REPORT=BASE/"reports"/"media"/f"acquisition_missing_{SID}.json"

def read_missing():
    try:data=json.loads(REPORT.read_text(encoding="utf-8"))
    except Exception:return []
    raw=data.get("missing_scenes") or data.get("missing") or data.get("scenes") or []
    out=[]
    for item in raw if isinstance(raw,list) else []:
        value=item.get("scene") if isinstance(item,dict) else item
        try: out.append(int(value))
        except Exception: pass
    return sorted(set(out))

def run(env):
    return subprocess.call([sys.executable,str(BASE/"midia.py")],cwd=BASE,env=env)

def main():
    if not SID:
        print("ERRO MEDIA STAGE RUNTIME: SHORT_ID vazio"); return 1
    env=os.environ.copy()
    code=run(env)
    if code==0:
        print("SAP_MEDIA_STAGE_RUNTIME=PASS pass=1"); return 0
    missing=read_missing()
    if not missing:
        print(f"SAP_MEDIA_STAGE_RUNTIME=HARD_FAIL code={code} reason=NO_MISSING_REPORT"); return code or 1
    print("SAP_MEDIA_STAGE_RUNTIME=RECOVERY_PASS scenes="+",".join(map(str,missing)))
    env["SAP_MEDIA_RECOVERY_PASS"]="1"
    env["SAP_MUST_RESCUE_MAX_QUERIES"]=env.get("SAP_MEDIA_RECOVERY_MUST_QUERIES","8")
    env["SAP_STOCK_RESCUE_MAX_QUERIES"]=env.get("SAP_MEDIA_RECOVERY_STOCK_QUERIES","4")
    env["SAP_MEDIA_PROVIDER_RESULT_TIMEOUT"]=env.get("SAP_MEDIA_RECOVERY_PROVIDER_TIMEOUT","30")
    env["SAP_WIKIMEDIA_SEARCH_DEADLINE"]=env.get("SAP_MEDIA_RECOVERY_WIKIMEDIA_DEADLINE","30")
    code2=run(env)
    if code2==0:
        print("SAP_MEDIA_STAGE_RUNTIME=PASS pass=2"); return 0
    missing2=read_missing()
    print("SAP_MEDIA_STAGE_RUNTIME=BLOCK remaining="+",".join(map(str,missing2 or missing)))
    return code2 or 1

if __name__=="__main__": raise SystemExit(main())
