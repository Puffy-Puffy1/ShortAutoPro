#!/usr/bin/env python3
"""Stage 6 external-failure control plane.

Persistent, cross-process provider circuits + URL-scoped bad-asset quarantine.
This module never relaxes semantic, evidence, or explicit-MUST validation.
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import time
from contextlib import contextmanager
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

try:
    import fcntl
except Exception:  # pragma: no cover - non-POSIX fallback
    fcntl = None

VERSION = "2.1"
BASE = Path(os.path.abspath(os.path.expanduser(os.getenv("SHORTAUTOPRO_BASE", "~/ShortAutoPro"))))
STATE_FILE = BASE / "cache" / "media_resilience" / "state.json"
_LOCK = threading.RLock()
_STATE = None

ALIASES = {
    "pexels_video": "pexels", "pexels_foto": "pexels",
    "pixabay_video": "pixabay", "pixabay_foto": "pixabay",
    "coverr_video": "coverr", "wikimedia_api": "wikimedia",
}
THRESHOLDS = {
    "AUTH": 1, "RATE_LIMIT": 1, "REMOVED": 1, "SERVER": 2,
    "NETWORK": 2, "TIMEOUT": 2, "MALFORMED": 2, "HTTP_OTHER": 2,
    "EMPTY": 4, "UNKNOWN": 3,
}
COOLDOWNS = {
    "AUTH": 900.0, "RATE_LIMIT": 60.0, "REMOVED": 300.0,
    "SERVER": 45.0, "NETWORK": 30.0, "TIMEOUT": 30.0,
    "MALFORMED": 60.0, "HTTP_OTHER": 60.0, "EMPTY": 20.0,
    "UNKNOWN": 30.0,
}
ASSET_TTL = {
    "HTTP_401": 1800.0, "HTTP_403": 1800.0, "HTTP_404": 604800.0, "HTTP_410": 604800.0,
    "HTTP_429": 900.0, "TIMEOUT": 600.0, "NETWORK": 600.0,
    "CONTENT_TYPE": 86400.0, "TOO_SMALL": 86400.0,
    "TOO_LARGE": 86400.0, "CORRUPT": 86400.0,
    "PROBE_FAIL": 86400.0, "REMOVED": 604800.0, "UNKNOWN": 900.0,
}
HALF_OPEN_LEASE_SECONDS = 15.0
MAX_BAD_ASSETS = 600


def provider_family(provider: Any) -> str:
    raw = str(provider or "unknown").strip().lower()
    return ALIASES.get(raw, raw or "unknown")


def classify_http_status(status: Any) -> str:
    try:
        code = int(status)
    except (TypeError, ValueError):
        return "UNKNOWN"
    if code in {401, 403}:
        return "AUTH"
    if code == 429:
        return "RATE_LIMIT"
    if code in {404, 410}:
        return "REMOVED"
    if 500 <= code <= 599:
        return "SERVER"
    if 200 <= code <= 399:
        return "SUCCESS"
    return "HTTP_OTHER"


def classify_exception(exc: Any) -> str:
    text = (type(exc).__name__ + " " + str(exc or "")).lower()
    if "timeout" in text:
        return "TIMEOUT"
    if any(x in text for x in ("jsondecode", "decodeerror", "invalid json", "malformed")):
        return "MALFORMED"
    if any(x in text for x in (
        "connection", "dns", "name resolution", "network", "socket",
        "ssl", "tls", "proxy", "chunkedencoding",
    )):
        return "NETWORK"
    return "UNKNOWN"


def _empty() -> dict[str, Any]:
    return {
        "version": VERSION,
        "providers": {},
        "bad_assets": {},
        "updated_at": 0.0,
        "corrupt_recoveries": 0,
    }


def _lock_path() -> Path:
    return STATE_FILE.parent / (STATE_FILE.name + ".lock")


@contextmanager
def _process_lock():
    """Serialize state transactions across cron/manual ShortAutoPro processes."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    handle = open(_lock_path(), "a+", encoding="utf-8")
    try:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        if fcntl is not None:
            try:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        handle.close()


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _provider_defaults(item: Any) -> dict[str, Any]:
    if not isinstance(item, dict):
        item = {}

    for key in (
        "consecutive_failures",
        "empty_streak",
        "successes",
        "failures",
        "empties",
        "resource_misses",
    ):
        item[key] = max(0, _safe_int(item.get(key, 0), 0))

    for key in ("open_until", "probe_lease_until"):
        item[key] = max(0.0, _safe_float(item.get(key, 0.0), 0.0))

    for key in ("open_reason", "probe_owner"):
        item[key] = str(item.get(key, "") or "")

    return item


