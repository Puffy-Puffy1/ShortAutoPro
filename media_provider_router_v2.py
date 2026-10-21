#!/usr/bin/env python3
"""Independent provider router for Media Acquisition V2.

Providers are isolated adapters. No provider imports midia.py.
"""
from __future__ import annotations

import math
import os
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests

from media_external_resilience import (
    provider_gate, note_provider_event, note_response, note_exception,
    asset_blocked, mark_asset_bad,
)
from media_validator_v2 import validate

TIMEOUT = float(os.getenv("SAP_MEDIA_API_TIMEOUT", "8") or 8)
DOWNLOAD_TIMEOUT = float(os.getenv("SAP_MEDIA_DOWNLOAD_READ_TIMEOUT", "15") or 15)
WIKIMEDIA_MIN_INTERVAL = max(1.0, float(os.getenv("SAP_WIKIMEDIA_MIN_INTERVAL", "1.5") or 1.5))
_WIKIMEDIA_LAST_REQUEST = 0.0
_WIKIMEDIA_CACHE: dict[str, list[dict[str, Any]]] = {}
BASE = Path(os.getenv("SHORTAUTOPRO_BASE", Path.home() / "ShortAutoPro")).resolve()

def _normalize_image_extension(path: Path) -> Path:
    """Match the stored image suffix to its actual file signature.

    Wikimedia file URLs may return PNG/WebP bytes even when the API candidate
    was classified as a generic image. Keeping those bytes under .jpg causes a
    false CONTENT_SIGNATURE_MISMATCH and rejects otherwise valid media. Unknown
    signatures are left unchanged so the validator still rejects HTML/error pages.
    """
    try:
        with path.open("rb") as stream:
            head = stream.read(16)
    except OSError:
        return path
    actual = None
    if head.startswith(b"\xff\xd8\xff"):
        actual = ".jpg"
    elif head.startswith(b"\x89PNG\r\n\x1a\n"):
        actual = ".png"
    elif head.startswith(b"RIFF") and head[8:12] == b"WEBP":
        actual = ".webp"
    if actual is None or path.suffix.lower() == actual:
        return path
    target = path.with_suffix(actual)
    if target.exists():
        target.unlink()
    path.replace(target)
    return target

def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", str(value or "").casefold()))


_QUERY_STOPWORDS = {
    "a", "an", "the", "of", "in", "on", "at", "by", "for", "from",
    "and", "or", "to", "with", "after", "before", "during", "near",
    "over", "under", "above", "below", "around", "about", "into", "onto",
    "through", "is", "are", "was", "were", "be", "been", "being", "it",
    "its", "this", "that", "these", "those", "as", "via", "old", "scene",
    "photo", "picture", "image", "view", "close", "up",
}
_QUERY_TOKEN_ALIASES = {
    "airplanes": "airplane", "mountains": "mountain", "hikers": "hiker",
    "bills": "bill", "dollars": "dollar", "passengers": "passenger",
    "stairs": "stair", "letters": "letter", "documents": "document",
    "files": "file", "investigators": "investigator",
    "investigations": "investigation", "airliners": "airliner",
    "aircrafts": "aircraft", "pages": "page", "forests": "forest",
    "snowy": "snow", "snowing": "snow", "snowfall": "snow",
    "woodland": "forest", "woodlands": "forest", "woods": "forest",
    "forested": "forest", "taiga": "forest",
}


def _meaningful_query_tokens(value: str) -> set[str]:
    result = set()
    for token in _tokens(value):
        if token in _QUERY_STOPWORDS or len(token) < 3:
            continue
        result.add(_QUERY_TOKEN_ALIASES.get(token, token))
    return result


def _candidate_relevance_text(candidate: dict[str, Any]) -> str:
    # Categories are useful for MUST evidence but too broad to prove shot relevance.
    primary = [
        candidate.get(key)
        for key in ("title", "image_description", "description", "alt", "caption", "name")
        if str(candidate.get(key) or "").strip()
    ]
    if primary:
        return " ".join(str(value) for value in primary)
    return str(candidate.get("descricao") or "")


