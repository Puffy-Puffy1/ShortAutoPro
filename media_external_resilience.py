#!/usr/bin/env python3
"""Stage 6 external-failure control plane.

Persistent provider circuits + bad-asset quarantine. This module never relaxes
semantic or evidence validation.
"""
from __future__ import annotations
import hashlib
import json
import os
import tempfile
import threading
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

VERSION = "1.0"
BASE = Path(os.path.abspath(os.path.expanduser(os.getenv("SHORTAUTOPRO_BASE", "~/ShortAutoPro"))))
STATE_FILE = BASE / "cache" / "media_resilience" / "state.json"
_LOCK = threading.RLock()
_STATE = None

ALIASES = {
    "pexels_video": "pexels", "pexels_foto": "pexels",
    "pixabay_video": "pixabay", "pixabay_foto": "pixabay",
    "coverr_video": "coverr", "wikimedia_api": "wikimedia",
}
THRESHOLDS = {"AUTH": 1, "RATE_LIMIT": 1, "SERVER": 2, "NETWORK": 2, "TIMEOUT": 2, "MALFORMED": 2, "EMPTY": 4}
COOLDOWNS = {"AUTH": 900.0, "RATE_LIMIT": 60.0, "SERVER": 45.0, "NETWORK": 30.0, "TIMEOUT": 30.0, "MALFORMED": 60.0, "EMPTY": 20.0}
ASSET_TTL = {"HTTP_403": 1800.0, "HTTP_404": 604800.0, "HTTP_410": 604800.0, "HTTP_429": 900.0, "TIMEOUT": 600.0, "NETWORK": 600.0, "CONTENT_TYPE": 86400.0, "TOO_SMALL": 86400.0, "TOO_LARGE": 86400.0, "CORRUPT": 86400.0, "PROBE_FAIL": 86400.0, "REMOVED": 604800.0, "UNKNOWN": 900.0}


def provider_family(provider: Any) -> str:
    raw = str(provider or "unknown").strip().lower()
    return ALIASES.get(raw, raw or "unknown")


def classify_http_status(status: Any) -> str:
    try:
        code = int(status)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if code in {401, 403}: return "AUTH"
    if code == 429: return "RATE_LIMIT"
    if code in {404, 410}: return "REMOVED"
    if 500 <= code <= 599: return "SERVER"
    if 200 <= code <= 399: return "SUCCESS"
    return "HTTP_OTHER"


def classify_exception(exc: Any) -> str:
    text = (type(exc).__name__ + " " + str(exc or "")).lower()
    if "timeout" in text:
        return "TIMEOUT"
    if any(x in text for x in ("jsondecode", "decodeerror", "invalid json", "malformed")):
        return "MALFORMED"
    if any(x in text for x in ("connection", "dns", "name resolution", "network", "socket", "ssl", "tls", "proxy", "chunkedencoding")):
        return "NETWORK"
    return "UNKNOWN"


def _empty():
    return {"version": VERSION, "providers": {}, "bad_assets": {}, "updated_at": 0.0}


def _atomic_write(data):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".state.", suffix=".tmp", dir=str(STATE_FILE.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, STATE_FILE)
        temp_name = ""
    finally:
        if temp_name:
            try: os.unlink(temp_name)
            except OSError: pass


def _load():
    global _STATE
    if _STATE is not None:
        return _STATE
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict): raise ValueError("state-not-dict")
    except Exception:
        data = _empty()
    data.setdefault("providers", {})
    data.setdefault("bad_assets", {})
    _STATE = data
    _cleanup(data)
    return data


def _cleanup(state):
    now = time.time()
    bad = state.setdefault("bad_assets", {})
    for key in list(bad):
        item = bad.get(key)
        if not isinstance(item, dict) or float(item.get("expires_at", 0.0) or 0.0) <= now:
            bad.pop(key, None)
    if len(bad) > 600:
        ordered = sorted(bad, key=lambda key: float((bad.get(key) or {}).get("last_seen", 0.0) or 0.0))
        for key in ordered[:len(bad) - 600]:
            bad.pop(key, None)


def _save(state):
    state["version"] = VERSION
    state["updated_at"] = time.time()
    _cleanup(state)
    try:
        _atomic_write(state)
    except Exception as exc:
        print(f"SAP_MEDIA_RESILIENCE_STATE=WRITE_FAIL {type(exc).__name__}:{str(exc)[:100]}")


def provider_gate(provider: Any):
    family = provider_family(provider)
    with _LOCK:
        state = _load()
        item = state["providers"].get(family, {})
        now = time.time()
        until = float(item.get("open_until", 0.0) or 0.0) if isinstance(item, dict) else 0.0
        if until > now:
            return False, str(item.get("open_reason", "OPEN")), until - now
        if until and isinstance(item, dict):
            item["open_until"] = 0.0
            item["open_reason"] = ""
            item["half_open_at"] = now
            _save(state)
        return True, "CLOSED", 0.0


