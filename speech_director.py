#!/usr/bin/env python3
"""Piper-safe speech director with per-segment pace and pauses.

Spoken words are immutable. Emphasis is represented by a small tempo/pause
change on the whole sentence, never by rewriting factual narration.
"""
from __future__ import annotations
import json,os,re,tempfile
from datetime import date
from pathlib import Path
from typing import Any
BASE=Path(os.getenv("SHORTAUTOPRO_BASE",os.path.expanduser("~/ShortAutoPro"))).resolve();SID=os.getenv("SHORT_ID",date.today().isoformat()).strip();PROFILE=os.getenv("SAP_CHANNEL_PROFILE","default").strip() or "default";R=BASE/"roteiros";SRC=R/f"short_{SID}.txt";OUT=R/f"speech_{SID}.txt";REPORT=R/f"speech_{SID}.json"
PRESETS={
 "true_crime":{"hook_tempo":1.02,"body_tempo":0.99,"long_tempo":1.025,"impact_tempo":0.96,"final_tempo":0.94,"pause_ms":170,"impact_pause_ms":260},
 "cinepulsar":{"hook_tempo":1.05,"body_tempo":1.03,"long_tempo":1.06,"impact_tempo":1.00,"final_tempo":0.98,"pause_ms":120,"impact_pause_ms":190},
 "psicotoon":{"hook_tempo":1.03,"body_tempo":1.00,"long_tempo":1.04,"impact_tempo":0.98,"final_tempo":0.96,"pause_ms":145,"impact_pause_ms":220},
 "default":{"hook_tempo":1.03,"body_tempo":1.00,"long_tempo":1.04,"impact_tempo":0.98,"final_tempo":0.96,"pause_ms":150,"impact_pause_ms":220},
}
IMPACT_TERMS=("mas","porém","entretanto","até que","então","descobriu","revelou","prova","evidence","however","until","revealed")
def wordseq(s:str)->list[str]:return [x.casefold() for x in re.findall(r"[A-Za-zÀ-ÿ0-9'-]+",s)]

def tts_safe_text(value:str)->str:
 """Remove unsupported Cyrillic parentheticals from Portuguese TTS only."""
 return re.sub(r"\s*\([^)]*[\u0400-\u04FF][^)]*\)", "", str(value or "")).strip()
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
 original=SRC.read_text(encoding="utf-8").strip();preset=PRESETS.get(PROFILE,PRESETS["default"]);sentences=[" ".join(x.split()) for x in re.split(r"(?<=[.!?])\s+|\n+",original) if x.strip()]
 if not sentences:print("ERRO SPEECH DIRECTOR: roteiro vazio");return 1
 chunks=[];directed=[]
 for i,s in enumerate(sentences):
  wc=len(wordseq(s));low=s.casefold();impact=any(term in low for term in IMPACT_TERMS) or wc<=7
  if i==0:tempo=preset["hook_tempo"]
  elif i==len(sentences)-1:tempo=preset["final_tempo"]
  elif impact:tempo=preset["impact_tempo"]
  elif wc>=22:tempo=preset["long_tempo"]
  else:tempo=preset["body_tempo"]
  pause=preset["impact_pause_ms"] if impact or i==len(sentences)-1 else preset["pause_ms"]
  text=s.rstrip()
  if not text.endswith((".","!","?",":",";","…")):text += "."
  directed.append(text)
  chunks.append({"index":i+1,"text":text,"tts_text":tts_safe_text(text),"tempo":round(float(tempo),3),"pause_ms":int(pause),"impact":bool(impact),"word_count":wc})
 directed_text="\n".join(directed).strip()+"\n"
 if wordseq(directed_text)!=wordseq(original):print("ERRO SPEECH DIRECTOR: palavras foram alteradas");return 1
 atomic_text(OUT,directed_text);atomic_json(REPORT,{"short_id":SID,"version":"2.0","profile":PROFILE,"content_preserved":True,"sentence_count":len(sentences),"source":str(SRC),"output":str(OUT),"chunks":chunks,"status":"PASS"})
 print(f"SPEECH DIRECTOR: PASS | profile={PROFILE} | chunks={len(chunks)} | dynamic_tempo=ON");return 0
if __name__=="__main__":raise SystemExit(main())
