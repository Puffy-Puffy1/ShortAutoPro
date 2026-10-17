#!/usr/bin/env python3
"""Measure and, when necessary, remaster the final MP4 audio stream.

This closes the codec gap where a pre-AAC limiter can still produce intersample
peaks above policy after encoding.
"""
from __future__ import annotations
import json, math, os, re, subprocess, tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Any
from subprocess_guard import run_group
from runtime_config import env_float

BASE=Path(os.getenv("SHORTAUTOPRO_BASE",os.path.expanduser("~/ShortAutoPro"))).resolve(); SID=os.getenv("SHORT_ID",date.today().isoformat()).strip(); VIDEO=BASE/"videos"/f"short_v6_{SID}.mp4"; REPORT=BASE/"reports"/"evolution"/f"final_audio_{SID}.json"
TARGET=env_float("SAP_AUDIO_TARGET_LUFS",-14.0,-24.0,-8.0); TP=env_float("SAP_AUDIO_TRUE_PEAK_DB",-1.5,-6.0,-0.1); LRA=env_float("SAP_AUDIO_LRA",7.0,1.0,20.0)

def atomic(p:Path,x:Any)->None:
 p.parent.mkdir(parents=True,exist_ok=True); fd,t=tempfile.mkstemp(prefix=f".{p.name}.",suffix=".tmp",dir=str(p.parent))
 try:
  with os.fdopen(fd,"w",encoding="utf-8") as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
  os.replace(t,p)
 except Exception:
  try:os.unlink(t)
  except OSError:pass
  raise

def file_identity(path:Path)->dict[str,int]:
 try:
  stat=path.stat()
  return {"size_bytes":int(stat.st_size),"mtime_ns":int(stat.st_mtime_ns)}
 except OSError:
  return {"size_bytes":0,"mtime_ns":0}

def measure(path:Path)->dict[str,float]:
 cmd=["ffmpeg","-hide_banner","-nostats","-i",str(path),"-map","0:a:0","-af",f"loudnorm=I={TARGET}:TP={TP}:LRA={LRA}:print_format=json","-f","null","-"]
 p=run_group(cmd,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,timeout=120,check=False)
 text=p.stderr or ""; blocks=re.findall(r"\{[\s\S]*?\}",text)
 for block in reversed(blocks):
  try:
   d=json.loads(block); vals={"lufs":float(d["input_i"]),"true_peak_db":float(d["input_tp"]),"lra":float(d.get("input_lra",0)),"threshold":float(d.get("input_thresh",-30)),"offset":float(d.get("target_offset",0))}
   if all(math.isfinite(v) for v in vals.values()): return vals
  except Exception: pass
 raise RuntimeError("loudnorm não retornou medição válida")

def remaster(path:Path,m:dict[str,float],*,linear:bool=True)->None:
 tmp=path.with_name(f".{path.stem}.master.{os.getpid()}.mp4")
 if linear:
  norm=(f"loudnorm=I={TARGET}:TP={TP}:LRA={LRA}:measured_I={m['lufs']}:measured_TP={m['true_peak_db']}:measured_LRA={m['lra']}:measured_thresh={m['threshold']}:offset={m['offset']}:linear=true:print_format=summary")
 else:
  # Bounded fallback: dynamic loudnorm avoids failing when linear mode cannot
  # satisfy the target for a short/limited source; limiter protects AAC output.
  norm=f"loudnorm=I={TARGET}:TP={TP}:LRA={LRA}:linear=false:print_format=summary"
 filt=f"{norm},alimiter=limit={10**(TP/20):.6f}:level=false"
 cmd=["ffmpeg","-y","-loglevel","error","-i",str(path),"-map","0:v:0","-map","0:a:0","-c:v","copy","-af",filt,"-c:a","aac","-b:a","192k","-ar","48000","-movflags","+faststart",str(tmp)]
 try:
  run_group(cmd,check=True,timeout=180)
  if not tmp.is_file() or tmp.stat().st_size<500000: raise RuntimeError("remaster inválido")
  os.replace(tmp,path)
 finally:
  try: tmp.unlink(missing_ok=True)
  except OSError: pass

def main()->int:
 if not VIDEO.is_file(): print(f"ERRO AUDIO FINALIZER: vídeo ausente: {VIDEO}"); return 1
 try:
  before=measure(VIDEO); tolerance_lufs=env_float("SAP_AUDIO_LUFS_TOLERANCE",0.7,0.1,3.0); tolerance_tp=env_float("SAP_AUDIO_TP_TOLERANCE",0.2,0.05,1.5)
  need=abs(before["lufs"]-TARGET)>tolerance_lufs or before["true_peak_db"]>TP+tolerance_tp
  if need:
   remaster(VIDEO,before,linear=True)
   after=measure(VIDEO)
   measurement_source="post_remaster_linear"
   # Codec true peaks can remain above target after a linear pass. Retry once
   # in dynamic mode, then measure the actual final AAC stream again.
   if after["true_peak_db"]>TP+0.35 or abs(after["lufs"]-TARGET)>max(1.0,tolerance_lufs):
    remaster(VIDEO,after,linear=False)
    after=measure(VIDEO)
    measurement_source="post_remaster_dynamic_retry"
  else:
   after=before
   measurement_source="unchanged_reuse"
  ok=abs(after["lufs"]-TARGET)<=max(1.0,tolerance_lufs) and after["true_peak_db"]<=TP+0.35
  payload={"short_id":SID,"version":"1.3","generated_at":datetime.now().astimezone().isoformat(timespec="seconds"),"target":{"lufs":TARGET,"true_peak_db":TP,"lra":LRA},"before":before,"remastered":need,"after":after,"measurement_source":measurement_source,"video_identity":file_identity(VIDEO),"status":"PASS" if ok else "BLOCK"}; atomic(REPORT,payload)
 except Exception as exc: print(f"ERRO AUDIO FINALIZER: {exc}"); return 1
 print(f"FINAL AUDIO: {payload['status']} | LUFS {after['lufs']:.2f} | TP {after['true_peak_db']:.2f} dB | remaster={'SIM' if need else 'NAO'}")
 return 0 if ok else 1
if __name__=="__main__":raise SystemExit(main())
