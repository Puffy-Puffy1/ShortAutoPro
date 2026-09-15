#!/usr/bin/env python3
"""Multidimensional selected-visual scoring for ShortAutoPro 3.0."""
from __future__ import annotations
import json,math,os,re,subprocess,tempfile,unicodedata
from datetime import date
from pathlib import Path
from typing import Any
BASE=Path(os.getenv("SHORTAUTOPRO_BASE",os.path.expanduser("~/ShortAutoPro"))).resolve();SID=os.getenv("SHORT_ID",date.today().isoformat()).strip();R=BASE/"roteiros";MAP=R/f"scene_map_{SID}.json";VI=R/f"visual_intelligence_6_{SID}.json";MEDIA=BASE/"imagens"/f"short_{SID}";OUT=R/f"visual_score_{SID}.json"
GENERIC={"coffee","cafe","lifestyle","smiling","happy","model","shopping","basket","laundry","generic","stock","office worker","sunset","landscape"}
def load(p:Path)->dict[str,Any]:
 try:x=json.loads(p.read_text(encoding="utf-8"));return x if isinstance(x,dict) else {}
 except Exception:return {}
def norm(v:Any)->str:
 s=unicodedata.normalize("NFKD",str(v or ""));return " ".join("".join(c for c in s if not unicodedata.combining(c)).lower().split())
def toks(v:Any)->set[str]:return {x for x in re.findall(r"[a-z0-9]+",norm(v)) if len(x)>=3}
def overlap(a:Any,b:Any)->float:
 aa,bb=toks(a),toks(b)
 if not aa:return 1.0
 return len(aa&bb)/len(aa)
def atomic(p:Path,x:Any)->None:
 p.parent.mkdir(parents=True,exist_ok=True);fd,t=tempfile.mkstemp(prefix=f".{p.name}.",suffix=".tmp",dir=str(p.parent))
 try:
  with os.fdopen(fd,"w",encoding="utf-8") as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
  os.replace(t,p)
 except Exception:
  try:os.unlink(t)
  except OSError:pass
  raise
def media_for(n:int)->Path|None:
 hits=[p for p in MEDIA.glob(f"scene_{n:02d}.*") if p.is_file() and p.suffix.lower() in {".jpg",".jpeg",".png",".webp",".mp4",".mov",".webm",".mkv"}]
 return hits[0] if len(hits)==1 else None
def probe(p:Path|None)->tuple[int,int]:
 if not p:return 0,0
 try:
  r=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","json",str(p)],capture_output=True,text=True,timeout=30);s=json.loads(r.stdout).get("streams",[]);return (int(s[0].get("width",0)),int(s[0].get("height",0))) if s else (0,0)
 except Exception:return 0,0
def clamp(v:float)->float:return round(max(0,min(100,v)),1)
def main()->int:
 sm=load(MAP);vi=load(VI);scenes=sm.get("scenes",[]) if isinstance(sm.get("scenes"),list) else [];viscenes=vi.get("scenes",[]) if isinstance(vi.get("scenes"),list) else []
 if not scenes:print("ERRO VISUAL SCORE: scene_map ausente");return 1
 rows=[];all_scores=[]
 for i,scene in enumerate(scenes,1):
  v=viscenes[i-1] if i<=len(viscenes) and isinstance(viscenes[i-1],dict) else {};win=v.get("winner",{}) if isinstance(v.get("winner"),dict) else {};desc=str(win.get("descricao",""));source=str(win.get("fonte",""));risk=str(win.get("risk","LOW")).upper();klass=str(win.get("class",""));p=media_for(i);w,h=probe(p);pixels=w*h
  relevance=clamp(float(win.get("semantic",0) or 0)) if win else 65.0
  location=clamp(100*overlap(scene.get("location",""),desc)) if scene.get("location") else 90.0
  subject_text=" ".join([str(scene.get("main_subject",""))," ".join(str(x) for x in scene.get("must_have",[]) if str(x).strip())]);subject=clamp(100*overlap(subject_text,desc)) if subject_text.strip() else 85.0
  era=clamp(100*overlap(scene.get("era",""),desc)) if scene.get("era") else 90.0
  quality=100.0 if pixels>=1280*720 else 90.0 if pixels>=921600 else 75.0 if pixels>=640*360 else 35.0
  orientation=100.0 if h>w else 86.0 if h and w else 50.0
  safety=100.0 if risk in {"LOW",""} and "MISLEADING" not in klass else 70.0 if risk=="MEDIUM" else 0.0
  generic_hits=sum(1 for term in GENERIC if term in norm(desc));generic_penalty=0.0
  if source.lower() in {"pexels","pixabay","coverr"} and relevance<72:generic_penalty+=12
  generic_penalty+=min(24,generic_hits*6)
  evidence_bonus=8.0 if str(win.get("evidence_class",""))=="CASE_DIRECT" or klass=="REAL_DOCUMENTARY" else 3.0 if klass=="SAFE_CONTEXT" else 0.0
  components={"relevance":relevance,"location":location,"character_object":subject,"era":era,"quality":quality,"orientation":orientation,"safety":safety}
  score=sum(components[k]*wgt for k,wgt in {"relevance":.28,"location":.12,"character_object":.18,"era":.08,"quality":.14,"orientation":.08,"safety":.12}.items())-generic_penalty+evidence_bonus;score=clamp(score);all_scores.append(score)
  rows.append({"scene":i,"media":str(p) if p else None,"provider":source or None,"vi6_class":klass or None,"components":components,"generic_penalty":generic_penalty,"documentary_bonus":evidence_bonus,"visual_score":score})
 avg=round(sum(all_scores)/len(all_scores),1);minimum=float(os.getenv("SAP_VISUAL_SCORE_MIN","72"));weak=[x["scene"] for x in rows if x["visual_score"]<minimum];payload={"short_id":SID,"version":"1.0","visual_score":avg,"threshold":minimum,"status":"PASS" if not weak and avg>=minimum else "REVIEW","weak_scenes":weak,"scenes":rows};atomic(OUT,payload);print(f"VISUAL MULTISCORE: {payload['status']} | {avg}/100 | weak={weak}");return 0
if __name__=="__main__":raise SystemExit(main())
