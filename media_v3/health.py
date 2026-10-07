from __future__ import annotations
import json, os, tempfile, time
from pathlib import Path
from threading import Lock
BASE=Path(os.getenv("SHORTAUTOPRO_BASE",Path.home()/"ShortAutoPro")).resolve()
PATH=BASE/".sap_state"/"provider_health_v3.json"
_LOCK=Lock()

def _load():
    try:
        data=json.loads(PATH.read_text(encoding="utf-8"))
        return data if isinstance(data,dict) else {"providers":{}}
    except Exception:
        return {"schema_version":"provider-health-v3","providers":{}}

def _save(data):
    PATH.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(prefix=".provider-health-",suffix=".tmp",dir=str(PATH.parent))
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(data,f,ensure_ascii=False,indent=2,sort_keys=True); f.write("\n"); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,PATH)
    finally:
        try: os.unlink(tmp)
        except OSError: pass

def record(provider,event,**meta):
    now=time.time()
    with _LOCK:
        data=_load(); data.setdefault("schema_version","provider-health-v3")
        item=data.setdefault("providers",{}).setdefault(provider,{})
        item["last_event"]=str(event).upper(); item["last_seen"]=now
        item["last_status"]=meta.get("status")
        item["last_latency_ms"]=meta.get("latency_ms")
        item["last_error"]=str(meta.get("error") or "")
        item["last_query"]=str(meta.get("query") or "")
        if str(event).upper()=="SUCCESS":
            item["successes"]=int(item.get("successes",0))+1
            item["last_success"]=now
        else:
            item["failures"]=int(item.get("failures",0))+1
            item["last_failure"]=now
        _save(data)

def snapshot():
    with _LOCK:
        return _load()
