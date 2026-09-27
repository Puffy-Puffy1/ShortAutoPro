#!/usr/bin/env python3
"""Canonical sequential batch runtime for ShortAutoPro.

Owns batch identity, per-item state, fresh/resume selection, retry scheduling,
global-blocker classification, exact release verification and atomic state.
Shell entrypoints are wrappers only.
"""
from __future__ import annotations
import argparse, fcntl, json, os, re, shutil, signal, subprocess, sys, tempfile, time
from datetime import datetime
from pathlib import Path
from typing import Any

BASE=Path(os.getenv("SHORTAUTOPRO_BASE",Path.home()/"ShortAutoPro")).resolve()
QUEUE=BASE/"queue"; STATE=QUEUE/"batch_state.json"; REPORTS=BASE/"reports"/"batches"
ITEM_STATES={"QUEUED","RUNNING","RETRY_PENDING","RECOVERING","COMPLETED","FAILED_PERMANENT","BLOCKED_GLOBAL","CANCELLED"}
TRANSIENT_CODES={"MEDIA_PROVIDER_TIMEOUT","MEDIA_RATE_LIMIT","MEDIA_INCOMPLETE","AI_TIMEOUT","AI_TEMPORARY","RENDER_TIMEOUT","RENDER_FAILURE","LOCK_ACTIVE","UNKNOWN_EXCEPTION"}
GLOBAL_CODES={"STORAGE_LOW","CONFIG_INVALID","RUNTIME_MISSING","STATE_CORRUPT"}
ENV_DROP={"SHORT_ID","SAP_REUSE_SHORT_ID","SHORT_TOPIC_EXACT","SHORT_ALLOW_REPEAT_TOPIC","SAP_BATCH_RECOVERY","SAP_RESUME_SHORT_ID"}
MAX_ATTEMPTS=max(1,min(int(os.getenv("SHORT_BATCH_MAX_ATTEMPTS","3")),5))
LOCK_FILE=QUEUE/".batch_runtime.lock"

class BatchLock:
    def __enter__(self):
        QUEUE.mkdir(parents=True,exist_ok=True); self.f=LOCK_FILE.open("a+")
        try: fcntl.flock(self.f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            self.f.close(); raise RuntimeError("LOCK_ACTIVE:batch")
        self.f.seek(0); self.f.truncate(); self.f.write(str(os.getpid())); self.f.flush(); return self
    def __exit__(self,*_):
        try: fcntl.flock(self.f.fileno(),fcntl.LOCK_UN)
        finally: self.f.close()

MIN_FREE_MB=max(256,int(os.getenv("SHORT_BATCH_MIN_FREE_MB","1024")))

def now(): return datetime.now().astimezone().isoformat(timespec="seconds")
def atomic(path:Path,data:Any):
    path.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(prefix="."+path.name+".",suffix=".tmp",dir=str(path.parent))
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(data,f,ensure_ascii=False,indent=2,sort_keys=True); f.write("\n"); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,path); tmp=""
    finally:
        if tmp:
            try: os.unlink(tmp)
            except OSError: pass

def load_state():
    try:
        d=json.loads(STATE.read_text(encoding="utf-8"))
    except Exception as e: raise RuntimeError(f"STATE_CORRUPT:{e}") from e
    if not isinstance(d,dict) or not isinstance(d.get("items"),list): raise RuntimeError("STATE_CORRUPT:schema")
    return d

def artifact_exists(sid):
    return any(p.exists() for p in [BASE/".sap_state"/f"pipeline_{sid}.json",BASE/"roteiros"/f"scene_map_{sid}.json",BASE/"roteiros"/f"short_{sid}.txt",BASE/"videos"/f"short_v6_{sid}.mp4"])