def _cleanup(state: dict[str, Any]) -> None:
    now = time.time()
    bad = state.setdefault("bad_assets", {})
    if not isinstance(bad, dict):
        state["bad_assets"] = {}
        bad = state["bad_assets"]

    for key in list(bad):
        item = bad.get(key)
        if not isinstance(item, dict):
            bad.pop(key, None)
            continue
        if _safe_float(item.get("expires_at", 0.0), 0.0) <= now:
            bad.pop(key, None)

    if len(bad) > MAX_BAD_ASSETS:
        ordered = sorted(
            bad,
            key=lambda key: float((bad.get(key) or {}).get("last_seen", 0.0) or 0.0),
        )
        for key in ordered[:len(bad) - MAX_BAD_ASSETS]:
            bad.pop(key, None)

    providers = state.setdefault("providers", {})
    if not isinstance(providers, dict):
        state["providers"] = {}
        providers = state["providers"]
    for name in list(providers):
        providers[name] = _provider_defaults(providers.get(name))


def _backup_corrupt_locked(exc: Exception) -> str:
    if not STATE_FILE.exists():
        return ""
    stamp = int(time.time())
    backup = STATE_FILE.parent / f"state.corrupt.{stamp}.{os.getpid()}.json"
    try:
        os.replace(STATE_FILE, backup)
    except OSError:
        return ""
    try:
        backups = sorted(
            STATE_FILE.parent.glob("state.corrupt.*.json"),
            key=lambda p: p.stat().st_mtime_ns,
            reverse=True,
        )
        for old in backups[3:]:
            try:
                old.unlink()
            except OSError:
                pass
    except OSError:
        pass
    print(
        "SAP_MEDIA_RESILIENCE_STATE=CORRUPT_RECOVERED "
        f"backup={backup.name} error={type(exc).__name__}:{str(exc)[:100]}"
    )
    return backup.name


def _load_locked() -> dict[str, Any]:
    """Always re-read disk so independent Termux processes share one truth."""
    global _STATE
    if not STATE_FILE.exists():
        data = _empty()
    else:
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("state-not-dict")
        except Exception as exc:
            backup = _backup_corrupt_locked(exc)
            data = _empty()
            data["corrupt_recoveries"] = 1
            if backup:
                data["last_corrupt_backup"] = backup

    data.setdefault("providers", {})
    data.setdefault("bad_assets", {})
    data.setdefault("corrupt_recoveries", 0)
    _cleanup(data)
    _STATE = data
    return data


def _atomic_write(data: dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=".state.", suffix=".tmp", dir=str(STATE_FILE.parent)
    )
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
            try:
                os.unlink(temp_name)
            except OSError:
                pass


def _save_locked(state: dict[str, Any]) -> None:
    state["version"] = VERSION
    state["updated_at"] = time.time()
    _cleanup(state)
    try:
        _atomic_write(state)
    except Exception as exc:
        print(
            "SAP_MEDIA_RESILIENCE_STATE=WRITE_FAIL "
            f"{type(exc).__name__}:{str(exc)[:100]}"
        )


