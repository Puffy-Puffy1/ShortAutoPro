#!/usr/bin/env python3
"""Unified ShortAutoPro confidence score and final release decision."""
from __future__ import annotations
import argparse,hashlib,json,math,os,tempfile
from datetime import date,datetime
from pathlib import Path
from typing import Any
BASE=Path(os.getenv("SHORTAUTOPRO_BASE",os.path.expanduser("~/ShortAutoPro"))).resolve();SID=os.getenv("SHORT_ID",date.today().isoformat()).strip();R=BASE/"roteiros";M=BASE/"manifests";E=BASE/"reports"/"evolution";I=BASE/"reports"/"intelligence";OUT=M/f"{SID}_release.json";RENDER_IDENTITY=M/f"{SID}_render_identity.json";PRODUCTION_MANIFEST=M/f"{SID}.json";FINAL_QUALITY=M/f"{SID}_quality.json"
def load(p:Path)->dict[str,Any]:
 try:
  x=json.loads(p.read_text(encoding="utf-8"));return x if isinstance(x,dict) else {}
 except Exception:return {}
def num(v:Any,d:float=0.0)->float:
 try:x=float(v);return x if math.isfinite(x) else d
 except Exception:return d
def atomic(p:Path,x:Any)->None:
 p.parent.mkdir(parents=True,exist_ok=True);fd,t=tempfile.mkstemp(prefix=f".{p.name}.",suffix=".tmp",dir=str(p.parent))
 try:
  with os.fdopen(fd,"w",encoding="utf-8") as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
  os.replace(t,p)
 except Exception:
  try:os.unlink(t)
  except OSError:pass
  raise
def clamp(x:float)->float:return round(max(0,min(100,x)),1)
def read_text(p:Path)->str:
 try:return p.read_text(encoding="utf-8").strip()
 except Exception:return ""
def text_sha(v:str)->str:return hashlib.sha256(str(v or "").encode("utf-8")).hexdigest()
def file_sha(p:Path)->str:
 try:
  h=hashlib.sha256()
  with p.open("rb") as f:
   for chunk in iter(lambda:f.read(1024*1024),b""):h.update(chunk)
  return h.hexdigest()
 except OSError:return ""
def brain_snapshot()->dict[str,Any]:
 try:
  import shortauto_brain as brain
  prep=brain.prepare(SID)
  _,quality=brain.quality(SID,enforce=False)
  return {"status":"PASS","prepare":{"evidence_coverage":prep.get("evidence_map",{}).get("coverage"),"story_arc_ok":prep.get("story_graph",{}).get("arc_ok"),"hook_ab_ready":prep.get("hook_ab",{}).get("ab_ready"),"channel":prep.get("channel"),"autonomy_mode":prep.get("autonomy_mode")},"quality":quality}
 except Exception as exc:
  return {"status":"ERROR","error":f"{type(exc).__name__}:{exc}"}