def query_relevance(query: str, candidate: dict[str, Any]) -> dict[str, Any]:
    """Compare meaningful query terms with asset metadata, excluding query echo/categories."""
    query_terms = _meaningful_query_tokens(query)
    asset_terms = _meaningful_query_tokens(_candidate_relevance_text(candidate))
    matched = sorted(query_terms & asset_terms)
    # Search queries often include setting, location, weather, and narrative context.
    # Requiring 60% of every token rejects valid assets whose title names only the
    # central subject. Require two meaningful metadata overlaps for longer queries;
    # retain one for short queries. MUST/AVOID verification remains a separate gate.
    required = min(2, len(query_terms)) if query_terms else 1
    ratio = len(matched) / len(query_terms) if query_terms else 0.0
    return {
        "ok": bool(query_terms) and len(matched) >= required,
        "matched_terms": matched,
        "matched_count": len(matched),
        "query_term_count": len(query_terms),
        "required_terms": required,
        "ratio": round(ratio, 3),
    }


def _score(query: str, description: str, must: list[str], avoid: list[str]) -> tuple[float,int,int]:
    q = _tokens(query)
    d = _tokens(description)
    hits = sum(1 for x in must if _tokens(x) <= d)
    avoids = sum(1 for x in avoid if _tokens(x) & d)
    overlap = len(q & d) / max(1, len(q))
    return overlap * 60 + hits * 35 - avoids * 60, hits, avoids

def _candidate(provider: str, kind: str, asset_id: Any, url: str, description: str,
               query: str, must: list[str], avoid: list[str], **extra: Any) -> dict[str, Any]:
    score, hits, avoids = _score(query, description, must, avoid)
    return {
        "fonte": provider, "source": provider, "tipo": kind, "id": str(asset_id or ""),
        "url": url, "descricao": description, "score": round(score, 3),
        "must_hits": hits, "avoid_hits": avoids, "evidence_class": "provider_metadata",
        "provenance": {"provider": provider, "asset_id": str(asset_id or ""), "url": url},
        **extra,
    }

class Provider:
    name = "base"
    def search(self, query: str, must: list[str], avoid: list[str]) -> list[dict[str, Any]]:
        raise NotImplementedError

class PexelsProvider(Provider):
    name = "pexels"
    def search(self, query, must, avoid):
        key = os.getenv("PEXELS_API_KEY", "")
        if not key: return []
        allowed, _, _ = provider_gate(self.name)
        if not allowed: return []
        out=[]
        try:
            s=requests.Session()
            for endpoint, kind, root in [
                ("https://api.pexels.com/videos/search","video","videos"),
                ("https://api.pexels.com/v1/search","image","photos"),
            ]:
                r=s.get(endpoint,headers={"Authorization":key},
                        params={"query":query,"orientation":"portrait","per_page":20},timeout=TIMEOUT)
                note_response(self.name,r)
                if not r.ok: continue
                for item in (r.json().get(root) or []):
                    if kind=="video":
                        files=item.get("video_files") or []
                        urls=[x.get("link") for x in files if x.get("link")]
                        if not urls: continue
                        url=max(urls,key=lambda x: 1 if "portrait" in x else 0)
                        desc=f'{item.get("url","")} {item.get("user",{}).get("name","")}'
                        out.append(_candidate(self.name,kind,item.get("id"),url,desc,query,must,avoid))
                    else:
                        src=item.get("src") or {}
                        url=src.get("portrait") or src.get("large2x") or src.get("large") or src.get("original")
                        if not url: continue
                        desc=str(item.get("alt") or "")
                        out.append(_candidate(self.name,kind,item.get("id"),url,desc,query,must,avoid))
            note_provider_event(self.name,"SUCCESS",item_count=len(out))
        except Exception as exc:
            note_exception(self.name,exc)
        return out

class PixabayProvider(Provider):
    name = "pixabay"
    def search(self, query, must, avoid):
        key=os.getenv("PIXABAY_API_KEY","")
        if not key: return []
        allowed,_,_=provider_gate(self.name)
        if not allowed: return []
        out=[]
        try:
            s=requests.Session()
            for endpoint, kind in [
                ("https://pixabay.com/api/videos/","video"),
                ("https://pixabay.com/api/","image"),
            ]:
                params={"key":key,"q":query,"per_page":25,"safesearch":"true"}
                if kind=="image": params.update({"image_type":"photo","orientation":"vertical"})
                r=s.get(endpoint,params=params,timeout=TIMEOUT)
                note_response(self.name,r)
                if not r.ok: continue
                for item in (r.json().get("hits") or []):
                    if kind=="video":
                        videos=item.get("videos") or {}
                        variant=videos.get("medium") or videos.get("small") or videos.get("tiny")
                        url=variant.get("url") if isinstance(variant,dict) else None
                        desc=str(item.get("tags") or "")
                    else:
                        url=item.get("largeImageURL") or item.get("webformatURL")
                        desc=str(item.get("tags") or "")
                    if url: out.append(_candidate(self.name,kind,item.get("id"),url,desc,query,must,avoid))
            note_provider_event(self.name,"SUCCESS",item_count=len(out))
        except Exception as exc:
            note_exception(self.name,exc)
        return out

