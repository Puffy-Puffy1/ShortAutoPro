#!/usr/bin/env python3
"""Safe artifact-validated resume for the single ShortAutoPro 3.0 pipeline."""
from __future__ import annotations
import argparse,fcntl,json,os,shutil,subprocess,sys
from pathlib import Path
from typing import Any
import shortautopro_evolution as evo
BASE=Path(os.getenv("SHORTAUTOPRO_BASE",os.path.expanduser("~/ShortAutoPro"))).resolve()
def professional_enabled()->bool:return os.getenv("SAP_PRO_EDIT","1").strip()=="1"
def read_json(path:Path)->dict[str,Any]:
 try:v=json.loads(path.read_text(encoding="utf-8"));return v if isinstance(v,dict) else {}
 except Exception:return {}
def nonempty(path:Path,minimum:int=1)->bool:
 try:return path.is_file() and path.stat().st_size>=minimum
 except OSError:return False
def expected_scenes()->int:
 try:v=int(os.getenv("SHORT_QTD_CENAS","12"))
 except ValueError:v=12
 return max(6,min(v,20))
def scene_count(sid:str)->int:
 d=read_json(BASE/"roteiros"/f"scene_map_{sid}.json");s=d.get("scenes",[]) if isinstance(d,dict) else [];return len(s) if isinstance(s,list) else 0
def media_ok(sid:str)->bool:
 r=read_json(BASE/"roteiros"/f"media_quality_{sid}.json")
 if str(r.get("status","")).upper()!="PASS" or r.get("critical"):return False
 folder=BASE/"imagens"/f"short_{sid}"
 if not folder.is_dir():return False
 valid=[p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {".jpg",".jpeg",".png",".webp",".mp4"} and p.stat().st_size>1000]
 return len(valid)>=expected_scenes()
def supervisor_ok(sid:str)->bool:
 d=read_json(BASE/"roteiros"/f"supervisor_{sid}.json");state=evo.load_state(sid);stage=state.get("stages",{}).get("production_supervisor.py",{}) if isinstance(state.get("stages"),dict) else {}
 return str(d.get("status","")).upper() in {"PASS","QUALITY_PASS","OK"} and isinstance(stage,dict) and stage.get("status")=="PASS"
def audio_ok(sid:str)->bool:return nonempty(BASE/"audios"/f"short_{sid}.mp3",5000)
def captions_ok(sid:str)->bool:
 p=BASE/"videos"/f"short_{sid}.ass"
 if not nonempty(p,200):return False
 try:return "Dialogue:" in p.read_text(encoding="utf-8",errors="ignore")
 except Exception:return False
def assembly_ok(sid:str)->bool:return nonempty(BASE/"temp"/sid/"video_sem_audio.mp4",100000)
def render_ok(sid:str)->bool:
 video=BASE/"videos"/f"short_v6_{sid}.mp4"
 if not nonempty(video,100000) or shutil.which("ffprobe") is None:return False
 try:
  raw=subprocess.check_output(["ffprobe","-v","error","-show_entries","stream=codec_name,codec_type,width,height","-of","json",str(video)],text=True,timeout=45);streams=json.loads(raw).get("streams",[]);v=next((x for x in streams if x.get("codec_type")=="video"),{});a=next((x for x in streams if x.get("codec_type")=="audio"),{})
  return v.get("codec_name")=="h264" and a.get("codec_name")=="aac" and int(v.get("width",0) or 0)==1080 and int(v.get("height",0) or 0)==1920
 except Exception:return False
def final_ok(sid:str)->bool:
 q=read_json(BASE/"manifests"/f"{sid}_quality.json");release=read_json(BASE/"manifests"/f"{sid}_release.json");return render_ok(sid) and q.get("approved") is True and release.get("decision") in {"PUBLISH","ACCEPTABLE"}
def pro_plan_ok(sid:str)->bool:
 d=read_json(BASE/"roteiros"/f"pro_edit_plan_{sid}.json");s=d.get("scenes",[]) if isinstance(d,dict) else [];return str(d.get("version","")).startswith("PRO_EDIT_") and isinstance(s,list) and len(s)==expected_scenes()
