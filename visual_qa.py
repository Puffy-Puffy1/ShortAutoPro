#!/usr/bin/env python3
"""Measured visual QA for selected assets and final video."""
from __future__ import annotations
import collections,hashlib,json,os,re,subprocess,tempfile
from datetime import date
from pathlib import Path
from typing import Any
from subprocess_guard import run_group
BASE=Path(os.getenv("SHORTAUTOPRO_BASE",os.path.expanduser("~/ShortAutoPro"))).resolve();SID=os.getenv("SHORT_ID",date.today().isoformat()).strip();MEDIA=BASE/"imagens"/f"short_{SID}";VIDEO=BASE/"videos"/f"short_v6_{SID}.mp4";MAP=BASE/"roteiros"/f"scene_map_{SID}.json";VSCORE=BASE/"roteiros"/f"visual_score_{SID}.json";OUT=BASE/"reports"/"evolution"/f"visual_qa_{SID}.json"
def atomic(p:Path,x:Any)->None:
 p.parent.mkdir(parents=True,exist_ok=True);fd,t=tempfile.mkstemp(prefix=f".{p.name}.",suffix=".tmp",dir=str(p.parent))
 try:
  with os.fdopen(fd,"w",encoding="utf-8") as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
  os.replace(t,p)
 except Exception:
  try:os.unlink(t)
  except OSError:pass
  raise
def load(p:Path)->dict[str,Any]:
 try:x=json.loads(p.read_text(encoding="utf-8"));return x if isinstance(x,dict) else {}
 except Exception:return {}
