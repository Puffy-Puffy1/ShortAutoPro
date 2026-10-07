#!/usr/bin/env python3
"""LEGACY compatibility provider router for Media Engine V2.

Canonical provider routing is owned by media_v3.providers / ProviderRouter.
This module remains only while old consumers are being mapped and retired.
It must not be used as a second production provider authority.
"""
from __future__ import annotations

import os
import re
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
BASE = Path(os.getenv("SHORTAUTOPRO_BASE", Path.home() / "ShortAutoPro")).resolve()

def _tokens(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", str(value or "").casefold()))

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
        allowed,_,_=provider_gate(self.name)
        if not allowed: return []
        out=[]
        try:
            params={"action":"query","generator":"search","gsrsearch":query,
                    "gsrnamespace":6,"gsrlimit":20,"prop":"imageinfo",
                    "iiprop":"url|mime|size","iiurlwidth":1400,"format":"json"}
            r=requests.get("https://commons.wikimedia.org/w/api.php",params=params,timeout=TIMEOUT)
            note_response(self.name,r)
            if not r.ok: return []
            pages=(r.json().get("query") or {}).get("pages") or {}
            for item in pages.values():
                info=(item.get("imageinfo") or [{}])[0]
                url=info.get("thumburl") or info.get("url")
                mime=str(info.get("mime") or "")
                if not url or not mime.startswith("image/"): continue
                desc=str(item.get("title") or "")
                out.append(_candidate(self.name,"image",item.get("pageid"),url,desc,query,must,avoid,
                                      license="Wikimedia Commons"))
            note_provider_event(self.name,"SUCCESS",item_count=len(out))
        except Exception as exc: note_exception(self.name,exc)
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
    """Return bounded, deterministic fallbacks for providers that return no hits.

    The fallback only changes the provider search query. It never relaxes MUST
    or AVOID verification; MediaProviderV2.prepare() remains the semantic gate.
    This prevents a single overly-specific/empty provider query from becoming
    an immediate scene-level providers_empty failure.
    """
    raw = " ".join(str(query or "").split()).strip()
    if not raw:
        return []
    variants = [raw]
    must_terms = [str(item).strip() for item in (must or []) if str(item).strip()]
    if must_terms:
        combined = " ".join(must_terms)
        if combined and combined.casefold() not in {v.casefold() for v in variants}:
            variants.append(combined)
        for term in must_terms:
            if term.casefold() not in {v.casefold() for v in variants}:
                variants.append(term)
    # Explicit MUST anchors are part of retrieval recovery. They do not relax
    # acceptance; they give providers a chance to return assets whose metadata
    # proves the required visual concept even when the editorial query is noisy.
    must_terms = [str(item).strip() for item in (must or []) if str(item).strip()]
    if must_terms:
        combined = " ".join(must_terms)
        if combined and combined.casefold() not in {v.casefold() for v in variants}:
            variants.append(combined)
        for term in must_terms:
            if term.casefold() not in {v.casefold() for v in variants}:
                variants.append(term)

    # Retrieval aliases are query expansion only. Acceptance remains fail-closed
    # because media_must_verifier independently proves the explicit MUST from
    # the returned asset evidence.
    retrieval_aliases = {
        "security sensor": ("motion sensor", "alarm sensor", "door sensor"),
    }
    for term in must_terms:
        for alias in retrieval_aliases.get(term.casefold(), ()):
            if alias.casefold() not in {v.casefold() for v in variants}:
                variants.append(alias)

    # Strip punctuation while preserving the original word order.
    normalized = re.sub(r"[^A-Za-z0-9À-ÿ]+", " ", raw).strip()
    if normalized and normalized.casefold() not in {v.casefold() for v in variants}:
        variants.append(normalized)
    words = normalized.split()
    # Provider APIs can fail on long natural-language queries. Try the most
    # informative bounded prefixes, then a compact two-term query.
    if len(words) > 4:
        variants.append(" ".join(words[:4]))
    if len(words) > 2:
        variants.append(" ".join(words[:2]))
    # Deduplicate case-insensitively and cap network amplification.
    out = []
    seen = set()
    for item in variants:
        key = item.casefold()
        if key and key not in seen:
            seen.add(key)
            out.append(item)
    max_variants = 8 if any(
        str(item).strip().casefold() == "security sensor"
        for item in (must or [])
    ) else 4
    return out[:max_variants]


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

        # Deterministic ordering: evidence/MUST first, then score, then provider/id.
        # AVOID is never relaxed here; prepare() still enforces the MUST contract.
        candidates = [
            c for c in candidates
            if int(c.get("avoid_hits", 0) or 0) == 0
        ]
        candidates.sort(
            key=lambda c: (
                int(c.get("must_hits", 0) or 0),
                float(c.get("score", 0) or 0),
                str(c.get("fonte", "")),
                str(c.get("id", "")),
            ),
            reverse=True,
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
            with requests.get(url,stream=True,timeout=DOWNLOAD_TIMEOUT) as r:
                if not r.ok:
                    note_response(provider,r)
                    mark_asset_bad(url,provider=provider,asset_id=candidate.get("id"),status=r.status_code)
                    dest.unlink(missing_ok=True)
                    return False,"",{"error_class":"DOWNLOAD_FAILED","status":r.status_code}
                with dest.open("wb") as fh:
                    for chunk in r.iter_content(1024*1024):
                        if chunk:
                            fh.write(chunk)
            result=validate(dest)
            candidate["asset_id"]=candidate.get("id")
            candidate["provenance"]=dict(candidate.get("provenance") or {})
            candidate["provenance"]["provider"]=provider
            return True,str(dest),result
        except requests.Timeout as exc:
            note_exception(provider,exc); mark_asset_bad(url,provider=provider,asset_id=candidate.get("id"),reason="TIMEOUT")
            dest.unlink(missing_ok=True)
            return False,"",{"error_class":"PROVIDER_TIMEOUT"}
        except requests.RequestException as exc:
            note_exception(provider,exc); mark_asset_bad(url,provider=provider,asset_id=candidate.get("id"),reason="REQUEST_ERROR")
            dest.unlink(missing_ok=True)
            return False,"",{"error_class":"DOWNLOAD_FAILED"}
        except Exception as exc:
            note_exception(provider,exc); mark_asset_bad(url,provider=provider,asset_id=candidate.get("id"),reason="CORRUPT")
            try: dest.unlink()
            except OSError: pass
            return False,"",{"error_class":"VALIDATION_FAILED"}