def base_boundary(sid:str)->str:
 if final_ok(sid):return "complete"
 if render_ok(sid):return "post_render"
 if assembly_ok(sid) and audio_ok(sid) and captions_ok(sid):return "post_assembly"
 if captions_ok(sid) and audio_ok(sid) and supervisor_ok(sid) and media_ok(sid):return "post_captions"
 if audio_ok(sid) and supervisor_ok(sid) and media_ok(sid):return "post_audio"
 if supervisor_ok(sid) and media_ok(sid) and scene_count(sid)==expected_scenes():return "post_media"
 return "full"
def boundary(sid:str)->str:
 point=base_boundary(sid)
 if professional_enabled() and point not in {"complete","full"} and not pro_plan_ok(sid):return "full"
 return point
def checkpoint(stage:str,status:str,title:str,sid:str)->None:
 try:evo.checkpoint(stage,status,title,sid)
 except Exception:pass
def run_python(sid:str,title:str,script:str,*args:str,allow:set[int]|None=None)->int:
 path=BASE/script
 if not path.is_file():raise RuntimeError(f"arquivo ausente: {script}")
 print(f"\n--- {title} ---");checkpoint(script,"start",title,sid);r=subprocess.run([sys.executable,str(path),*args],cwd=str(BASE),env=os.environ.copy());allowed=allow or {0}
 if r.returncode not in allowed:checkpoint(script,"fail",title,sid);raise RuntimeError(f"{script} falhou com código {r.returncode}")
 checkpoint(script,"pass",title,sid);return r.returncode
def acquire_generation_lock(sid:str):
 root=BASE/".locks"/"runs";root.mkdir(parents=True,exist_ok=True);handle=(root/f"{sid}.lock").open("a+")
 try:fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
 except OSError:handle.close();raise RuntimeError(f"produção {sid} já está em andamento")
 return handle
def full_rerun(sid:str)->int:
 main=BASE/"main.py"
 if not main.is_file():raise RuntimeError("main.py ausente")
 mode="profissional" if professional_enabled() else "standard rollback";print(f"Nenhum checkpoint parcial é seguro. Reexecutando pipeline oficial ({mode}).")
 env=os.environ.copy();env["SHORT_ID"]=sid;env["SAP_PRO_EDIT"]="1" if professional_enabled() else "0";return subprocess.run([sys.executable,str(main),"run"],cwd=str(BASE),env=env).returncode
def copy_download(sid:str)->str:
 final=BASE/"videos"/f"short_v6_{sid}.mp4";downloads=Path(os.path.expanduser("~/storage/shared/Download"))
 if downloads.is_dir() and final.is_file():
  target=downloads/f"ShortAutoPro_{sid}.mp4"
  try:shutil.copy2(final,target);return str(target) if target.stat().st_size>0 else str(final)
  except Exception:pass
 return str(final)
def final_gates(sid:str)->int:
 for title,script,args in [("EVOLUTION E2E","shortautopro_evolution.py",("e2e",)),("QUALITY GATE","quality_check.py",()),("PUBLISH PACK","publish_pack.py",()),("SOURCE LEDGER","source_ledger.py",()),("PUBLISH INTEGRITY","publish_integrity_gate.py",()),("PRODUCTION MANIFEST","production_manifest.py",()),("FINAL QUALITY","final_quality.py",())]:run_python(sid,title,script,*args)
 qargs=["quality-score"]+(["--enforce"] if os.getenv("SAP_EVOLUTION_ENFORCE","0")=="1" else []);run_python(sid,"EVOLUTION QUALITY SCORE","shortautopro_evolution.py",*qargs)
 if professional_enabled():run_python(sid,"PROFESSIONAL QUALITY GATE","professional_quality_gate.py")
 return run_python(sid,"SHORTAUTOPRO RELEASE GATE","release_gate.py","--enforce",allow={0,20})
