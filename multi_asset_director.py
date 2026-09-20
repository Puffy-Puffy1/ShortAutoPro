#!/usr/bin/env python3
"""Fetch a bounded secondary documentary asset for visually long/important scenes."""
from __future__ import annotations
import json,os,subprocess,tempfile,time
from datetime import date
from pathlib import Path
from typing import Any
import requests
from wikimedia_source import buscar_wikimedia_fotos,salvar_credito
from evidence_guard import avaliar_evidencia
from subprocess_guard import run_group
BASE=Path(os.getenv("SHORTAUTOPRO_BASE",os.path.expanduser("~/ShortAutoPro"))).resolve();SID=os.getenv("SHORT_ID",date.today().isoformat()).strip();R=BASE/"roteiros";MAP=R/f"scene_map_{SID}.json";PLAN=R/f"pro_edit_plan_{SID}.json";OUT=R/f"multi_asset_{SID}.json";DIR=BASE/"imagens"/f"short_{SID}_secondary"
try:MAX_ASSET_BYTES=int(os.getenv("SAP_MULTI_ASSET_MAX_BYTES",str(40*1024*1024)) or 40*1024*1024)
except (TypeError,ValueError):MAX_ASSET_BYTES=40*1024*1024
MAX_ASSET_BYTES=max(2*1024*1024,min(MAX_ASSET_BYTES,100*1024*1024))
try:MAX_DOWNLOAD_SECONDS=float(os.getenv("SAP_MULTI_ASSET_DOWNLOAD_SECONDS","45") or 45)
except (TypeError,ValueError):MAX_DOWNLOAD_SECONDS=45.0
MAX_DOWNLOAD_SECONDS=max(10.0,min(MAX_DOWNLOAD_SECONDS,120.0))
def load(p:Path)->dict[str,Any]:
 try:x=json.loads(p.read_text(encoding="utf-8"));return x if isinstance(x,dict) else {}
 except Exception:return {}
def atomic(p:Path,x:Any)->None:
 p.parent.mkdir(parents=True,exist_ok=True);fd,t=tempfile.mkstemp(prefix=f".{p.name}.",suffix=".tmp",dir=str(p.parent))
 try:
  with os.fdopen(fd,"w",encoding="utf-8") as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
  os.replace(t,p)
 except Exception:
  try:os.unlink(t)
  except OSError:pass
  raise
def download(url:str,dest:Path)->bool:
 tmp=dest.with_name(f".{dest.name}.{os.getpid()}.tmp")
 try:
  started=time.monotonic()
  read_timeout=max(5.0,min(20.0,MAX_DOWNLOAD_SECONDS))
  with requests.get(url,stream=True,timeout=(10,read_timeout),headers={"User-Agent":"ShortAutoPro/3.0"}) as r:
   if not r.ok:return False
   try:declared=int(r.headers.get("Content-Length") or 0)
   except (TypeError,ValueError):declared=0
   if declared>MAX_ASSET_BYTES:return False
   total=0
   with tmp.open("wb") as f:
    for chunk in r.iter_content(128*1024):
     if not chunk:continue
     if time.monotonic()-started>MAX_DOWNLOAD_SECONDS:return False
     total+=len(chunk)
     if total>MAX_ASSET_BYTES:return False
     f.write(chunk)
  if tmp.stat().st_size<20000:return False
  probe=run_group(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","json",str(tmp)],capture_output=True,text=True,timeout=30)
  if probe.returncode:return False
  s=json.loads(probe.stdout).get("streams",[]);w=int(s[0].get("width",0)) if s else 0;h=int(s[0].get("height",0)) if s else 0
  if w*h<640*360:return False
  os.replace(tmp,dest);return True
 except Exception:return False
 finally:
  try:tmp.unlink(missing_ok=True)
  except OSError:pass
def main()->int:
 data=load(MAP);scenes=data.get("scenes",[]) if isinstance(data.get("scenes"),list) else [];plan=load(PLAN);ps=plan.get("scenes",[]) if isinstance(plan.get("scenes"),list) else []
 if not scenes:print("ERRO MULTI ASSET: scene_map ausente");return 1
 topic=""
 for p in (R/f"used_topic_{SID}.txt",R/f"topic_{SID}.txt"):
  if p.is_file():topic=p.read_text(encoding="utf-8").strip();break
 DIR.mkdir(parents=True,exist_ok=True);max_secondary=max(0,min(6,int(os.getenv("SAP_MULTI_ASSET_MAX","4"))));chosen=[]
 priorities=[]
 for i,s in enumerate(scenes,1):
  role=str(s.get("narrative_role","")).lower();segment=str(s.get("segment",''));primary_photo=any((BASE/"imagens"/f"short_{SID}").glob(f"scene_{i:02d}.*"));importance=(3 if role in {"evidence","reveal","turn","climax","payoff"} else 0)+(1 if len(segment.split())>=16 else 0)
  if primary_photo:priorities.append((importance,i,s))
 priorities.sort(key=lambda x:(-x[0],x[1]))
 for _,i,s in priorities[:max_secondary]:
  alts=s.get("alt_queries",[]) if isinstance(s.get("alt_queries"),list) else [];query=str(alts[0] if alts else s.get("query","")).strip();must=[str(x) for x in s.get("must_have",[]) if str(x).strip()];avoid=[str(x) for x in s.get("avoid",[]) if str(x).strip()];mode=str(s.get("visual_mode","") or "document")
  if not query:continue
  try:cands=buscar_wikimedia_fotos(query,must,avoid,assunto=topic,segmento=str(s.get("segment","")),visual_mode=mode,limite=8)
  except Exception:cands=[]
  winner=None
  for c in cands:
   try:ev=avaliar_evidencia(c,topic,str(s.get("segment","")),must,mode)
   except Exception:continue
   if not ev.get("allowed"):continue
   c["evidence_class"]=ev.get("class");c["score"]=float(c.get("score",0))+float(ev.get("bonus",0));winner=c;break
  if not winner:continue
  dest=DIR/f"scene_{i:02d}_b.jpg"
  if download(str(winner.get("url","")),dest):
   salvar_credito(SID,i,winner);chosen.append({"scene":i,"asset":str(dest),"source":"Wikimedia","evidence_class":winner.get("evidence_class"),"query":query,"score":winner.get("score")})
 beats=[]
 for i,s in enumerate(scenes,1):
  sec=next((x for x in chosen if x["scene"]==i),None);beats.append({"scene":i,"beats":2 if sec else 1,"secondary":sec["asset"] if sec else None,"fallback":"detail_crop" if not sec else None})
 payload={"short_id":SID,"version":"1.0","secondary_assets":chosen,"scene_beats":beats,"status":"PASS"};atomic(OUT,payload);print(f"MULTI ASSET DIRECTOR: PASS | secondary={len(chosen)}/{max_secondary}");return 0
if __name__=="__main__":raise SystemExit(main())
