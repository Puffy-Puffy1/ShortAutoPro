from __future__ import annotations
import hashlib, json, os, shutil, tempfile, time
from pathlib import Path
from typing import Any
import requests
from .diagnostics import SceneDiagnostics
from .query import build_query_plan
from .providers import ProviderRegistry, ProviderAdapter
from media_validator_v2 import validate as validate_media
from .health import record as record_provider_health

FORBIDDEN=("slate","placeholder","neutral_editorial","editorial_reuse")

class CircuitState:
    def __init__(self, threshold=2, cooldown=30): self.failures=0; self.open_until=0.0; self.threshold=threshold; self.cooldown=cooldown
    def allow(self): return time.monotonic() >= self.open_until
    def fail(self):
        self.failures += 1
        if self.failures >= self.threshold: self.open_until=time.monotonic()+self.cooldown
    def success(self): self.failures=0; self.open_until=0.0

class MediaAcquisitionV3:
    def __init__(self, base: Path, registry: ProviderRegistry | None = None):
        self.base=Path(base).resolve(); self.registry=registry or ProviderRegistry(); self._circuits_by_sid={}
    def _score(self, candidate, query, hard, soft, avoid):
        text=" ".join(str(candidate.get(k) or "") for k in ("description","title","tags","url")).casefold()
        tokens=set(__import__("re").findall(r"[a-z0-9À-ÿ]+",text)); q=set(__import__("re").findall(r"[a-z0-9À-ÿ]+",query.casefold()))
        hard_hits=sum(1 for x in hard if set(__import__("re").findall(r"[a-z0-9À-ÿ]+",x.casefold())) <= tokens)
        soft_hits=sum(1 for x in soft if set(__import__("re").findall(r"[a-z0-9À-ÿ]+",x.casefold())) <= tokens)
        # Avoid rules are phrase-aware: a multi-word rule matches only when all\n        # of its meaningful tokens are present. This prevents rules such as\n        # "container ship" from rejecting every valid "ship" candidate.\n        avoid_hits=sum(1 for x in avoid if set(__import__("re").findall(r"[a-z0-9À-ÿ]+",x.casefold())) <= tokens)\n        overlap=len(q&tokens)/max(1,len(q)); score=overlap*50+soft_hits*12+hard_hits*30-avoid_hits*70
        return score,hard_hits,soft_hits,avoid_hits
    def _download(self, candidate, sid, scene_no, diag):
        provider=str(candidate.get("provider") or "unknown"); url=str(candidate.get("url") or "")
        outdir=self.base/"imagens"/f"short_{sid}"; outdir.mkdir(parents=True,exist_ok=True)
        if candidate.get("local_path"):
            src=Path(str(candidate["local_path"])).expanduser().resolve()
            if not src.is_file():
                diag.reject("DOWNLOAD_FAILED",provider=provider,asset_id=candidate.get("id"),detail="local_missing")
                return None
            dest=outdir/f"scene_{scene_no:02d}_{provider}{src.suffix.lower()}"
            tmp=dest.with_suffix(dest.suffix+".part")
            try:
                shutil.copy2(src,tmp)
                os.replace(tmp,dest)
            except OSError as exc:
                tmp.unlink(missing_ok=True)
                diag.reject("DOWNLOAD_FAILED",provider=provider,asset_id=candidate.get("id"),detail=type(exc).__name__)
                return None
        else:
            if not url.startswith(("http://","https://")): diag.reject("INVALID_URL",provider=provider,asset_id=candidate.get("id")); return None
            ext=".mp4" if str(candidate.get("kind"))=="video" else ".jpg"; dest=outdir/f"scene_{scene_no:02d}_{provider}{ext}"
            tmp=dest.with_suffix(dest.suffix+".part")
            last_reason="DOWNLOAD_FAILED"
            for attempt in range(2):
                try:
                    with requests.get(url,stream=True,timeout=(5,15)) as r:
                        if r.status_code == 429:
                            last_reason="RATE_LIMIT"
                        elif r.status_code >= 500:
                            last_reason="HTTP_ERROR"
                        elif not r.ok:
                            last_reason="HTTP_ERROR"
                        else:
                            with tmp.open("wb") as fh:
                                for chunk in r.iter_content(1024*1024):
                                    if chunk:
                                        fh.write(chunk)
                            os.replace(tmp,dest)
                            last_reason=""
                            break
                    tmp.unlink(missing_ok=True)
                except requests.Timeout:
                    last_reason="TIMEOUT"
                    tmp.unlink(missing_ok=True)
                except requests.RequestException as exc:
                    last_reason="DOWNLOAD_FAILED"
                    tmp.unlink(missing_ok=True)
                    if attempt == 1:
                        diag.reject(last_reason,provider=provider,asset_id=candidate.get("id"),detail=type(exc).__name__)
                        return None
                if attempt == 0:
                    time.sleep(0.25)
            if last_reason:
                diag.reject(last_reason,provider=provider,asset_id=candidate.get("id"))
                return None
        diag.candidates_downloaded += 1
        try:
            result=validate_media(dest); diag.candidates_valid += 1
        except Exception as exc:
            diag.reject(self._map_validation_error(str(exc)),provider=provider,asset_id=candidate.get("id"),detail=str(exc)); dest.unlink(missing_ok=True); return None
        return result | {"path":str(dest),"provider":provider,"asset_id":str(candidate.get("id") or ""),"description":str(candidate.get("description") or ""),"kind":str(candidate.get("kind") or "image"),"provenance":candidate}
    @staticmethod
    def _map_validation_error(message):
        m=message.upper()
        if "TOO_SMALL" in m: return "FILE_TOO_SMALL"
        if "NO_VIDEO" in m: return "NO_VIDEO_STREAM"
        if "NO_IMAGE" in m: return "NO_IMAGE_STREAM"
        if "NO_STREAM" in m or "PROBE_FAIL" in m or "PROBE_INVALID" in m: return "CORRUPTED_FILE"
        if "DURATION" in m: return "DURATION_INVALID"
        if "EXTENSION" in m or "UNSUPPORTED" in m: return "UNSUPPORTED_FORMAT"
        if "DIMENSION" in m: return "RESOLUTION_INVALID"
        if "SIGNATURE" in m: return "CORRUPTED_FILE"
        return "VALIDATION_FAILED"
    def acquire_scene(self,sid,number,scene):
        sid=str(sid).strip(); scene_id=str(scene.get("scene_id",scene.get("scene",number)))
        query=str(scene.get("query") or scene.get("busca") or scene.get("segment") or "").strip()
        hard=[str(x).strip() for x in (scene.get("hard_must") or scene.get("must_have") or []) if str(x).strip()]
        soft=[str(x).strip() for x in (scene.get("soft_must") or []) if str(x).strip()]
        avoid=[str(x).strip() for x in (scene.get("avoid") or []) if str(x).strip()]
        diag=SceneDiagnostics(scene_id,query,must=hard,soft_must=soft,avoid=avoid)
        if not query: diag.final_status="FAILED"; diag.error="MEDIA_INPUT_INVALID:query_empty"; return None,diag
        plan=build_query_plan(query,hard,soft); diag.query_variants=list(plan.variants)
        pool=[]; seen=set()
        for provider,status in self.registry.enabled():
            diag.providers_attempted.append(provider.name)
            diag.provider_results[provider.name]={"status":status.reason,"queries":[]}
            if not status.enabled:
                diag.provider_results[provider.name]["skipped"]=True
                if status.reason == "NO_API_KEY":
                    diag.fallbacks.append({"type":"provider","provider":provider.name,"reason":"NO_API_KEY"})
                else:
                    diag.fallbacks.append({"type":"provider","provider":provider.name,"reason":status.reason})
                continue
            circuits=self._circuits_by_sid.setdefault(sid,{p.name:CircuitState() for p in self.registry.providers})
            circuit=circuits[provider.name]
            if not circuit.allow():
                diag.provider_results[provider.name]["circuit"]="OPEN"
                diag.fallbacks.append({"type":"provider","provider":provider.name,"reason":"CIRCUIT_OPEN"})
                continue

            accepted_from_provider=0
            provider_seen=set()
            for qindex,q in enumerate(plan.variants):
                rows=None
                for attempt in range(2):
                    detail=""
                    try:
                        rows=provider.search(q, hard, soft, avoid)
                        diag.provider_results[provider.name]["queries"].append({"query":q,"count":len(rows),"attempt":attempt+1})
                        record_provider_health(provider.name,"SUCCESS",query=q,latency_ms=0,status=200)
                        break
                    except requests.Timeout:
                        reason="TIMEOUT"
                    except requests.HTTPError as exc:
                        reason="HTTP_ERROR"
                        detail=getattr(getattr(exc,"response",None),"status_code",None)
                    except requests.RequestException as exc:
                        reason="PROVIDER_UNAVAILABLE"
                        detail=type(exc).__name__
                    except Exception as exc:
                        raw=str(exc).upper()
                        if "RATE_LIMIT" in raw or "429" in raw:
                            reason="RATE_LIMIT"
                        elif "TIMEOUT" in raw:
                            reason="TIMEOUT"
                        elif "HTTP_ERROR" in raw or "HTTP 5" in raw:
                            reason="HTTP_ERROR"
                        else:
                            reason="PROVIDER_UNAVAILABLE"
                        detail=str(exc)
                    diag.provider_results[provider.name]["queries"].append({"query":q,"error":reason,"attempt":attempt+1,**({"detail":detail} if "detail" in locals() else {})})
                    record_provider_health(provider.name,reason,query=q,error=detail)
                    diag.fallbacks.append({"type":"query","provider":provider.name,"query":q,"reason":reason})
                    circuit.fail()
                    if attempt == 0 and reason in {"RATE_LIMIT","TIMEOUT","HTTP_ERROR","PROVIDER_UNAVAILABLE"}:
                        time.sleep(0.25)
                        continue
                    rows=[]
                    break
                if rows is None:
                    rows=[]

                if not rows:
                    diag.fallbacks.append({"type":"query","provider":provider.name,"query":q,"reason":"ZERO_RESULTS"})
                    continue

                query_accepted=0
                for row in rows:
                    if not isinstance(row,dict):
                        diag.reject("VALIDATION_FAILED",provider=provider.name,detail="candidate_not_object")
                        continue
                    score,hh,sh,ah=self._score(row,q,hard,soft,avoid)
                    row.update({"provider":provider.name,"score":score,"hard_hits":hh,"soft_hits":sh,"avoid_hits":ah})
                    diag.candidates_found += 1
                    key=(provider.name,str(row.get("id") or row.get("url") or ""))
                    if key in seen or key in provider_seen:
                        diag.reject("DUPLICATE",provider=provider.name,asset_id=row.get("id"))
                        continue
                    provider_seen.add(key)
                    if ah:
                        diag.reject("AVOID_MATCH",provider=provider.name,asset_id=row.get("id"))
                        continue
                    if hard and hh < len(hard):
                        diag.reject("MUST_NOT_MATCH",provider=provider.name,asset_id=row.get("id"),hits=hh,total=len(hard))
                        continue
                    if score < 35:
                        diag.reject("LOW_RELEVANCE",provider=provider.name,asset_id=row.get("id"),score=round(score,2))
                        continue
                    seen.add(key)
                    pool.append(row)
                    query_accepted += 1
                    accepted_from_provider += 1

                # A query that yielded usable candidates is sufficient for this
                # provider. If every candidate was rejected, keep searching with
                # the next progressive query variant instead of stopping early.
                if query_accepted:
                    break

            if accepted_from_provider:
                circuit.success()
            elif diag.provider_results[provider.name]["queries"]:
                circuit.fail()
        pool.sort(key=lambda x:(float(x.get("score",0)),int(x.get("hard_hits",0)),int(x.get("soft_hits",0)),str(x.get("provider","")),str(x.get("id",""))),reverse=True)
        for candidate in pool:
            result=self._download(candidate,sid,number,diag)
            if result:
                result["verification_mode"]="hard_must" if hard else "relevance"
                diag.selected_provider=result["provider"]; diag.selected_asset_id=result["asset_id"]; diag.final_status="RESOLVED"
                return result,diag
        diag.final_status="FAILED"; diag.error="MEDIA_ACQUISITION_V3_EXHAUSTED"; return None,diag