class CoverrProvider(Provider):
    name="coverr"
    def search(self, query, must, avoid):
        key=os.getenv("COVERR_API_KEY","")
        if not key: return []
        allowed,_,_=provider_gate(self.name)
        if not allowed: return []
        out=[]
        try:
            r=requests.get("https://api.coverr.co/videos",
                headers={"Authorization":f"Bearer {key}"},
                params={"query":query,"page":0,"page_size":20,"urls":"true"},timeout=TIMEOUT)
            note_response(self.name,r)
            if not r.ok: return []
            for item in (r.json().get("hits") or []):
                desc=" ".join(map(str,[item.get("title",""),item.get("description",""),item.get("tags","")]))
                urls=item.get("urls") or {}
                for url in urls.values() if isinstance(urls,dict) else []:
                    if isinstance(url,str) and url.startswith("http"):
                        out.append(_candidate(self.name,"video",item.get("id") or item.get("slug"),url,desc,query,must,avoid))
                        break
            note_provider_event(self.name,"SUCCESS",item_count=len(out))
        except Exception as exc: note_exception(self.name,exc)
        return out

class WikimediaProvider(Provider):
    name="wikimedia"
    def search(self, query, must, avoid):
        allowed, gate_reason, gate_remaining = provider_gate(self.name)
        if not allowed:
            # A circuit-open return is not the same as a genuine empty search.
            # Log only the health reason and duration, never request secrets.
            print(
                f"SAP_MEDIA_PROVIDER_GATE provider={self.name} allowed=false "
                f"reason={str(gate_reason or 'OPEN')} "
                f"remaining_seconds={max(0, int(float(gate_remaining or 0)))}"
            )
            return []
        out=[]
        try:
            # Commons file titles alone are often generic ("File:...jpg").
            # Fetch the file's own structured description and categories so the
            # verifier can evaluate actual asset metadata rather than search text.
            params={"action":"query","generator":"search","gsrsearch":query,
                    "gsrnamespace":6,"gsrlimit":20,
                    "prop":"imageinfo|categories",
                    "iiprop":"url|mime|size|extmetadata","iiurlwidth":1920,
                    "cllimit":"max","format":"json"}
            global _WIKIMEDIA_LAST_REQUEST
            cache_key = str(query).strip().casefold()
            cached = _WIKIMEDIA_CACHE.get(cache_key)
            if cached is not None:
                return [dict(item) for item in cached]
            # Wikimedia Commons applies shared-IP rate limits. Query expansion can
            # otherwise issue several requests per scene in a burst. Serialize and
            # pace requests, then honor Retry-After for temporary 429 responses.
            for attempt in range(3):
                wait_for = WIKIMEDIA_MIN_INTERVAL - (time.monotonic() - _WIKIMEDIA_LAST_REQUEST)
                if wait_for > 0:
                    time.sleep(wait_for)
                r=requests.get(
                    "https://commons.wikimedia.org/w/api.php",
                    params=params,
                    headers={"User-Agent": "ShortAutoPro/2.3 (educational-video-automation; media retrieval; contact: cinepulsar.contato@gmail.com)"},
                    timeout=TIMEOUT,
                )
                _WIKIMEDIA_LAST_REQUEST = time.monotonic()
                event = note_response(self.name,r)
                if r.status_code == 429 and attempt < 2:
                    retry_after = r.headers.get("Retry-After", "")
                    try:
                        delay = min(20.0, max(2.0, float(retry_after)))
                    except (TypeError, ValueError):
                        delay = 3.0 * (attempt + 1)
                    print(f"SAP_MEDIA_PROVIDER_RETRY provider=wikimedia status=429 delay={delay:.1f}s attempt={attempt + 1}")
                    time.sleep(delay)
                    continue
                if not r.ok:
                    note_provider_event(self.name, event, status=r.status_code, detail="Wikimedia Commons search HTTP failure")
                    print(f"SAP_MEDIA_PROVIDER_FAILURE provider=wikimedia status={r.status_code}")
                    return []
                break
            pages=(r.json().get("query") or {}).get("pages") or {}
            for item in pages.values():
                info=(item.get("imageinfo") or [{}])[0]
                url=info.get("thumburl") or info.get("url")
                mime=str(info.get("mime") or "")
                if not url or not mime.startswith("image/"): continue
                title=str(item.get("title") or "")
                ext=info.get("extmetadata") or {}
                def metadata_value(key):
                    value=ext.get(key) or {}
                    raw=value.get("value","") if isinstance(value,dict) else value
                    # Commons descriptions may contain HTML markup. Keep plain
                    # descriptive text only; never mix in the search query.
                    raw=re.sub(r"<[^>]*>", " ", str(raw or ""))
                    return re.sub(r"\s+", " ", raw).strip()
                categories=[
                    str(category.get("title") or "").replace("Category:", "")
                    for category in (item.get("categories") or [])
                    if isinstance(category,dict) and category.get("title")
                ]
                description_parts=[
                    title,
                    metadata_value("ObjectName"),
                    metadata_value("ImageDescription"),
                    " ".join(categories),
                ]
                desc=" ".join(part for part in description_parts if part)
                out.append(_candidate(
                    self.name,"image",item.get("pageid"),url,desc,query,must,avoid,
                    title=title,
                    image_description=metadata_value("ImageDescription"),
                    tags=categories,
                    license="Wikimedia Commons",
                ))
            _WIKIMEDIA_CACHE[cache_key] = [dict(item) for item in out]
            note_provider_event(self.name,"SUCCESS",item_count=len(out))
        except Exception as exc:
            note_exception(self.name, exc)
            # Keep live provider failures diagnosable without exposing URLs,
            # request parameters, credentials, or upstream response bodies.
            print(f"SAP_MEDIA_PROVIDER_FAILURE provider={self.name} error={type(exc).__name__}", flush=True)
        return out

