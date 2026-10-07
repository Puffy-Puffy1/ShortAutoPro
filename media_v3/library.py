from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", Path.home() / "ShortAutoPro")).resolve()
ROOT = BASE / ".sap_state" / "media_cache_v3"
INDEX = BASE / ".sap_state" / "media_library_v3.json"
_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm", ".mkv"}


def _tokens(value: Any) -> set[str]:
    text = str(value or "").casefold()
    return set(re.findall(r"[a-z0-9À-ÿ]+", text))


def _atomic_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _load() -> dict[str, Any]:
    try:
        data = json.loads(INDEX.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {"schema_version": "media-library-v3", "assets": []}
    except Exception:
        return {"schema_version": "media-library-v3", "assets": []}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class LocalLibraryV3:
    """Persistent cache of media already accepted by Media Acquisition V3.

    This layer never accepts an asset by itself. Every cached asset was first
    downloaded and validated by V3, and every retrieval rechecks file existence,
    size and SHA-256 before returning it to the acquisition selector.
    """

    def __init__(self, base: Path = BASE):
        self.base = Path(base).resolve()
        self.root = self.base / ".sap_state" / "media_cache_v3"
        self.index = self.base / ".sap_state" / "media_library_v3.json"

    def _read(self) -> dict[str, Any]:
        try:
            data = json.loads(self.index.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {"schema_version": "media-library-v3", "assets": []}
        except Exception:
            return {"schema_version": "media-library-v3", "assets": []}

    def store(self, path: str | Path, *, provider: str, asset_id: str, query: str,
              description: str = "", tags: Any = None, provenance: dict[str, Any] | None = None,
              license_name: str = "") -> dict[str, Any]:
        source = Path(path).expanduser().resolve()
        if not source.is_file() or source.stat().st_size <= 1000:
            raise ValueError("LOCAL_LIBRARY_INVALID_SOURCE")
        if source.suffix.lower() not in _EXTS:
            raise ValueError("LOCAL_LIBRARY_UNSUPPORTED_EXTENSION")

        digest = _sha256(source)
        self.root.mkdir(parents=True, exist_ok=True)
        destination = self.root / f"{digest}{source.suffix.lower()}"
        if not destination.is_file() or _sha256(destination) != digest:
            tmp = destination.with_suffix(destination.suffix + ".part")
            shutil.copy2(source, tmp)
            os.replace(tmp, destination)

        data = self._read()
        assets = [x for x in data.get("assets", []) if isinstance(x, dict)]
        record = {
            "asset_id": f"sha256:{digest[:16]}",
            "sha256": digest,
            "local_path": str(destination),
            "provider": str(provider),
            "asset_id_source": str(asset_id),
            "query": str(query),
            "description": str(description),
            "tags": tags if isinstance(tags, list) else str(tags or ""),
            "provenance": provenance or {},
            "license": str(license_name or ""),
            "kind": "video" if destination.suffix.lower() in {".mp4", ".mov", ".webm", ".mkv"} else "image",
            "size_bytes": destination.stat().st_size,
        }
        assets = [x for x in assets if str(x.get("sha256")) != digest]
        assets.append(record)
        data["schema_version"] = "media-library-v3"
        data["assets"] = assets[-10000:]
        _atomic_json(self.index, data)
        return record

    def search(self, query: str, must: list[str] | None = None,
               soft_must: list[str] | None = None, avoid: list[str] | None = None,
               limit: int = 12) -> list[dict[str, Any]]:
        must = [str(x).strip() for x in (must or []) if str(x).strip()]
        soft = [str(x).strip() for x in (soft_must or []) if str(x).strip()]
        avoid = [str(x).strip() for x in (avoid or []) if str(x).strip()]
        q_tokens = _tokens(query)
        scored: list[dict[str, Any]] = []

        for asset in self._read().get("assets", []):
            if not isinstance(asset, dict):
                continue
            path = Path(str(asset.get("local_path") or "")).expanduser()
            if not path.is_file() or path.stat().st_size <= 1000:
                continue
            expected = str(asset.get("sha256") or "")
            if not expected or _sha256(path) != expected:
                continue

            metadata = " ".join(str(asset.get(k) or "") for k in
                                ("query", "description", "tags", "provider", "provenance", "license"))
            meta_tokens = _tokens(metadata)
            hard_hits = sum(1 for item in must if _tokens(item) <= meta_tokens)
            soft_hits = sum(1 for item in soft if _tokens(item) <= meta_tokens)
            avoid_hits = sum(1 for item in avoid if _tokens(item) <= meta_tokens)
            if avoid_hits:
                continue
            if must and hard_hits != len(must):
                continue

            relevance = len(q_tokens & meta_tokens) / max(1, len(q_tokens)) * 50
            score = relevance + hard_hits * 30 + soft_hits * 12
            scored.append({
                "provider": "local_v3",
                "kind": asset.get("kind") or "image",
                "id": asset.get("asset_id"),
                "url": "file://" + str(path),
                "local_path": str(path),
                "description": asset.get("description") or asset.get("query") or "",
                "tags": asset.get("tags") or "",
                "score": score,
                "hard_hits": hard_hits,
                "soft_hits": soft_hits,
                "avoid_hits": 0,
                "sha256": expected,
                "license": asset.get("license") or "",
                "provenance": asset.get("provenance") or {},
                "source_query": asset.get("query") or "",
            })

        scored.sort(key=lambda x: (float(x["score"]), int(x["hard_hits"]), int(x["soft_hits"])), reverse=True)
        return scored[:max(1, min(int(limit), 32))]

    def status(self) -> dict[str, Any]:
        data = self._read()
        assets = data.get("assets", [])
        return {
            "schema_version": "media-library-v3",
            "assets": len(assets) if isinstance(assets, list) else 0,
            "path": str(self.index),
            "cache_dir": str(self.root),
        }


def search_candidates(query: str, must=None, soft_must=None, avoid=None, limit: int = 12):
    return LocalLibraryV3().search(query, must, soft_must, avoid, limit)


def store(path, **metadata):
    return LocalLibraryV3().store(path, **metadata)