def release_ok(sid,env):
    p=subprocess.run([sys.executable,str(BASE/"release_artifact_guard.py"),"--short-id",sid],cwd=BASE,env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    return p.returncode==0

def clean_env(sid):
    env=os.environ.copy()
    for k in ENV_DROP: env.pop(k,None)
    env["SHORTAUTOPRO_BASE"]=str(BASE); env["SHORT_ID"]=sid
    return env

def classify(text,code):
    t=(text or "").lower()
    if any(x in t for x in ("no space left","storage_low","disk full")): return "GLOBAL_BLOCKER","STORAGE_LOW"
    if any(x in t for x in ("config_invalid","config.sh não encontrado","ffmpeg ausente","python ausente")): return "GLOBAL_BLOCKER","CONFIG_INVALID"
    if "429" in t or "rate_limit" in t: return "RECOVERABLE","MEDIA_RATE_LIMIT"
    if "provider" in t and "timeout" in t: return "RECOVERABLE","MEDIA_PROVIDER_TIMEOUT"
    if "media_incomplete" in t or "mídia incompleta" in t or "media missing" in t: return "RECOVERABLE","MEDIA_INCOMPLETE"
    if "render" in t and "timeout" in t: return "RECOVERABLE","RENDER_TIMEOUT"
    if "render" in t: return "RECOVERABLE","RENDER_FAILURE"
    if "lock" in t and ("active" in t or "andamento" in t): return "RECOVERABLE","LOCK_ACTIVE"
    if code in (124,137,143): return "RECOVERABLE","UNKNOWN_EXCEPTION"
    return "RECOVERABLE","UNKNOWN_EXCEPTION"

def ensure_preflight(total):
    for p in ("main.py","release_artifact_guard.py","resume_short_runtime.py"):
        if not (BASE/p).is_file(): raise RuntimeError(f"RUNTIME_MISSING:{p}")
    free=shutil.disk_usage(BASE).free//(1024*1024)
    if free<MIN_FREE_MB: raise RuntimeError(f"STORAGE_LOW:free_mb={free} required_mb={MIN_FREE_MB}")
    return free

def new_state(total):
    bid=datetime.now().strftime("%Y-%m-%d_%H%M%S")+"_"+str(os.getpid())
    items=[]
    for i in range(1,total+1):
        sid=f"{bid}_{i:02d}"
        items.append({"index":i,"short_id":sid,"status":"QUEUED","attempts":0,"recovery_count":0,"created_at":now(),"updated_at":now(),"last_stage":"","last_error":"","error_class":"","error_code":"","last_exit_code":None,"topic":"","release":"UNKNOWN","output_path":"","log_path":str(BASE/"logs"/"lotes"/f"{bid}_{i:02d}.log")})
    d={"version":"BATCH_STATE_3.0_PER_ITEM","batch_id":bid,"total":total,"status":"RUNNING","created_at":now(),"updated_at":now(),"items":items,"summary":{}}
    summarize(d); atomic(STATE,d); return d

def summarize(d):
    counts={s:0 for s in ITEM_STATES}
    for x in d["items"]: counts[x["status"]]=counts.get(x["status"],0)+1
    d["summary"]={"completed":counts["COMPLETED"],"retry_pending":counts["RETRY_PENDING"],"failed_permanent":counts["FAILED_PERMANENT"],"blocked_global":counts["BLOCKED_GLOBAL"],"queued":counts["QUEUED"],"running":counts["RUNNING"]+counts["RECOVERING"]}
    d["updated_at"]=now()

def save(d): summarize(d); atomic(STATE,d)

def run_item(d,item,recovery=False):
    sid=item["short_id"]; env=clean_env(sid); log=Path(item["log_path"]); log.parent.mkdir(parents=True,exist_ok=True)
    if release_ok(sid,env):
        item.update(status="COMPLETED",release="PUBLISH",last_exit_code=0,last_error="",error_class="",error_code="",updated_at=now()); save(d)
        print(f"BATCH_ITEM_COMPLETE index={item['index']} short_id={sid} release=PUBLISH existing=YES"); return
    has=artifact_exists(sid)
    mode="resume" if has or recovery or item["status"] in {"RETRY_PENDING","RECOVERING"} else "fresh"
    item["status"]="RECOVERING" if mode=="resume" else "RUNNING"; item["attempts"]+=1; item["recovery_count"]+=int(mode=="resume"); item["updated_at"]=now(); save(d)
    print(f"BATCH_ITEM_START index={item['index']} short_id={sid} attempt={item['attempts']}")
    print(f"BATCH_ITEM_MODE={mode.upper()} short_id={sid}")
    cmd=[sys.executable,str(BASE/"main.py"),"resume","--short-id",sid] if mode=="resume" else [sys.executable,str(BASE/"main.py"),"run"]
    started=time.monotonic()
    with log.open("a",encoding="utf-8") as fh:
        fh.write(f"\n[{now()}] mode={mode} attempt={item['attempts']} short_id={sid}\n"); fh.flush()
        p=subprocess.run(cmd,cwd=BASE,env=env,stdout=fh,stderr=subprocess.STDOUT)
    code=p.returncode; item["last_exit_code"]=code
    if code==0 and release_ok(sid,env):
        item.update(status="COMPLETED",release="PUBLISH",last_error="",error_class="",error_code="",output_path=str(BASE/"videos"/f"short_v6_{sid}.mp4"),updated_at=now()); save(d)
        print(f"BATCH_ITEM_COMPLETE index={item['index']} short_id={sid} release=PUBLISH duration={int(time.monotonic()-started)}s"); return
    tail=""
    try: tail=log.read_text(encoding="utf-8",errors="replace")[-12000:]
    except OSError: pass
    cls,err=classify(tail,code); item.update(last_error=tail[-500:].replace("\n"," "),error_class=cls,error_code=err,release="BLOCK",updated_at=now())
    if cls=="GLOBAL_BLOCKER": item["status"]="BLOCKED_GLOBAL"
    elif item["attempts"]>=MAX_ATTEMPTS: item["status"]="FAILED_PERMANENT"
    else: item["status"]="RETRY_PENDING"
    save(d); print(f"BATCH_ITEM_DEFERRED index={item['index']} short_id={sid} class={cls} reason={err} attempt={item['attempts']}")

def write_report(d):
    REPORTS.mkdir(parents=True,exist_ok=True); summarize(d)
    jp=REPORTS/f"{d['batch_id']}.json"; tp=REPORTS/f"{d['batch_id']}.txt"; atomic(jp,d)
    lines=[f"BATCH: {d['batch_id']}",f"TOTAL: {d['total']}",f"STATUS: {d['status']}",f"COMPLETED: {d['summary']['completed']}",f"FAILED: {d['summary']['failed_permanent']}",f"RETRY_PENDING: {d['summary']['retry_pending']}",""]
    for x in d["items"]: lines.append(f"{x['index']:02d} {x['status']} ID={x['short_id']} attempts={x['attempts']} error={x['error_code'] or '-'} release={x['release']}")
    tp.write_text("\n".join(lines)+"\n",encoding="utf-8"); return jp,tp

def execute(d):
    interrupted=False
    def stop(sig,frame):
        nonlocal interrupted; interrupted=True; print(f"BATCH_SIGNAL signal={sig} state=PRESERVED")
    signal.signal(signal.SIGINT,stop); signal.signal(signal.SIGTERM,stop)
    # First pass: never retry an item inline; healthy later items continue.
    for item in d["items"]:
        if interrupted: break
        if item["status"]=="COMPLETED": continue
        if item["status"]=="BLOCKED_GLOBAL": break
        if item["status"] in {"QUEUED","RUNNING","RECOVERING","RETRY_PENDING"}:
            run_item(d,item,recovery=item["status"]!="QUEUED")
            if item["status"]=="BLOCKED_GLOBAL": break
            print(f"BATCH_CONTINUE next={item['index']+1 if item['index']<d['total'] else 'RECOVERY'}")
    # Recovery rounds target only pending items and always use exact-ID resume.
    for attempt_round in range(2,MAX_ATTEMPTS+1):
        pending=[x for x in d["items"] if x["status"]=="RETRY_PENDING"]
        if not pending or interrupted: break
        print(f"BATCH_RECOVERY_ROUND round={attempt_round} pending={len(pending)}")
        for item in pending:
            if interrupted: break
            run_item(d,item,recovery=True)
            if item["status"]=="BLOCKED_GLOBAL": break
    if interrupted: d["status"]="INTERRUPTED"
    elif any(x["status"]=="BLOCKED_GLOBAL" for x in d["items"]): d["status"]="BLOCKED_GLOBAL"
    elif all(x["status"]=="COMPLETED" for x in d["items"]): d["status"]="COMPLETED"
    else: d["status"]="COMPLETED_WITH_ERRORS"
    save(d); jp,tp=write_report(d); print(f"BATCH_RESULT status={d['status']} completed={d['summary']['completed']}/{d['total']} report={tp}")
    return 0 if d["status"]=="COMPLETED" else 1

def status():
    if not STATE.exists(): print("Nenhum lote salvo."); return 0
    try: d=load_state()
    except RuntimeError as e: print(str(e)); return 1
    summarize(d); print(json.dumps(d,ensure_ascii=False,indent=2)); return 0

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("count",nargs="?",type=int); ap.add_argument("--resume",action="store_true"); ap.add_argument("--status",action="store_true"); args=ap.parse_args()
    if args.status:return status()
    QUEUE.mkdir(parents=True,exist_ok=True)
    try:
        with BatchLock():
            ensure_preflight(args.count or 1)
            if args.resume:
                d=load_state()
                if d.get("status")=="COMPLETED": print("Este lote já foi concluído."); return 0
            else:
                total=max(1,min(args.count or int(os.getenv("SHORT_LOTE","3")),10)); d=new_state(total)
            return execute(d)
    except RuntimeError as e:
        print(f"BATCH_BLOCKED {e}"); return 2

if __name__=="__main__": raise SystemExit(main())