def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument("--enforce",action="store_true");args=ap.parse_args()
 retention=load(R/f"retention_{SID}.json");continuity=load(R/f"visual_continuity_{SID}.json");vscore=load(R/f"visual_score_{SID}.json");vqa=load(E/f"visual_qa_{SID}.json");audio=load(E/f"final_audio_{SID}.json");pro=load(M/f"{SID}_professional.json");legacy=load(M/f"{SID}_quality.json");media=load(R/f"media_quality_{SID}.json");caption=load(R/f"pro_caption_{SID}.json");caption_layout=load(R/f"caption_layout_{SID}.json");vd=load(R/f"visual_director_{SID}.json")
 factual_ok=bool(legacy.get("approved",False));critical=[]
 manifest_sha_now=file_sha(PRODUCTION_MANIFEST);quality_input=legacy.get("input_identity",{}) if isinstance(legacy.get("input_identity"),dict) else {};quality_manifest_sha=str(quality_input.get("production_manifest_sha256","") or "")
 if not manifest_sha_now:critical.append("production_manifest_identity_missing")
 elif not quality_manifest_sha:critical.append("final_quality_manifest_identity_missing")
 elif quality_manifest_sha!=manifest_sha_now:critical.append("final_quality_manifest_identity_mismatch")
 render_identity=load(RENDER_IDENTITY);current_topic=read_text(R/f"used_topic_{SID}.txt") or read_text(R/f"topic_{SID}.txt");current_topic_sha=text_sha(current_topic) if current_topic else ""
 identity_enforce=os.getenv("SAP_ARTIFACT_IDENTITY_ENFORCE","1")=="1"
 if identity_enforce:
  if not render_identity:critical.append("render_identity_missing")
  else:
   if str(render_identity.get("short_id",""))!=SID:critical.append("render_short_id_mismatch")
   render_topic_sha=str(render_identity.get("topic_sha256","") or "")
   if not current_topic_sha:critical.append("canonical_topic_identity_missing")
   elif not render_topic_sha:critical.append("render_topic_identity_missing")
   elif render_topic_sha!=current_topic_sha:critical.append("render_topic_identity_mismatch")
 if not factual_ok:critical.append("legacy_final_quality_not_approved")
 if not media:critical.append("media_quality_report_missing")
 elif str(media.get("status","")).upper()!="PASS":critical.append("media_quality_not_pass")
 neutral_media=media.get("neutral_editorial_scenes",[]) if isinstance(media.get("neutral_editorial_scenes"),list) else []
 if neutral_media:critical.append("neutral_editorial_media_present:"+",".join(map(str,neutral_media)))
 if not vqa:critical.append("visual_qa_missing")
 elif str(vqa.get("status","")).upper()=="BLOCK":critical.append("visual_qa_block")
 rendered_content=vqa.get("measurements",{}).get("rendered_content",{}) if isinstance(vqa.get("measurements"),dict) else {}
 if vqa and (
  not isinstance(rendered_content,dict)
  or not rendered_content.get("available")
  or not rendered_content.get("scene_timeline_available")
  or rendered_content.get("opening_blank")
  or rendered_content.get("blank_scenes")
 ):critical.append("rendered_visual_content_not_verified")
 if str(audio.get("status","PASS")).upper()=="BLOCK":critical.append("audio_master_block")
 script=clamp((num(retention.get("components",{}).get("hook"),80)+num(retention.get("components",{}).get("language"),80)+num(retention.get("components",{}).get("payoff"),80))/3)
 media_score=num(pro.get("components",{}).get("media"),100 if str(media.get("status","")).upper()=="PASS" else 75)
 visual=clamp(0.18*num(vd.get("visual_director_score"),80)+0.20*num(continuity.get("visual_continuity_score"),80)+0.37*num(vscore.get("visual_score"),80)+0.25*num(vqa.get("visual_qa_score"),80))
 if audio:
  aft=audio.get("after",{}) if isinstance(audio.get("after"),dict) else {};target=audio.get("target",{}) if isinstance(audio.get("target"),dict) else {};le=abs(num(aft.get("lufs"),-14)-num(target.get("lufs"),-14));tp_over=max(0,num(aft.get("true_peak_db"),-1.5)-num(target.get("true_peak_db"),-1.5));audio_score=clamp(100-le*12-tp_over*18)
 else:audio_score=num(pro.get("components",{}).get("audio_master"),75)
 subtitle_base=num(caption.get("score"),num(pro.get("components",{}).get("captions"),75));layout_score=num(caption_layout.get("score"),subtitle_base);subtitle=clamp(0.75*subtitle_base+0.25*layout_score)
 ret=clamp(num(retention.get("retention_score"),75));technical=clamp(num(pro.get("components",{}).get("technical"),100 if factual_ok else 0))
 components={"script_score":script,"media_score":clamp(media_score),"visual_score":visual,"audio_score":audio_score,"subtitle_score":subtitle,"retention_score":ret,"technical_score":technical}
 weights={"script_score":0.14,"media_score":0.16,"visual_score":0.18,"audio_score":0.12,"subtitle_score":0.10,"retention_score":0.15,"technical_score":0.15};score=round(sum(components[k]*weights[k] for k in weights),1)
 brain=brain_snapshot();brain_enforce=os.getenv("SAP_BRAIN_ENFORCE","0")=="1";brain_quality=brain.get("quality",{}) if isinstance(brain.get("quality"),dict) else {};brain_budget=brain_quality.get("quality_budget",{}) if isinstance(brain_quality.get("quality_budget"),dict) else {};intelligence=load(I/f"final_{SID}.json");intelligence_enforce=os.getenv("SAP_INTELLIGENCE_ENFORCE","0")=="1";intelligence_qa=intelligence.get("explainable_qa",{}) if isinstance(intelligence.get("explainable_qa"),dict) else {};intelligence_conf=intelligence.get("confidence_automation",{}) if isinstance(intelligence.get("confidence_automation"),dict) else {}
 if brain_enforce and brain.get("status")!="PASS":critical.append("shortauto_brain_error")
 if brain_enforce and str(brain_budget.get("status","")).upper()=="BLOCK":critical.append("shortauto_brain_quality_budget_block")
 if brain_enforce and str(brain_quality.get("decision","")).upper()=="BLOCK":critical.append("shortauto_brain_autonomy_block")
 if intelligence_enforce and not intelligence:critical.append("intelligence_report_missing")
 if intelligence_enforce and str(intelligence_conf.get("decision","")).upper()=="BLOCK":critical.append("intelligence_confidence_block")
 if critical:decision="BLOCK"
 elif score>=90:decision="PUBLISH"
 elif score>=80:decision="ACCEPTABLE"
 elif score>=70:decision="REPAIR"
 else:decision="BLOCK"
 actions=[]
 weak_scenes=vscore.get("weak_scenes",[]) if isinstance(vscore.get("weak_scenes"),list) else []
 if components["media_score"]<80 or components["visual_score"]<80:actions.append("replace_weak_or_generic_media" + ((":"+",".join(map(str,weak_scenes))) if weak_scenes else ""))
 if components["retention_score"]<80:actions.append("repair_pacing")
 if components["audio_score"]<90:actions.append("remaster_audio")
 if components["subtitle_score"]<85:actions.append("repair_caption_layout")
 if str(brain_budget.get("status","")).upper()=="BLOCK":actions.append("review_shortauto_brain_quality_budget")
 if str(intelligence_conf.get("decision","")).upper()=="REPAIR":actions.append("review_intelligence_explainable_qa")
 input_identity={"production_manifest_sha256":file_sha(PRODUCTION_MANIFEST),"final_quality_sha256":file_sha(FINAL_QUALITY)}
 if not input_identity["production_manifest_sha256"]:critical.append("production_manifest_identity_missing")
 if not input_identity["final_quality_sha256"]:critical.append("final_quality_identity_missing")
 if critical:decision="BLOCK"
 payload={"short_id":SID,"version":"RELEASE_GATE_1.6_VISUAL_CONTENT_INTEGRITY","generated_at":datetime.now().astimezone().isoformat(timespec="seconds"),"shortautopro_score":score,"decision":decision,"components":components,"weights":weights,"critical":critical,"repair_actions":actions,"visual_multiscore":vscore,"shortauto_brain":brain,"brain_enforced":brain_enforce,"shortauto_intelligence":intelligence,"intelligence_enforced":intelligence_enforce,"intelligence_qa_score":num(intelligence_qa.get("score"),0),"artifact_identity":{"enforced":identity_enforce,"current_topic":current_topic,"current_topic_sha256":current_topic_sha,"render_identity":render_identity},"input_identity":input_identity};atomic(OUT,payload);print(json.dumps(payload,ensure_ascii=False,indent=2))
 if args.enforce and decision=="BLOCK":return 1
 if args.enforce and decision=="REPAIR":return 20
 return 0
if __name__=="__main__":raise SystemExit(main())