def _retry_after_seconds(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return max(1.0, min(float(value), 900.0))
    except (TypeError, ValueError):
        pass
    try:
        dt = parsedate_to_datetime(str(value))
        seconds = dt.timestamp() - time.time()
        return max(1.0, min(seconds, 900.0))
    except Exception:
        return None


def provider_gate(provider: Any):
    family = provider_family(provider)
    with _LOCK:
        with _process_lock():
            state = _load_locked()
            item = _provider_defaults(state["providers"].get(family))
            state["providers"][family] = item
            now = time.time()
            until = _safe_float(item.get("open_until", 0.0), 0.0)
            lease_until = _safe_float(item.get("probe_lease_until", 0.0), 0.0)

            if until > now:
                return False, str(item.get("open_reason", "OPEN") or "OPEN"), until - now

            if lease_until > now:
                return False, "HALF_OPEN_BUSY", lease_until - now

            if until and until <= now:
                previous = str(item.get("open_reason", "") or "OPEN")
                item["open_until"] = 0.0
                item["previous_open_reason"] = previous
                item["open_reason"] = ""
                item["half_open_at"] = now
                item["probe_lease_until"] = now + HALF_OPEN_LEASE_SECONDS
                item["probe_owner"] = f"{os.getpid()}:{threading.get_ident()}"
                _save_locked(state)
                return True, "HALF_OPEN", 0.0

            if lease_until:
                item["probe_lease_until"] = 0.0
                item["probe_owner"] = ""
                _save_locked(state)

            return True, "CLOSED", 0.0


def note_provider_event(
    provider: Any,
    event: str,
    *,
    status=None,
    retry_after=None,
    detail="",
    item_count=None,
):
    family = provider_family(provider)
    event = str(event or "UNKNOWN").upper()
    now = time.time()

    with _LOCK:
        with _process_lock():
            state = _load_locked()
            item = _provider_defaults(state["providers"].get(family))
            state["providers"][family] = item

            # Any reported result completes the half-open probe.
            item["probe_lease_until"] = 0.0
            item["probe_owner"] = ""
            item["last_event"] = event
            item["last_status"] = int(status) if str(status or "").isdigit() else None
            item["last_detail"] = str(detail or "")[:160]
            item["last_seen"] = now
            if item_count is not None:
                try:
                    item["last_item_count"] = max(0, int(item_count))
                except (TypeError, ValueError):
                    item["last_item_count"] = 0

            if event == "SUCCESS":
                item["successes"] = int(item.get("successes", 0) or 0) + 1
                item["consecutive_failures"] = 0
                item["empty_streak"] = 0
                item["open_until"] = 0.0
                item["open_reason"] = ""
                item["last_success"] = now

            elif event == "HTTP_SUCCESS":
                item["consecutive_failures"] = 0
                if item.get("open_reason") != "EMPTY":
                    item["open_until"] = 0.0
                    item["open_reason"] = ""

            elif event == "EMPTY":
                item["empties"] = int(item.get("empties", 0) or 0) + 1
                item["empty_streak"] = int(item.get("empty_streak", 0) or 0) + 1
                item["consecutive_failures"] = 0
                if item["empty_streak"] >= THRESHOLDS["EMPTY"]:
                    item["open_until"] = now + COOLDOWNS["EMPTY"]
                    item["open_reason"] = "EMPTY"

            elif event == "RESOURCE_MISS":
                # A 401/403/404/410 from a media CDN is URL/asset scoped.
                # It must not poison the search-provider circuit.
                item["resource_misses"] = int(item.get("resource_misses", 0) or 0) + 1
                item["consecutive_failures"] = 0
                item["empty_streak"] = 0

            else:
                item["failures"] = int(item.get("failures", 0) or 0) + 1
                item["consecutive_failures"] = int(
                    item.get("consecutive_failures", 0) or 0
                ) + 1
                item["empty_streak"] = 0
                threshold = THRESHOLDS.get(event, THRESHOLDS["UNKNOWN"])
                if item["consecutive_failures"] >= threshold:
                    cooldown = COOLDOWNS.get(event, COOLDOWNS["UNKNOWN"])
                    if event == "RATE_LIMIT":
                        parsed = _retry_after_seconds(retry_after)
                        if parsed is not None:
                            cooldown = parsed
                    item["open_until"] = now + cooldown
                    item["open_reason"] = event

            _save_locked(state)


def note_response(provider: Any, response: Any):
    status = getattr(response, "status_code", None)
    event = classify_http_status(status)
    family = provider_family(provider)
    retry_after = None
    try:
        retry_after = response.headers.get("Retry-After")
    except Exception:
        pass

    if event == "SUCCESS":
        note_provider_event(provider, "HTTP_SUCCESS", status=status)
    elif family.startswith("download_") and status in {401, 403, 404, 410}:
        note_provider_event(
            provider,
            "RESOURCE_MISS",
            status=status,
            detail=f"download_http_{status}",
        )
    else:
        note_provider_event(
            provider,
            event,
            status=status,
            retry_after=retry_after,
        )
    return event


def note_exception(provider: Any, exc: Any):
    event = classify_exception(exc)
    note_provider_event(
        provider,
        event,
        detail=f"{type(exc).__name__}:{str(exc)[:120]}",
    )
    return event


def note_items(provider: Any, items: Any):
    try:
        count = len(items)
    except Exception:
        count = 0
    note_provider_event(provider, "SUCCESS" if count else "EMPTY", item_count=count)


def _asset_key(
    url: Any,
    provider: Any = "",
    asset_id: Any = "",
    *,
    asset_wide: bool = False,
):
    family = provider_family(provider)
    stable_id = str(asset_id or "").strip()
    if asset_wide and stable_id:
        raw = f"{family}|id:{stable_id}"
    else:
        raw = f"{family}|url:{str(url or '').strip()}"
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()


def _candidate_urls(candidate: dict[str, Any]) -> list[str]:
    values: list[Any] = [
        candidate.get("url"),
        candidate.get("download_url"),
        candidate.get("src"),
    ]
    variants = candidate.get("_download_variants", [])
    if isinstance(variants, (list, tuple)):
        values.extend(variants)

    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        if isinstance(value, dict):
            value = value.get("url") or value.get("link")
        text = str(value or "").strip()
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    return out


def asset_blocked(
    url: Any,
    *,
    provider: Any = "",
    asset_id: Any = "",
):
    keys = [
        _asset_key(url, provider, asset_id, asset_wide=False),
    ]
    if str(asset_id or "").strip():
        keys.append(_asset_key(url, provider, asset_id, asset_wide=True))

    with _LOCK:
        with _process_lock():
            state = _load_locked()
            now = time.time()
            for key in keys:
                item = state["bad_assets"].get(key)
                if not isinstance(item, dict):
                    continue
                remaining = _safe_float(item.get("expires_at", 0.0), 0.0) - now
                if remaining > 0:
                    return True, str(item.get("reason", "BLOCKED")), remaining
                state["bad_assets"].pop(key, None)
            return False, "", 0.0


def mark_asset_bad(
    url: Any,
    *,
    provider: Any = "",
    asset_id: Any = "",
    reason="UNKNOWN",
    status=None,
    asset_wide: bool = False,
):
    reason = str(reason or "UNKNOWN").upper()
    if status in {401, "401"}:
        reason = "HTTP_401"
    elif status in {403, "403"}:
        reason = "HTTP_403"
    elif status in {404, "404"}:
        reason = "HTTP_404"
    elif status in {410, "410"}:
        reason = "HTTP_410"
    elif status in {429, "429"}:
        reason = "HTTP_429"

    ttl = ASSET_TTL.get(reason, ASSET_TTL["UNKNOWN"])
    key = _asset_key(url, provider, asset_id, asset_wide=asset_wide)
    try:
        parsed = urlsplit(str(url or ""))
        locator = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"[:220]
    except Exception:
        locator = ""

    now = time.time()
    with _LOCK:
        with _process_lock():
            state = _load_locked()
            state["bad_assets"][key] = {
                "provider": provider_family(provider),
                "asset_id": str(asset_id or "")[:100],
                "scope": "asset" if asset_wide else "url",
                "locator": locator,
                "reason": reason,
                "status": int(status) if str(status or "").isdigit() else None,
                "last_seen": now,
                "expires_at": now + ttl,
            }
            _save_locked(state)

    print(
        "SAP_MEDIA_ASSET_QUARANTINE=ADD "
        f"provider={provider_family(provider)} reason={reason} "
        f"scope={'asset' if asset_wide else 'url'} ttl={ttl:.0f}s"
    )


def filter_quarantined(candidates: Any):
    out = []
    for candidate in list(candidates or []):
        if not isinstance(candidate, dict):
            out.append(candidate)
            continue

        provider = candidate.get("fonte", "")
        asset_id = candidate.get("id", "")
        urls = _candidate_urls(candidate)
        if not urls:
            out.append(candidate)
            continue

        available: list[str] = []
        blocked_meta: list[tuple[str, float]] = []
        for url in urls:
            blocked, reason, remaining = asset_blocked(
                url, provider=provider, asset_id=asset_id
            )
            if blocked:
                blocked_meta.append((reason, remaining))
            else:
                available.append(url)

        if not available:
            reason, remaining = blocked_meta[0] if blocked_meta else ("BLOCKED", 0.0)
            print(
                "SAP_MEDIA_ASSET_QUARANTINE=SKIP "
                f"provider={provider_family(provider)} id={asset_id or '?'} "
                f"reason={reason} remaining={remaining:.0f}s"
            )
            continue

        primary = str(candidate.get("url") or "").strip()
        selected = primary if primary in available else available[0]
        cleaned_variants = [url for url in available if url != selected]

        if (
            selected != primary
            or list(candidate.get("_download_variants", []) or []) != cleaned_variants
        ):
            candidate = dict(candidate)
            candidate["url"] = selected
            candidate["_download_variants"] = cleaned_variants

        if primary and selected != primary:
            print(
                "SAP_MEDIA_ASSET_QUARANTINE=PRIMARY_ROTATED "
                f"provider={provider_family(provider)} id={asset_id or '?'}"
            )

        out.append(candidate)
    return out


def infer_download_provider(url: Any):
    try:
        host = urlsplit(str(url or "")).netloc.lower()
    except Exception:
        host = ""
    if "pexels" in host:
        return "download_pexels"
    if "pixabay" in host:
        return "download_pixabay"
    if "coverr" in host:
        return "download_coverr"
    if "wikimedia" in host:
        return "download_wikimedia"
    return "download_external"


def snapshot():
    with _LOCK:
        with _process_lock():
            state = _load_locked()
            return json.loads(json.dumps(state.get("providers", {})))


def diagnostics():
    with _LOCK:
        with _process_lock():
            state = _load_locked()
            return {
                "version": VERSION,
                "providers": json.loads(json.dumps(state.get("providers", {}))),
                "bad_assets_active": len(state.get("bad_assets", {})),
                "corrupt_recoveries": int(state.get("corrupt_recoveries", 0) or 0),
                "last_corrupt_backup": state.get("last_corrupt_backup", ""),
                "updated_at": _safe_float(state.get("updated_at", 0.0), 0.0),
            }


__all__ = [
    "VERSION", "provider_family", "classify_http_status", "classify_exception",
    "provider_gate", "note_provider_event", "note_response", "note_exception",
    "note_items", "asset_blocked", "mark_asset_bad", "filter_quarantined",
    "infer_download_provider", "snapshot", "diagnostics",
]
