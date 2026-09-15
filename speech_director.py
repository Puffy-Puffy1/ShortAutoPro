#!/usr/bin/env python3
"""Piper-safe speech direction without changing spoken words."""
from __future__ import annotations
import json,os,re,tempfile
from datetime import date
from pathlib import Path
from typing import Any
BASE=Path(os.getenv("SHORTAUTOPRO_BASE",os.path.expanduser("~/ShortAutoPro"))).resolve();SID=os.getenv("SHORT_ID",date.today().isoformat()).strip();PROFILE=os.getenv("SAP_CHANNEL_PROFILE","default").strip() or "default";R=BASE/"roteiros";SRC=R/f"short_{SID}.txt";OUT=R/f"speech_{SID}.txt";REPORT=R/f"speech_{SID}.json"
PAUSE={"true_crime":{"sentence":"\n","impact":"...\n"},"cinepulsar":{"sentence":"\n","impact":"!\n"},"psicotoon":{"sentence":"\n","impact":"...\n"},"default":{"sentence":"\n","impact":".\n"}}
def wordseq(s:str)->list[str]:return [x.casefold() for x in re.findall(r"[A-Za-zÀ-ÿ0-9'-]+",s)]
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
 if not SRC.is_file():print("ERRO SPEECH DIRECTOR: roteiro ausente");return 1
 original=SRC.read_text(encoding="utf-8").strip();policy=PAUSE.get(PROFILE,PAUSE["default"]);sentences=[" ".join(x.split()) for x in re.split(r"(?<=[.!?])\s+|\n+",original) if x.strip()];out=[]
 for i,s in enumerate(sentences):
  # Preserve words exactly; only strengthen pause boundaries for Piper.
  clean=s.rstrip(); impact=(i==0 or i==len(sentences)-1 or len(wordseq(clean))<=8)
  if clean.endswith((".","!","?",":",";","…")): out.append(clean+"\n")
  else: out.append(clean+(policy["impact"] if impact else policy["sentence"]))
 directed="".join(out).strip()+"\n"
 if wordseq(directed)!=wordseq(original):print("ERRO SPEECH DIRECTOR: palavras foram alteradas");return 1
 atomic_text(OUT,directed);atomic_json(REPORT,{"short_id":SID,"version":"1.0","profile":PROFILE,"content_preserved":True,"sentence_count":len(sentences),"source":str(SRC),"output":str(OUT),"status":"PASS"});print(f"SPEECH DIRECTOR: PASS | profile={PROFILE} | sentences={len(sentences)}");return 0
if __name__=="__main__":raise SystemExit(main())
