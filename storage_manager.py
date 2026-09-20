#!/usr/bin/env python3
"""Safe storage preflight and cleanup for ShortAutoPro."""
from __future__ import annotations
import argparse,fcntl,json,os,shutil,tempfile,time
from datetime import date
from pathlib import Path
from typing import Any
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
def size(p:Path)->int:
 try:
  if p.is_file():return p.stat().st_size
  return sum(x.stat().st_size for x in p.rglob("*") if x.is_file())
 except Exception:return 0
def candidates()->list[Path]:
 out=[]
 for root,pat in ((BASE/"imagens","short_*"),(BASE/"temp","*")):
  if root.is_dir():out.extend(x for x in root.glob(pat) if x.is_dir())
 return out
def _held_lock(lock:Path)->bool:
 try:
  with lock.open("a+") as handle:
   try:
    fcntl.flock(handle.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:
    return True
   fcntl.flock(handle.fileno(),fcntl.LOCK_UN)
 except OSError:
  return False
 try:lock.unlink(missing_ok=True)
 except OSError:pass
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
 if SID:out.add(SID)
 return out
def protected(p:Path)->bool:
 name=p.name
 for sid in active_ids():
  if name==sid or name==f"short_{sid}" or sid in name:return True
 return False
def cleanup(execute:bool)->dict[str,Any]:
 keep=max(1,min(20,int(os.getenv("SHORT_STORAGE_KEEP_PROJECTS","3"))));days=max(1,min(90,int(os.getenv("SHORT_STORAGE_KEEP_DAYS","7"))));cutoff=time.time()-days*86400;items=sorted(candidates(),key=lambda p:p.stat().st_mtime if p.exists() else 0,reverse=True);remove=[]
 for i,p in enumerate(items):
  if protected(p):continue
  old=(p.stat().st_mtime<cutoff) if p.exists() else False
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
 ap=argparse.ArgumentParser();ap.add_argument("command",choices=["preflight","cleanup","status"],nargs="?",default="status");ap.add_argument("--execute",action="store_true");args=ap.parse_args();usage=shutil.disk_usage(BASE);min_free=int(float(os.getenv("SAP_MIN_FREE_GB","1.2"))*1024**3);payload={"short_id":SID,"version":"1.0","disk":{"total":usage.total,"used":usage.used,"free":usage.free,"free_gb":round(usage.free/1024**3,2),"min_free_gb":round(min_free/1024**3,2)}}
 if args.command=="preflight":payload["status"]="PASS" if usage.free>=min_free else "BLOCK";atomic(OUT,payload);print(json.dumps(payload,indent=2));return 0 if payload["status"]=="PASS" else 1
 if args.command=="cleanup":payload["cleanup"]=cleanup(args.execute);payload["status"]="PASS"
 else:payload["status"]="PASS"
 atomic(OUT,payload);print(json.dumps(payload,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
