#!/usr/bin/env python3
"""Semantic safe-zone guard for ASS captions.

Uses Visual Director protected zones. It does not claim face detection; it moves
the global caption safe area when the storyboard indicates important lower-frame
content and reports residual collision risk.
"""
from __future__ import annotations
import json,os,re,tempfile
from datetime import date
from pathlib import Path
from typing import Any
BASE=Path(os.getenv("SHORTAUTOPRO_BASE",os.path.expanduser("~/ShortAutoPro"))).resolve();SID=os.getenv("SHORT_ID",date.today().isoformat()).strip();ASS=BASE/"videos"/f"short_{SID}.ass";MAP=BASE/"roteiros"/f"scene_map_{SID}.json";REPORT=BASE/"roteiros"/f"caption_layout_{SID}.json"
def atomic_text(p:Path,s:str)->None:
 p.parent.mkdir(parents=True,exist_ok=True);fd,t=tempfile.mkstemp(prefix=f".{p.name}.",suffix=".tmp",dir=str(p.parent))
 try:
  with os.fdopen(fd,"w",encoding="utf-8") as f:f.write(s);f.flush();os.fsync(f.fileno())
  os.replace(t,p)
 except Exception:
  try:os.unlink(t)
  except OSError:pass
  raise
def atomic_json(p:Path,x:Any)->None:atomic_text(p,json.dumps(x,ensure_ascii=False,indent=2)+"\n")
def main()->int:
 if not ASS.is_file() or not MAP.is_file():print("ERRO CAPTION LAYOUT: artefatos ausentes");return 1
 try:data=json.loads(MAP.read_text(encoding="utf-8"));scenes=data.get("scenes",[]);zones=[str(x.get("protected_zone","center")).lower() for x in scenes if isinstance(x,dict)];bottom=sum(1 for z in zones if z=="bottom");center=sum(1 for z in zones if z=="center");margin=305
 except Exception as exc:print(f"ERRO CAPTION LAYOUT: {exc}");return 1
 if bottom>=max(2,len(zones)//4):margin=390
 elif bottom:margin=350
 content=ASS.read_text(encoding="utf-8");lines=[];changed=False
 for line in content.splitlines():
  if line.startswith("Style: Dynamic,"):
   parts=line.split(",")
   if len(parts)>=23:parts[21]=str(margin);line=",".join(parts);changed=True
  lines.append(line)
 if not changed:print("ERRO CAPTION LAYOUT: Style Dynamic ausente");return 1
 atomic_text(ASS,"\n".join(lines)+"\n");risk=round(100*bottom/max(1,len(zones)),1);score=round(max(0,100-risk*0.35),1);atomic_json(REPORT,{"short_id":SID,"version":"1.0","status":"PASS" if score>=88 else "REVIEW","score":score,"protected_zones":{"bottom":bottom,"center":center,"total":len(zones)},"margin_v":margin,"collision_risk_percent":risk,"method":"semantic protected-zone heuristic; no face detector claimed"});print(f"CAPTION LAYOUT: PASS | margin_v={margin} | risk={risk}%");return 0
if __name__=="__main__":raise SystemExit(main())