def resume(sid:str)->int:
 os.environ["SHORT_ID"]=sid;point=boundary(sid);pro=professional_enabled();mode="PROFESSIONAL" if pro else "STANDARD_ROLLBACK";print("========================================\n SHORTAUTOPRO 3.0 - SAFE RESUME\n========================================");print(f"ID: {sid}\nMode: {mode}\nBoundary: {point}\n")
 if point=="complete":print("Produção já aprovada pelo Release Gate.");return 0
 if point=="full":return full_rerun(sid)
 lock=acquire_generation_lock(sid)
 try:
  order={"post_media":1,"post_audio":2,"post_captions":3,"post_assembly":4,"post_render":5};rank=order[point]
  if rank<=1:
   if pro:
    run_python(sid,"PROFESSIONAL EDIT DIRECTOR","professional_edit_director.py");run_python(sid,"PROFESSIONAL EDIT AUTO-REPAIR","professional_edit_repair.py");run_python(sid,"MULTI-ASSET DIRECTOR","multi_asset_director.py")
   run_python(sid,"RETENTION ENGINE","retention_engine.py","--repair","--enforce");run_python(sid,"SOUND DESIGN","sound_design_engine.py");run_python(sid,"FINAL EDITORIAL GATE","editorial_gate.py");run_python(sid,"SPEECH DIRECTOR","speech_director.py");run_python(sid,"GERANDO VOZ PIPER","audio.py")
  if rank<=2:
   run_python(sid,"WHISPER + LEGENDA","legenda_dinamica.py")
   if pro:run_python(sid,"PROFESSIONAL CAPTION DIRECTOR","professional_caption_director.py");run_python(sid,"CAPTION SAFE-ZONE GUARD","caption_layout_guard.py")
   run_python(sid,"CAPTION AUDIT","shortautopro_evolution.py","caption-audit")
  if rank<=3:run_python(sid,"PROFESSIONAL MULTI-BEAT ASSEMBLER" if pro else "STANDARD ASSEMBLER","video_professional.py" if pro else "video.py")
  if rank<=4:
   run_python(sid,"RENDER FINAL V6","v6_runtime.py")
   if not render_ok(sid):raise RuntimeError("V6 terminou sem artefato técnico válido")
  run_python(sid,"FINAL AUDIO MASTER","audio_finalizer.py");run_python(sid,"VISUAL QA","visual_qa.py")
  code=final_gates(sid)
  if code==20:
   if pro:run_python(sid,"REPAIR EDIT","professional_edit_repair.py")
   run_python(sid,"REPAIR RETENTION","retention_engine.py","--repair");run_python(sid,"REPAIR SOUND","sound_design_engine.py");run_python(sid,"REASSEMBLE","video_professional.py" if pro else "video.py");run_python(sid,"RERENDER","v6_runtime.py");run_python(sid,"FINAL AUDIO MASTER","audio_finalizer.py");run_python(sid,"VISUAL QA","visual_qa.py");code=final_gates(sid)
  if code==20 or not final_ok(sid):raise RuntimeError("retomada terminou sem Release Gate aprovado")
  run_python(sid,"REGISTRANDO ASSUNTO","register_topic.py");destination=copy_download(sid);evo.finish_production("SUCCESS",sid);print(f"\nRESUME_STATUS=PASS\nMODE={mode}\nVídeo: {destination}");return 0
 except Exception as exc:evo.finish_production("FAILED",sid);print(f"RESUME_ERROR={type(exc).__name__}: {exc}",file=sys.stderr);return 1
 finally:
  try:fcntl.flock(lock.fileno(),fcntl.LOCK_UN);lock.close()
  except Exception:pass
def latest_incomplete()->str|None:
 if not evo.STATE_DIR.is_dir():return None
 states=sorted(evo.STATE_DIR.glob("*.json"),key=lambda p:p.stat().st_mtime,reverse=True)
 for path in states:
  data=read_json(path)
  if str(data.get("production_status","")).upper()!="SUCCESS":return path.stem
 return states[0].stem if states else None
def main()->int:
 p=argparse.ArgumentParser();p.add_argument("--short-id",default=None);p.add_argument("--status",action="store_true");args=p.parse_args();sid=args.short_id or os.getenv("SHORT_ID","").strip() or latest_incomplete()
 if not sid:print("Nenhuma produção encontrada para retomar.");return 0
 if args.status:
  payload={"short_id":sid,"mode":"PROFESSIONAL" if professional_enabled() else "STANDARD_ROLLBACK","boundary":boundary(sid),"plan":evo.resume_plan(sid)}
  if professional_enabled():payload["professional_plan"]=pro_plan_ok(sid)
  print(json.dumps(payload,ensure_ascii=False,indent=2));return 0
 return resume(sid)
if __name__=="__main__":raise SystemExit(main())
