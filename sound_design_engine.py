#!/usr/bin/env python3
"""Build a deterministic, profile-aware music/SFX/ducking plan."""
from __future__ import annotations
import json, os, tempfile
from datetime import date
from pathlib import Path
from typing import Any

BASE=Path(os.getenv("SHORTAUTOPRO_BASE",os.path.expanduser("~/ShortAutoPro"))).resolve(); SID=os.getenv("SHORT_ID",date.today().isoformat()).strip(); PROFILE=os.getenv("SAP_CHANNEL_PROFILE","default").strip() or "default"
R=BASE/"roteiros"; MAP=R/f"scene_map_{SID}.json"; PLAN=R/f"pro_edit_plan_{SID}.json"; OUT=R/f"sound_design_{SID}.json"
PRESETS={
 "true_crime":{"music_mood":"dark_tension","music_volume":0.035,"duck_ratio":7.0,"ambience":"restrained","sfx_density":0.24},
 "cinepulsar":{"music_mood":"cinematic_energy","music_volume":0.050,"duck_ratio":6.0,"ambience":"cinematic","sfx_density":0.34},
 "psicotoon":{"music_mood":"retro_curiosity","music_volume":0.044,"duck_ratio":6.0,"ambience":"retro","sfx_density":0.30},
 "default":{"music_mood":"light_suspense","music_volume":0.040,"duck_ratio":6.0,"ambience":"documentary","sfx_density":0.26},
}

def load(p:Path)->dict[str,Any]:
 try:
  x=json.loads(p.read_text(encoding="utf-8")); return x if isinstance(x,dict) else {}
 except Exception:return {}

def atomic(p:Path,x:Any)->None:
 p.parent.mkdir(parents=True,exist_ok=True); fd,t=tempfile.mkstemp(prefix=f".{p.name}.",suffix=".tmp",dir=str(p.parent))
 try:
  with os.fdopen(fd,"w",encoding="utf-8") as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
  os.replace(t,p)
 except Exception:
  try:os.unlink(t)
  except OSError:pass
  raise

def main()->int:
 scene_map=load(MAP); scenes=scene_map.get("scenes",[]) if isinstance(scene_map.get("scenes"),list) else []
 if not scenes: print("ERRO SOUND DESIGN: scene_map ausente"); return 1
 preset=dict(PRESETS.get(PROFILE,PRESETS["default"])); events=[]
 high={"hook","cold_open","turn","turning_point","reveal","climax","payoff"}; evidence={"evidence","document","explanation"}
 max_events=max(1,round(len(scenes)*preset["sfx_density"]))
 for i,s in enumerate(scenes,1):
  role=str(s.get("narrative_role","")).lower(); emotion=str(s.get("emotion",s.get("mood",""))).lower()
  kind=None
  if i==1: kind="hit_soft"
  elif role in {"turn","turning_point","reveal","climax"}: kind="riser_hit"
  elif role in evidence: kind="subtle_tick"
  elif role=="payoff": kind="resolve_soft"
  if kind and len(events)<max_events: events.append({"scene":i,"type":kind,"emotion":emotion,"max_duration":0.8,"curated_only":os.getenv("SAP_PRO_ALLOW_GENERATED_SFX","0")!="1"})
 out={"short_id":SID,"version":"1.0","profile":PROFILE,**preset,"voice_priority":True,"ducking":{"enabled":True,"threshold":0.032,"ratio":preset["duck_ratio"],"attack_ms":18,"release_ms":300},"events":events,"rules":{"music_competes_with_voice":False,"generated_sfx_allowed":os.getenv("SAP_PRO_ALLOW_GENERATED_SFX","0")=="1","max_sfx_events":max_events}}
 atomic(OUT,out)
 # Feed the existing professional renderer through its canonical plan.
 plan=load(PLAN)
 if plan:
  audio=plan.get("audio") if isinstance(plan.get("audio"),dict) else {}; audio["music_volume"]=preset["music_volume"]; audio["music_mood"]=preset["music_mood"]; audio["duck_ratio"]=preset["duck_ratio"]; plan["audio"]=audio; plan["sound_design_report"]=str(OUT); atomic(PLAN,plan)
 print(f"SOUND DESIGN: PASS | mood={preset['music_mood']} | sfx_events={len(events)}")
 return 0
if __name__=="__main__":raise SystemExit(main())