class LocalLibraryProvider(Provider):
    name="local"
    def search(self, query, must, avoid):
        try:
            from shortauto_asset_library import search_candidates
            return search_candidates(query,must,avoid,limit=12)
        except Exception:
            return []

def _query_variants(query: str, must: list[str] | None = None) -> list[str]:
    """Build a small, deterministic set of retrieval fallbacks.

    Query expansion only changes provider search terms. MUST and AVOID checks
    remain strict and are enforced separately before an asset can be accepted.
    """
    raw = " ".join(str(query or "").split()).strip()
    if not raw:
        return []

    must_terms = [str(item).strip() for item in (must or []) if str(item).strip()]
    normalized = re.sub(r"[^A-Za-z0-9À-ÿ]+", " ", raw).strip()
    words = normalized.split()
    aliases = {
        "security sensor": ("motion sensor", "alarm sensor", "door sensor"),
        "ship": ("vessel", "boat", "watercraft"),
        "boat": ("ship", "vessel", "watercraft"),
        "vessel": ("ship", "boat", "watercraft"),
        "ocean": ("sea", "open water"),
        "sea": ("ocean", "open water"),
        "car": ("automobile", "motor vehicle", "road vehicle", "cars"),
        "automobile": ("car", "motor vehicle", "road vehicle"),
        "vehicle": ("car", "automobile", "motor vehicle", "road vehicle"),
        "canvas tent": ("tent", "camping tent", "canvas shelter", "tent in snow"),
        "tent": ("canvas tent", "camping tent", "tent in snow", "snow tent"),
        "snow": ("snowfall", "snow-covered", "snowy landscape", "winter camping"),
        "darkness": ("night", "nighttime", "at night", "low-light", "dark"),
        "forest": ("woodland", "woodlands", "woods", "pine forest", "coniferous forest", "taiga"),
        "train": ("railway train", "locomotive", "rail transport", "passenger train"),
        "torn tent": ("ripped tent", "damaged tent", "torn canvas tent"),
        "topographic map": ("topographical map", "contour map", "relief map", "elevation map"),
    }

    candidates = [raw]
    if normalized and normalized.casefold() != raw.casefold():
        candidates.append(normalized)

    # Keep the combined editorial anchors early for multi-anchor scenes.
    if must_terms:
        candidates.append(" ".join(must_terms))

    # Add a limited number of context-preserving variants before broad aliases.
    for term in must_terms:
        term_aliases = aliases.get(term.casefold(), ())
        if not term_aliases:
            continue
        pattern = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)
        if pattern.search(raw):
            candidates.append(pattern.sub(term_aliases[0], raw, count=1))
        else:
            candidates.append(term_aliases[0])

    # Preserve each explicit anchor as a standalone retrieval option.
    candidates.extend(must_terms)

    # Include bounded alias fallbacks for catalogs using alternate labels.
    for term in must_terms:
        candidates.extend(aliases.get(term.casefold(), ()))

    if len(words) > 4:
        candidates.append(" ".join(words[:4]))
    if len(words) > 2:
        candidates.append(" ".join(words[:2]))
    if len(must_terms) == 1:
        candidates.append(must_terms[0])

    # Deduplicate once, preserving priority and limiting provider requests.
    result = []
    seen = set()
    max_variants = 8 if any(term.casefold() in aliases for term in must_terms) else 4
    for candidate in candidates:
        item = " ".join(str(candidate or "").split()).strip()
        key = item.casefold()
        if item and key not in seen:
            seen.add(key)
            result.append(item)
            if len(result) == max_variants:
                break
    return result