def note_provider_event(provider: Any, event: str, *, status=None, retry_after=None, detail="", item_count=None):
    family = provider_family(provider)
    event = str(event or "UNKNOWN").upper()
    now = time.time()
    with _LOCK:
        state = _load()
        item = state["providers"].get(family)
        if not isinstance(item, dict):
            item = {}
            state["providers"][family] = item
        item.setdefault("consecutive_failures", 0)
        item.setdefault("empty_streak", 0)
        item.setdefault("open_until", 0.0)
        item.setdefault("open_reason", "")
        item.setdefault("successes", 0)
        item.setdefault("failures", 0)
        item.setdefault("empties", 0)
        item["last_event"] = event
        item["last_status"] = int(status) if str(status or "").isdigit() else None
        item["last_detail"] = str(detail or "")[:160]
        item["last_seen"] = now
        if item_count is not None:
            item["last_item_count"] = max(0, int(item_count))
        if event == "SUCCESS":
            item["successes"] = int(item.get("successes", 0) or 0) + 1
            item["consecutive_failures"] = 0
            item["empty_streak"] = 0
            item["open_until"] = 0.0
            item["open_reason"] = ""
            item["last_success"] = now
        elif event == "EMPTY":
            item["empties"] = int(item.get("empties", 0) or 0) + 1
            item["empty_streak"] = int(item.get("empty_streak", 0) or 0) + 1
            item["consecutive_failures"] = 0
            if item["empty_streak"] >= THRESHOLDS["EMPTY"]:
                item["open_until"] = now + COOLDOWNS["EMPTY"]
                item["open_reason"] = "EMPTY"
        else:
            item["failures"] = int(item.get("failures", 0) or 0) + 1
            item["consecutive_failures"] = int(item.get("consecutive_failures", 0) or 0) + 1
            item["empty_streak"] = 0
            threshold = THRESHOLDS.get(event, 2)
            if item["consecutive_failures"] >= threshold:
                cooldown = COOLDOWNS.get(event, 30.0)
                if event == "RATE_LIMIT":
                    try: cooldown = max(1.0, min(float(retry_after), 900.0))
                    except (TypeError, ValueError): pass
                item["open_until"] = now + cooldown
                item["open_reason"] = event
        _save(state)


def note_response(provider: Any, response: Any):
    status = getattr(response, "status_code", None)
    event = classify_http_status(status)
    retry_after = None
    try: retry_after = response.headers.get("Retry-After")
    except Exception: pass
    if event == "SUCCESS":
        note_provider_event(provider, "SUCCESS", status=status)
    elif event in {"AUTH", "RATE_LIMIT", "SERVER"}:
        note_provider_event(provider, event, status=status, retry_after=retry_after)
    return event


def note_exception(provider: Any, exc: Any):
    event = classify_exception(exc)
    note_provider_event(provider, event, detail=f"{type(exc).__name__}:{str(exc)[:120]}")
    return event


def note_items(provider: Any, items: Any):
    try: count = len(items)
    except Exception: count = 0
    note_provider_event(provider, "SUCCESS" if count else "EMPTY", item_count=count)


def _asset_key(url: Any, provider: Any = "", asset_id: Any = ""):
    family = provider_family(provider)
    stable_id = str(asset_id or "").strip()
    if stable_id:
        raw = f"{family}|id:{stable_id}"
    else:
        raw = f"{family}|url:{str(url or '').strip()}"
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()


def asset_blocked(url: Any, *, provider: Any = "", asset_id: Any = ""):
    key = _asset_key(url, provider, asset_id)
    with _LOCK:
        state = _load()
        item = state["bad_assets"].get(key)
        if not isinstance(item, dict):
            return False, "", 0.0
        remaining = float(item.get("expires_at", 0.0) or 0.0) - time.time()
        if remaining <= 0:
            state["bad_assets"].pop(key, None)
            _save(state)
            return False, "", 0.0
        return True, str(item.get("reason", "BLOCKED")), remaining


def mark_asset_bad(url: Any, *, provider: Any = "", asset_id: Any = "", reason="UNKNOWN", status=None):
    reason = str(reason or "UNKNOWN").upper()
    if status in {403, "403"}: reason = "HTTP_403"
    elif status in {404, "404"}: reason = "HTTP_404"
    elif status in {410, "410"}: reason = "HTTP_410"
    elif status in {429, "429"}: reason = "HTTP_429"
    ttl = ASSET_TTL.get(reason, ASSET_TTL["UNKNOWN"])
    key = _asset_key(url, provider, asset_id)
    try:
        parsed = urlsplit(str(url or ""))
        locator = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"[:220]
    except Exception:
        locator = ""
    with _LOCK:
        state = _load()
        state["bad_assets"][key] = {"provider": provider_family(provider), "asset_id": str(asset_id or "")[:100], "locator": locator, "reason": reason, "status": int(status) if str(status or "").isdigit() else None, "last_seen": time.time(), "expires_at": time.time() + ttl}
        _save(state)
    print(f"SAP_MEDIA_ASSET_QUARANTINE=ADD provider={provider_family(provider)} reason={reason} ttl={ttl:.0f}s")


def filter_quarantined(candidates: Any):
    out = []
    for candidate in list(candidates or []):
        if not isinstance(candidate, dict):
            out.append(candidate); continue
        provider = candidate.get("fonte", "")
        asset_id = candidate.get("id", "")
        url = candidate.get("url") or candidate.get("download_url") or candidate.get("src") or ""
        blocked, reason, remaining = asset_blocked(url, provider=provider, asset_id=asset_id)
        if blocked:
            print(f"SAP_MEDIA_ASSET_QUARANTINE=SKIP provider={provider_family(provider)} id={asset_id or '?'} reason={reason} remaining={remaining:.0f}s")
            continue
        out.append(candidate)
    return out


def infer_download_provider(url: Any):
    try: host = urlsplit(str(url or "")).netloc.lower()
    except Exception: host = ""
    if "pexels" in host: return "download_pexels"
    if "pixabay" in host: return "download_pixabay"
    if "coverr" in host: return "download_coverr"
    if "wikimedia" in host: return "download_wikimedia"
    return "download_external"


def snapshot():
    with _LOCK:
        return json.loads(json.dumps(_load().get("providers", {})))


__all__ = ["VERSION", "provider_family", "classify_http_status", "classify_exception", "provider_gate", "note_provider_event", "note_response", "note_exception", "note_items", "asset_blocked", "mark_asset_bad", "filter_quarantined", "infer_download_provider", "snapshot"]