def probe(p:Path)->dict[str,Any]:
 r=run_group(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height,codec_name,avg_frame_rate","-of","json",str(p)],capture_output=True,text=True,timeout=30)
 if r.returncode:return {}
 try:s=json.loads(r.stdout).get("streams",[]);return s[0] if s else {}
 except Exception:return {}
def sha(p:Path)->str:
 h=hashlib.sha256()
 with p.open("rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def filter_exists(name:str)->bool:
 try:return any(name in line for line in subprocess.check_output(["ffmpeg","-hide_banner","-filters"],text=True,stderr=subprocess.STDOUT,timeout=30).splitlines())
 except Exception:return False
def black_seconds(path:Path)->float:
 if not path.is_file():return 0.0
 r=run_group(["ffmpeg","-hide_banner","-nostats","-i",str(path),"-vf","blackdetect=d=0.12:pix_th=0.02","-an","-f","null","-"],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,timeout=120)
 return sum(float(x) for x in re.findall(r"black_duration:([0-9.]+)",r.stderr or ""))
def crop_detect(path:Path)->dict[str,int]|None:
 if not path.is_file() or not filter_exists("cropdetect"):return None
 r=run_group(["ffmpeg","-hide_banner","-nostats","-i",str(path),"-t","12","-vf","fps=1,cropdetect=24:16:0","-an","-f","null","-"],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,timeout=120)
 crops=re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)",r.stderr or "")
 if not crops:return None
 common=collections.Counter(crops).most_common(1)[0][0];w,h,x,y=map(int,common);return {"width":w,"height":h,"x":x,"y":y}
def blur_risk(path:Path)->float|None:
 if not filter_exists("blurdetect"):return None
 r=run_group(["ffmpeg","-hide_banner","-nostats","-i",str(path),"-vf","fps=1,scale=360:-2,blurdetect=block_width=32:block_height=32:block_pct=80","-frames:v","12","-an","-f","null","-"],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,text=True,timeout=90)
 vals=[float(x) for x in re.findall(r"blur(?:mean)?:\s*([0-9.]+)",r.stderr or "",re.I)];return round(sum(vals)/len(vals),3) if vals else None
def main()->int:
 issues=[];warnings=[];assets=[];hashes={};scene_map=load(MAP);scenes=scene_map.get("scenes",[]) if isinstance(scene_map.get("scenes"),list) else [];vscore=load(VSCORE);score_rows=vscore.get("scenes",[]) if isinstance(vscore.get("scenes"),list) else []
 if not MEDIA.is_dir():issues.append("media_directory_missing")
 else:
  files=sorted(p for p in MEDIA.iterdir() if p.is_file() and p.suffix.lower() in {".jpg",".jpeg",".png",".webp",".mp4",".mov",".webm"});expected=int(os.getenv("SHORT_QTD_CENAS","12"));primary=[p for p in files if re.fullmatch(r"scene_\d{2}\.(?:jpg|jpeg|png|webp|mp4|mov|webm)",p.name,re.I)]
  if len(primary)!=expected:issues.append(f"primary_scene_count:{len(primary)}/{expected}")
  for p in primary:
   meta=probe(p);w=int(meta.get("width",0) or 0);h=int(meta.get("height",0) or 0);digest=sha(p);dup=hashes.get(digest);hashes[digest]=p.name;scene_no=int(re.search(r"(\d{2})",p.name).group(1));scene=scenes[scene_no-1] if scene_no<=len(scenes) and isinstance(scenes[scene_no-1],dict) else {};score_row=score_rows[scene_no-1] if scene_no<=len(score_rows) and isinstance(score_rows[scene_no-1],dict) else {};provider=str(score_row.get("provider","") or "")
   item={"scene":scene_no,"file":p.name,"width":w,"height":h,"pixels":w*h,"duplicate_of":dup,"protected_zone":scene.get("protected_zone"),"main_subject":scene.get("main_subject"),"provider":provider or None}
   if w*h<320*180:issues.append(f"critical_resolution:{p.name}")
   elif w*h<1280*720:warnings.append(f"low_resolution:{p.name}")
   if dup:issues.append(f"exact_duplicate:{p.name}:{dup}")
   if h>0 and w/h>2.2:warnings.append(f"extreme_horizontal_crop_risk:{p.name}")
   if str(scene.get("protected_zone",""))=="center" and str(scene.get("shot_type","")) in {"portrait","close_up"} and w>h:warnings.append(f"face_crop_risk:{p.name}")
   if not provider:warnings.append(f"watermark_provenance_unknown:{p.name}")
   item["watermark_risk"]="LOW" if provider in {"Pexels","Pixabay","Wikimedia","Wikimedia Commons","Coverr"} else "UNKNOWN";assets.append(item)
 if not VIDEO.is_file():issues.append("final_video_missing")
 black=black_seconds(VIDEO) if VIDEO.is_file() else 0.0
 if black>0.22:issues.append(f"black_frames_seconds:{black:.3f}")
 crop=crop_detect(VIDEO) if VIDEO.is_file() else None
 if crop and (crop["width"]<1060 or crop["height"]<1880):warnings.append(f"black_bar_or_border_risk:{crop['width']}x{crop['height']}+{crop['x']}+{crop['y']}")
 blur=blur_risk(VIDEO) if VIDEO.is_file() else None
 score=100.0-len(issues)*18.0-len(warnings)*2.5;score=round(max(0,min(100,score)),1);status="PASS" if not issues and score>=85 else "REVIEW" if not issues else "BLOCK"
 payload={"short_id":SID,"version":"1.1","visual_qa_score":score,"status":status,"issues":issues,"warnings":warnings,"measurements":{"black_seconds":round(black,3),"cropdetect":crop,"blur_metric":blur,"blur_detector_available":filter_exists("blurdetect"),"crop_detector_available":filter_exists("cropdetect")},"assets":assets,"limitations":{"watermark":"provider/provenance risk only; no OCR/CV watermark classifier installed","face_crop":"storyboard/framing risk heuristic; no face detector installed"}};atomic(OUT,payload);print(f"VISUAL QA: {status} | score={score}/100 | issues={len(issues)} warnings={len(warnings)}");return 0 if status!="BLOCK" else 1
if __name__=="__main__":raise SystemExit(main())
