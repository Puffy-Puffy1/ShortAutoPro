#!/usr/bin/env python3
"""Safe storage preflight and cleanup for ShortAutoPro."""
from __future__ import annotations
import argparse,fcntl,json,os,shutil,tempfile,time
from datetime import date
from pathlib import Path
from typing import Any
from runtime_config import env_float, env_int
BASE=Path(os.getenv("SHORTAUTOPRO_BASE",os.path.expanduser("~/ShortAutoPro"))).resolve();SID=os.getenv("SHORT_ID",date.today().isoformat()).strip();OUT=BASE/"reports"/"evolution"/f"storage_{SID}.json"
def atomic(p:Path,x:Any)->None:
 p.parent.mkdir(parents=True,exist_ok=True);fd,t=tempfile.mkstemp(prefix=f".{p.name}.",suffix=".tmp",dir=str(p.parent))
 try:
  with os.fdopen(fd,"w",encoding="utf-8") as f:json.dump(x,f,ensure_ascii=False,indent=2);f.write("\n");f.flush();os.fsync(f.fileno())
  os.replace(t,p)
 except Exception:
  try:os.unlink(t)
  except OSError:pass
  raise
def min_free_bytes()->int:
 value=env_float("SAP_MIN_FREE_GB",1.2,0.5,20.0)
 return int(value*1024**3)
def safe_mtime(p:Path)->float:
 try:return p.stat().st_mtime
 except OSError:return 0.0
def size(p:Path)->int:
 if p.is_file():
  try:return p.stat().st_size
  except OSError:return 0
 total=0
 try:iterator=p.rglob("*")
 except OSError:return 0
 for x in iterator:
  try:
   if x.is_file():total+=x.stat().st_size
  except OSError:continue
 return total
def candidates()->list[Path]:
 out=[]
 for root,pat in ((BASE/"imagens","short_*"),(BASE/"temp","*")):
  if root.is_dir():out.extend(x for x in root.glob(pat) if x.is_dir())
 return out
def candidate_groups()->list[list[Path]]:
 groups=[]
 for root,pat in ((BASE/"imagens","short_*"),(BASE/"temp","*")):
  items=[x for x in root.glob(pat) if x.is_dir()] if root.is_dir() else []
  groups.append(sorted(items,key=safe_mtime,reverse=True))
 return groups
def _held_lock(lock:Path)->bool:
 try:
  with lock.open("a+") as handle:
   try:
    fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:
    return True
   fcntl.flock(handle.fileno(),fcntl.LOCK_UN)
 except OSError:
  # An unreadable lock is not evidence that the production is inactive.
  return True
 # Never unlink a flock file: a waiting process may already own its inode.
 return False
def active_ids()->set[str]:
 out:set[str]=set()
 runs=BASE/".locks"/"runs"
 if runs.is_dir():
  for lock in runs.glob("*.lock"):
   sid=lock.stem.strip()
   if sid and _held_lock(lock):out.add(sid)
 legacy=BASE/".locks"/"active_ids"
 if legacy.is_dir():
  for item in legacy.iterdir():
   sid=item.name.strip()
   if sid:out.add(sid)
 # Batch items awaiting recovery still depend on partial media/temp artifacts.
 # Protect them even while no per-run flock is currently held.
 batch=BASE/"queue"/"batch_state.json"
 try:
  data=json.loads(batch.read_text(encoding="utf-8")) if batch.is_file() else {}
  items=data.get("items",[]) if isinstance(data,dict) else []
  for item in items if isinstance(items,list) else []:
   if not isinstance(item,dict):continue
   if str(item.get("status","")).lower() in {"running","recovering","retry_pending","blocked_global"}:
    sid=str(item.get("short_id","")).strip()
    if sid:out.add(sid)
 except Exception as exc:
  print(f"STORAGE_BATCH_STATE=UNREADABLE {type(exc).__name__}:{str(exc)[:100]}")
 if SID:out.add(SID)
 return out
def protected(p:Path)->bool:
 name=p.name
 for sid in active_ids():
  if name==sid or name==f"short_{sid}" or sid in name:return True
 return False
def cleanup(execute:bool)->dict[str,Any]:
 keep=env_int("SHORT_STORAGE_KEEP_PROJECTS",3,1,20);days=env_int("SHORT_STORAGE_KEEP_DAYS",7,1,90);cutoff=time.time()-days*86400;remove=[]
 # Apply retention independently to media projects and temp projects so
 # transient temp directories cannot consume the retention slots of media.
 for items in candidate_groups():
  for i,p in enumerate(items):
   if protected(p):continue
   old=safe_mtime(p)<cutoff
   if i>=keep or old:remove.append(p)
 freed=sum(size(p) for p in remove)
 removed=[]
 skipped_active=[]
 if execute:
  for p in remove:
   # Re-check immediately before deletion because another production may have
   # started after the cleanup plan was built.
   if protected(p):
    skipped_active.append(p);continue
   # Generic temp directories cannot be safely attributed to one Short.
   # Re-snapshot active runs immediately before every deletion so a production
   # that started after the cleanup plan was built cannot lose its temp data.
   if p.parent==BASE/"temp":
    current_active=active_ids()
    if len(current_active)>1:
     skipped_active.append(p);continue
   try:
    shutil.rmtree(p);removed.append(p)
   except OSError:pass
  for p in BASE.rglob("__pycache__"):
   if p.is_dir():
    try:shutil.rmtree(p)
    except OSError:pass
 return {"execute":execute,"keep_projects":keep,"keep_days":days,"planned":[str(p.relative_to(BASE)) for p in remove],"removed":[str(p.relative_to(BASE)) for p in removed],"skipped_active":[str(p.relative_to(BASE)) for p in skipped_active],"estimated_freed_bytes":freed}
def main()->int:
 ap=argparse.ArgumentParser();ap.add_argument("command",choices=["preflight","cleanup","status"],nargs="?",default="status");ap.add_argument("--execute",action="store_true");args=ap.parse_args();usage=shutil.disk_usage(BASE);min_free=min_free_bytes();payload={"short_id":SID,"version":"1.1","disk":{"total":usage.total,"used":usage.used,"free":usage.free,"free_gb":round(usage.free/1024**3,2),"min_free_gb":round(min_free/1024**3,2)}}
 if args.command=="preflight":payload["status"]="PASS" if usage.free>=min_free else "BLOCK";atomic(OUT,payload);print(json.dumps(payload,indent=2));return 0 if payload["status"]=="PASS" else 1
 if args.command=="cleanup":payload["cleanup"]=cleanup(args.execute);payload["status"]="PASS"
 else:payload["status"]="PASS"
 atomic(OUT,payload);print(json.dumps(payload,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