class MediaProviderRouterV2:
    def __init__(self, providers=None):
        self.providers = providers or [
            PexelsProvider(), PixabayProvider(), WikimediaProvider(), CoverrProvider(), LocalLibraryProvider()
        ]

    def search(self, query, must, avoid, **_: Any):
        candidates = []
        variants = _query_variants(query, must)
        for provider in self.providers:
            provider_candidates = []
            # Query variants are bounded retrieval fallbacks. Do not stop at the
            # first non-empty result: a provider may return generic assets for
            # the editorial query while a MUST-specific variant contains assets
            # whose metadata can actually prove the explicit requirements.
            for variant in variants:
                try:
                    found = provider.search(variant, must, avoid)
                except Exception:
                    found = []
                if found:
                    provider_candidates.extend(found)
                    # Stop expanding once this provider has a safe result set
                    # with explicit metadata hits for every MUST term. This
                    # reduces repeated calls to rate-limited public providers.
                    if any(
                        query_relevance(query, item)["ok"]
                        and (not must or int(item.get("must_hits", 0) or 0) >= len(must))
                        and int(item.get("avoid_hits", 0) or 0) == 0
                        for item in found
                    ):
                        break
            candidates.extend(provider_candidates)

        # The same provider asset can be returned by multiple retrieval
        # variants. Keep one canonical candidate so query expansion cannot
        # duplicate downloads or distort ranking.
        unique = {}
        for candidate in candidates:
            key = (
                str(candidate.get("fonte") or candidate.get("source") or ""),
                str(candidate.get("id") or ""),
                str(candidate.get("url") or ""),
            )
            unique.setdefault(key, candidate)
        candidates = list(unique.values())
        for candidate in candidates:
            candidate["query_relevance"] = query_relevance(query, candidate)

        # Deterministic ordering: relevant metadata first, then MUST evidence and score.
        # AVOID is never relaxed here; prepare() still enforces the MUST contract.
        candidates = [
            c for c in candidates
            if int(c.get("avoid_hits", 0) or 0) == 0
        ]
        candidates.sort(
            key=lambda c: (
                bool((c.get("query_relevance") or {}).get("ok")),
                int((c.get("query_relevance") or {}).get("matched_count", 0) or 0),
                float((c.get("query_relevance") or {}).get("ratio", 0) or 0),
                int(c.get("must_hits", 0) or 0),
                float(c.get("score", 0) or 0),
                str(c.get("fonte", "")),
                str(c.get("id", "")),
            ),
            reverse=True,
        )
        # Live runs need enough acquisition telemetry to distinguish empty
        # providers from candidates rejected by strict semantic verification.
        # Do not print URLs, API credentials, or full provider metadata.
        if os.getenv("FIRST_VIDEO_LIVE") == "1":
            provider_counts = {}
            for candidate in candidates:
                name = str(candidate.get("fonte") or candidate.get("source") or "?")
                provider_counts[name] = provider_counts.get(name, 0) + 1
            summary = ",".join(
                f"{name}:{count}" for name, count in sorted(provider_counts.items())
            ) or "-"
            max_metadata_hits = max(
                (int(candidate.get("must_hits", 0) or 0) for candidate in candidates),
                default=0,
            )
            # Log a bounded, normalized query so failed live runs can be
            # traced to scene/query generation without dumping provider payloads.
            safe_query = re.sub(r"\s+", " ", str(query or "")).strip()[:180]
            safe_must = ",".join(
                re.sub(r"\s+", " ", str(term or "")).strip()[:48]
                for term in (must or []) if str(term or "").strip()
            )[:180] or "-"
            safe_variants = " || ".join(
                re.sub(r"\s+", " ", str(variant or "")).strip()[:64]
                for variant in variants
            )[:220] or "-"
            print(
                "SAP_MEDIA_SEARCH "
                f"query={safe_query!r} must={safe_must!r} "
                f"query_chars={len(str(query))} variants={len(variants)} "
                f"variant_samples={safe_variants!r} "
                f"candidates={len(candidates)} providers={summary} "
                f"max_metadata_must_hits={max_metadata_hits}",
                flush=True,
            )
        return candidates
    def download(self, candidate: dict[str,Any], scene_number: int, short_id: str) -> tuple[bool,str,dict[str,Any]]:
        provider=str(candidate.get("fonte") or candidate.get("source") or "unknown")
        url=str(candidate.get("url") or "")
        if not url: return False,"",{"error_class":"DOWNLOAD_FAILED"}
        blocked,reason,_=asset_blocked(url,provider=provider,asset_id=candidate.get("id"))
        if blocked: return False,"",{"error_class":"ASSET_QUARANTINED","reason":reason}
        ext=".mp4" if str(candidate.get("tipo","")).lower() in {"video","vídeo"} else ".jpg"
        safe_short_id = re.sub(r"[^A-Za-z0-9._-]", "_", str(short_id))
        if not safe_short_id or safe_short_id != str(short_id) or ".." in safe_short_id:
            return False, "", {"error_class": "SHORT_ID_INVALID"}
        if int(scene_number) < 1 or int(scene_number) > 999:
            return False, "", {"error_class": "SCENE_NUMBER_INVALID"}
        outdir = (BASE / "imagens" / f"short_{safe_short_id}").resolve()
        base_media = (BASE / "imagens").resolve()
        try:
            outdir.relative_to(base_media)
        except ValueError:
            return False, "", {"error_class": "OUTPUT_PATH_INVALID"}
        outdir.mkdir(parents=True, exist_ok=True)
        dest = outdir / f"scene_{int(scene_number):02d}_{provider}{ext}"
        try:
            dest.unlink(missing_ok=True)
            # Wikimedia Commons requires an identifiable User-Agent on file
            # downloads too; setting it only on API search does not carry over.
            # Keep provider-specific identity while giving every external host a
            # stable fallback User-Agent.
            headers = {
                "User-Agent": (
                    "ShortAutoPro/2.3 (educational-video-automation; media retrieval; "
                    "contact: cinepulsar.contato@gmail.com)"
                    if provider.casefold() == "wikimedia"
                    else "ShortAutoPro/2.3 (media retrieval; educational-video-automation)"
                ),
                "Accept": "image/*,video/*;q=0.9,*/*;q=0.8",
            }
            # Retry transient transport failures before quarantining an otherwise
            # semantically verified asset. A single timeout/5xx/429 must not
            # permanently poison a URL that may work on the next attempt.
            last_status = None
            for attempt in range(3):
                try:
                    with requests.get(url,headers=headers,stream=True,timeout=DOWNLOAD_TIMEOUT) as r:
                        last_status = r.status_code
                        if not r.ok:
                            note_response(provider,r)
                            if r.status_code == 429 or 500 <= r.status_code <= 599:
                                if attempt < 2:
                                    retry_after = r.headers.get("Retry-After", "")
                                    try:
                                        delay = min(8.0, max(1.0, float(retry_after)))
                                    except (TypeError, ValueError):
                                        delay = float(attempt + 1)
                                    print(f"SAP_MEDIA_DOWNLOAD_RETRY provider={provider} status={r.status_code} attempt={attempt + 1} delay={delay:.1f}s")
                                    time.sleep(delay)
                                    continue
                            mark_asset_bad(url,provider=provider,asset_id=candidate.get("id"),status=r.status_code)
                            dest.unlink(missing_ok=True)
                            print(f"SAP_MEDIA_DOWNLOAD_FAILURE provider={provider} status={r.status_code} class=HTTP")
                            return False,"",{"error_class":"DOWNLOAD_FAILED","status":r.status_code}
                        with dest.open("wb") as fh:
                            for chunk in r.iter_content(1024*1024):
                                if chunk:
                                    fh.write(chunk)
                    break
                except requests.Timeout as exc:
                    note_exception(provider,exc)
                    dest.unlink(missing_ok=True)
                    if attempt < 2:
                        delay = float(attempt + 1)
                        print(f"SAP_MEDIA_DOWNLOAD_RETRY provider={provider} class=TIMEOUT attempt={attempt + 1} delay={delay:.1f}s")
                        time.sleep(delay)
                        continue
                    mark_asset_bad(url,provider=provider,asset_id=candidate.get("id"),reason="TIMEOUT")
                    print(f"SAP_MEDIA_DOWNLOAD_FAILURE provider={provider} class=TIMEOUT attempts=3")
                    return False,"",{"error_class":"PROVIDER_TIMEOUT"}
                except requests.RequestException as exc:
                    note_exception(provider,exc)
                    dest.unlink(missing_ok=True)
                    if attempt < 2:
                        delay = float(attempt + 1)
                        print(f"SAP_MEDIA_DOWNLOAD_RETRY provider={provider} class={type(exc).__name__} attempt={attempt + 1} delay={delay:.1f}s")
                        time.sleep(delay)
                        continue
                    mark_asset_bad(url,provider=provider,asset_id=candidate.get("id"),reason="REQUEST_ERROR")
                    print(f"SAP_MEDIA_DOWNLOAD_FAILURE provider={provider} class={type(exc).__name__} attempts=3")
                    return False,"",{"error_class":"DOWNLOAD_FAILED"}
            if ext == ".jpg":
                dest = _normalize_image_extension(dest)
            result=validate(dest)
            candidate["asset_id"]=candidate.get("id")
            candidate["provenance"]=dict(candidate.get("provenance") or {})
            candidate["provenance"]["provider"]=provider
            return True,str(dest),result
        except Exception as exc:
            # A local media-validation rejection is an asset-quality event,
            # not proof that the provider is unhealthy. Counting ValueError as
            # provider failure can open the circuit after several bad candidates
            # and suppress unrelated queries/scenes. Only transport/unexpected
            # failures contribute to provider-health resilience state.
            if not isinstance(exc, ValueError):
                note_exception(provider, exc)
            # Keep diagnostics actionable without printing signed URLs, headers,
            # tokens, or provider response bodies.
            # Validation exceptions use stable, non-sensitive reason codes
            # (e.g. MEDIA_TOO_SMALL, CONTENT_SIGNATURE_MISMATCH). Expose only
            # those codes: never echo exception text, paths, URLs, or response data.
            reason_code = "UNEXPECTED"
            if isinstance(exc, ValueError):
                candidate_reason = str(exc).strip().upper()
                if re.fullmatch(r"[A-Z][A-Z0-9_]{0,63}", candidate_reason):
                    reason_code = candidate_reason
            print(
                f"SAP_MEDIA_DOWNLOAD_FAILURE provider={provider} "
                f"class={type(exc).__name__} reason={reason_code} "
                f"stage=DOWNLOAD_OR_VALIDATE",
                flush=True,
            )
            quarantine_reason = {
                "MEDIA_TOO_SMALL": "TOO_SMALL",
                "CONTENT_SIGNATURE_MISMATCH": "CONTENT_TYPE",
                "UNSUPPORTED_EXTENSION": "CONTENT_TYPE",
                "PROBE_FAIL": "PROBE_FAIL",
                "PROBE_INVALID_JSON": "PROBE_FAIL",
                "NO_STREAM": "PROBE_FAIL",
                "NO_VIDEO_STREAM": "PROBE_FAIL",
                "INVALID_DIMENSIONS": "CORRUPT",
                "INVALID_DURATION": "CORRUPT",
            }.get(reason_code, "CORRUPT")
            mark_asset_bad(url,provider=provider,asset_id=candidate.get("id"),reason=quarantine_reason)
            try: dest.unlink()
            except OSError: pass
            return False,"",{"error_class":"VALIDATION_FAILED"}
