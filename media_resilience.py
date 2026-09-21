#!/usr/bin/env python3
"""Persistent resilience layer for external media providers.

This module does not weaken semantic/evidence gates. It isolates availability
risk from Wikimedia/stock providers and keeps a bounded local cache of metadata
and already-validated media so temporary external failures do not dominate a
Short production.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import fcntl
except Exception:  # pragma: no cover - non-POSIX fallback
    fcntl = None

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", os.path.expanduser("~/ShortAutoPro"))).resolve()
STATE_DIR = BASE / ".sap_state" / "media_resilience"
CACHE_DIR = BASE / ".sap_cache" / "media"
QUERY_STATE = STATE_DIR / "query_cache.json"
PROVIDER_STATE = STATE_DIR / "provider_health.json"
QUARANTINE_STATE = STATE_DIR / "url_quarantine.json"
BLOB_INDEX = STATE_DIR / "blob_index.json"
LOCK_FILE = STATE_DIR / ".lock"

DEFAULT_POSITIVE_TTL = 7 * 86400
DEFAULT_EMPTY_TTL = 20 * 60
DEFAULT_STALE_MAX = 30 * 86400


def _now() -> float:
    return time.time()


def _load(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        tmp = ""
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass


class _Lock:
    def __enter__(self):
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        self.handle = LOCK_FILE.open("a+")
        if fcntl is not None:
            fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, exc_type, exc, tb):
        if fcntl is not None:
            try:
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass
        self.handle.close()


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def provider_from_url(url: str) -> str:
    host = (urlparse(str(url or "")).hostname or "").casefold()
    if "wikimedia" in host or "wikipedia" in host:
        return "wikimedia"
    if "pexels" in host:
        return "pexels"
    if "pixabay" in host:
        return "pixabay"
    if "coverr" in host:
        return "coverr"
    return host or "unknown"


def _provider_record(provider: str) -> dict[str, Any]:
    data = _load(PROVIDER_STATE, {"version": "1.0", "providers": {}})
    providers = data.get("providers", {}) if isinstance(data, dict) else {}
    record = providers.get(provider, {}) if isinstance(providers, dict) else {}
    return record if isinstance(record, dict) else {}


def provider_allowed(provider: str) -> tuple[bool, str]:
    name = str(provider or "unknown").strip().casefold()
    record = _provider_record(name)
    until = float(record.get("circuit_until", 0.0) or 0.0)
    if until > _now():
        return False, str(record.get("last_reason", "circuit_open") or "circuit_open")
    return True, "OK"


def record_provider_result(
    provider: str,
    *,
    ok: bool,
    status_code: int | None = None,
    reason: str = "",
    retry_after: float | None = None,
) -> dict[str, Any]:
    name = str(provider or "unknown").strip().casefold()
    now = _now()

    with _Lock():
        data = _load(PROVIDER_STATE, {"version": "1.0", "providers": {}})
        if not isinstance(data, dict):
            data = {"version": "1.0", "providers": {}}
        providers = data.get("providers")
        if not isinstance(providers, dict):
            providers = {}
        rec = providers.get(name, {})
        if not isinstance(rec, dict):
            rec = {}

        failures = int(rec.get("consecutive_failures", 0) or 0)
        circuit_until = float(rec.get("circuit_until", 0.0) or 0.0)

        if ok:
            rec.update({
                "consecutive_failures": 0,
                "circuit_until": 0.0,
                "last_success": now,
                "last_status": int(status_code or 200),
                "last_reason": "success",
            })
        else:
            failures += 1
            cooldown = 0.0
            code = int(status_code or 0)

            if code in {401, 403}:
                cooldown = float(os.getenv("SAP_MEDIA_AUTH_COOLDOWN_SECONDS", "21600") or 21600)
            elif code == 429:
                if retry_after is not None:
                    cooldown = max(60.0, min(float(retry_after), 3600.0))
                else:
                    cooldown = float(os.getenv("SAP_MEDIA_RATE_LIMIT_COOLDOWN_SECONDS", "900") or 900)
            elif code in {500, 502, 503, 504} or reason in {"timeout", "network"}:
                if failures >= 2:
                    cooldown = min(3600.0, 300.0 * (2 ** min(failures - 2, 3)))
            elif reason == "persistent_empty" and failures >= 3:
                cooldown = 600.0

            if cooldown > 0:
                circuit_until = max(circuit_until, now + cooldown)

            rec.update({
                "consecutive_failures": failures,
                "circuit_until": circuit_until,
                "last_failure": now,
                "last_status": code,
                "last_reason": str(reason or f"http_{code}" or "failure"),
            })

        providers[name] = rec
        data["providers"] = providers
        data["updated_at"] = now
        _atomic(PROVIDER_STATE, data)
        return dict(rec)


def query_cache_key(provider: str, payload: Any) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _hash_text(f"{provider.casefold()}|{canonical}")


def cache_query_result(
    provider: str,
    payload: Any,
    candidates: list[Any],
    *,
    positive_ttl: int = DEFAULT_POSITIVE_TTL,
    empty_ttl: int = DEFAULT_EMPTY_TTL,
) -> None:
    key = query_cache_key(provider, payload)
    now = _now()
    items = list(candidates or [])
    ttl = positive_ttl if items else empty_ttl

    with _Lock():
        data = _load(QUERY_STATE, {"version": "1.0", "entries": {}})
        if not isinstance(data, dict):
            data = {"version": "1.0", "entries": {}}
        entries = data.get("entries")
        if not isinstance(entries, dict):
            entries = {}
        entries[key] = {
            "provider": str(provider),
            "created_at": now,
            "expires_at": now + max(60, int(ttl)),
            "candidates": items,
        }
        # Keep the persistent metadata cache bounded.
        if len(entries) > 3000:
            ordered = sorted(
                entries.items(),
                key=lambda kv: float((kv[1] or {}).get("created_at", 0) or 0),
                reverse=True,
            )[:2500]
            entries = dict(ordered)
        data["entries"] = entries
        data["updated_at"] = now
        _atomic(QUERY_STATE, data)


def get_cached_query(
    provider: str,
    payload: Any,
    *,
    allow_stale: bool = False,
    stale_max_seconds: int = DEFAULT_STALE_MAX,
) -> tuple[list[Any] | None, str]:
    key = query_cache_key(provider, payload)
    data = _load(QUERY_STATE, {"entries": {}})
    entries = data.get("entries", {}) if isinstance(data, dict) else {}
    entry = entries.get(key) if isinstance(entries, dict) else None
    if not isinstance(entry, dict):
        return None, "MISS"

    now = _now()
    expires = float(entry.get("expires_at", 0.0) or 0.0)
    created = float(entry.get("created_at", 0.0) or 0.0)
    candidates = entry.get("candidates")
    if not isinstance(candidates, list):
        return None, "MISS"

    if expires >= now:
        return candidates, "FRESH"

    if allow_stale and created > 0 and now - created <= max(3600, stale_max_seconds):
        return candidates, "STALE"

    return None, "EXPIRED"


def quarantine_url(
    url: str,
    *,
    reason: str,
    status_code: int | None = None,
    ttl_seconds: int | None = None,
) -> None:
    raw = str(url or "").strip()
    if not raw:
        return

    code = int(status_code or 0)
    if ttl_seconds is None:
        if code in {404, 410}:
            ttl_seconds = 7 * 86400
        elif code in {401, 403}:
            ttl_seconds = 6 * 3600
        elif code == 429:
            ttl_seconds = 30 * 60
        elif reason in {"corrupt", "invalid_media", "mime"}:
            ttl_seconds = 24 * 3600
        else:
            ttl_seconds = 30 * 60

    key = _hash_text(raw)
    now = _now()
    with _Lock():
        data = _load(QUARANTINE_STATE, {"version": "1.0", "urls": {}})
        if not isinstance(data, dict):
            data = {"version": "1.0", "urls": {}}
        urls = data.get("urls")
        if not isinstance(urls, dict):
            urls = {}
        urls[key] = {
            "url": raw,
            "reason": str(reason),
            "status_code": code,
            "until": now + max(60, int(ttl_seconds)),
            "updated_at": now,
        }
        # Evict expired entries while writing.
        urls = {
            k: v for k, v in urls.items()
            if isinstance(v, dict) and float(v.get("until", 0) or 0) > now
        }
        data["urls"] = urls
        data["updated_at"] = now
        _atomic(QUARANTINE_STATE, data)


def url_allowed(url: str) -> tuple[bool, str]:
    raw = str(url or "").strip()
    if not raw:
        return False, "EMPTY_URL"
    key = _hash_text(raw)
    data = _load(QUARANTINE_STATE, {"urls": {}})
    urls = data.get("urls", {}) if isinstance(data, dict) else {}
    entry = urls.get(key) if isinstance(urls, dict) else None
    if not isinstance(entry, dict):
        return True, "OK"
    if float(entry.get("until", 0.0) or 0.0) <= _now():
        return True, "EXPIRED"
    return False, str(entry.get("reason", "quarantined") or "quarantined")


def _blob_path(url: str) -> Path:
    return CACHE_DIR / "blobs" / f"{_hash_text(str(url or ''))}.bin"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()
    except OSError:
        return ""


def cache_validated_media(
    url: str,
    source_file: str | os.PathLike[str],
    *,
    provider: str = "",
    metadata: dict[str, Any] | None = None,
) -> bool:
    raw = str(url or "").strip()
    src = Path(source_file)
    if not raw or not src.is_file():
        return False

    try:
        size = int(src.stat().st_size)
    except OSError:
        return False
    if size <= 1000:
        return False

    digest = _file_sha256(src)
    if not digest:
        return False

    blob = _blob_path(raw)
    blob.parent.mkdir(parents=True, exist_ok=True)
    tmp = blob.with_name(f".{blob.name}.{os.getpid()}.tmp")
    try:
        shutil.copy2(src, tmp)
        if _file_sha256(tmp) != digest:
            raise OSError("cache copy hash mismatch")
        os.replace(tmp, blob)
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return False

    with _Lock():
        data = _load(BLOB_INDEX, {"version": "1.0", "items": {}})
        if not isinstance(data, dict):
            data = {"version": "1.0", "items": {}}
        items = data.get("items")
        if not isinstance(items, dict):
            items = {}
        key = _hash_text(raw)
        items[key] = {
            "url": raw,
            "blob": str(blob),
            "sha256": digest,
            "size_bytes": size,
            "provider": str(provider or provider_from_url(raw)),
            "metadata": metadata if isinstance(metadata, dict) else {},
            "cached_at": _now(),
            "last_used_at": _now(),
        }
        data["items"] = items
        data["updated_at"] = _now()
        _atomic(BLOB_INDEX, data)
    return True


def restore_cached_media(
    url: str,
    destination: str | os.PathLike[str],
) -> bool:
    raw = str(url or "").strip()
    if not raw:
        return False
    key = _hash_text(raw)
    data = _load(BLOB_INDEX, {"items": {}})
    items = data.get("items", {}) if isinstance(data, dict) else {}
    item = items.get(key) if isinstance(items, dict) else None
    if not isinstance(item, dict):
        return False

    blob = Path(str(item.get("blob", "") or ""))
    if not blob.is_file():
        return False

    expected_sha = str(item.get("sha256", "") or "")
    if expected_sha and _file_sha256(blob) != expected_sha:
        try:
            blob.unlink(missing_ok=True)
        except OSError:
            pass
        return False

    dest = Path(destination)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f".{dest.name}.{os.getpid()}.cachetmp")
    try:
        shutil.copy2(blob, tmp)
        if expected_sha and _file_sha256(tmp) != expected_sha:
            raise OSError("restored cache hash mismatch")
        os.replace(tmp, dest)
        return True
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        return False


def cache_stats() -> dict[str, Any]:
    data = _load(BLOB_INDEX, {"items": {}})
    items = data.get("items", {}) if isinstance(data, dict) else {}
    count = 0
    total = 0
    if isinstance(items, dict):
        for item in items.values():
            if not isinstance(item, dict):
                continue
            path = Path(str(item.get("blob", "") or ""))
            try:
                if path.is_file():
                    count += 1
                    total += path.stat().st_size
            except OSError:
                continue
    return {"items": count, "bytes": total}


def prune_cache(
    *,
    max_bytes: int | None = None,
    max_age_days: int | None = None,
) -> dict[str, Any]:
    if max_bytes is None:
        try:
            max_gb = float(os.getenv("SAP_MEDIA_CACHE_MAX_GB", "1.5") or 1.5)
        except (TypeError, ValueError):
            max_gb = 1.5
        max_bytes = int(max(0.25, min(max_gb, 8.0)) * 1024**3)
    if max_age_days is None:
        try:
            max_age_days = int(os.getenv("SAP_MEDIA_CACHE_MAX_DAYS", "30") or 30)
        except (TypeError, ValueError):
            max_age_days = 30
        max_age_days = max(3, min(max_age_days, 180))

    now = _now()
    cutoff = now - max_age_days * 86400

    with _Lock():
        data = _load(BLOB_INDEX, {"version": "1.0", "items": {}})
        items = data.get("items", {}) if isinstance(data, dict) else {}
        if not isinstance(items, dict):
            items = {}

        valid: list[tuple[str, dict[str, Any], Path, int, float]] = []
        removed = 0
        freed = 0

        for key, item in items.items():
            if not isinstance(item, dict):
                continue
            path = Path(str(item.get("blob", "") or ""))
            try:
                size = int(path.stat().st_size)
            except OSError:
                continue
            used = float(item.get("last_used_at", item.get("cached_at", 0)) or 0)
            if used and used < cutoff:
                try:
                    path.unlink(missing_ok=True)
                    removed += 1
                    freed += size
                except OSError:
                    pass
                continue
            valid.append((key, item, path, size, used))

        total = sum(row[3] for row in valid)
        if total > max_bytes:
            valid.sort(key=lambda row: row[4])
            kept = []
            for row in valid:
                if total > max_bytes:
                    try:
                        row[2].unlink(missing_ok=True)
                        removed += 1
                        freed += row[3]
                        total -= row[3]
                        continue
                    except OSError:
                        pass
                kept.append(row)
            valid = kept

        data["items"] = {key: item for key, item, _, _, _ in valid}
        data["updated_at"] = now
        _atomic(BLOB_INDEX, data)

    return {
        "removed": removed,
        "freed_bytes": freed,
        "remaining_items": len(valid),
        "remaining_bytes": sum(row[3] for row in valid),
        "max_bytes": max_bytes,
        "max_age_days": max_age_days,
    }


__all__ = [
    "cache_query_result",
    "get_cached_query",
    "provider_allowed",
    "record_provider_result",
    "quarantine_url",
    "url_allowed",
    "cache_validated_media",
    "restore_cached_media",
    "provider_from_url",
    "cache_stats",
    "prune_cache",
]
