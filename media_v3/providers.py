from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Any
import requests

@dataclass(frozen=True)
class ProviderStatus:
    enabled: bool
    reason: str = "READY"

class ProviderAdapter:
    name = "base"

    def status(self) -> ProviderStatus:
        return ProviderStatus(True)

    def search(self, query: str, must=None, soft_must=None, avoid=None) -> list[dict[str, Any]]:
        raise NotImplementedError

def _request(url: str, *, params=None, headers=None):
    return requests.get(url, params=params, headers=headers, timeout=(5, 12))

class PexelsAdapter(ProviderAdapter):
    name = "pexels"
    def status(self):
        return ProviderStatus(bool(os.getenv("PEXELS_API_KEY")), "READY" if os.getenv("PEXELS_API_KEY") else "NO_API_KEY")
    def search(self, query, must=None, soft_must=None, avoid=None):
        key=os.getenv("PEXELS_API_KEY")
        if not key: return []
        out=[]; session=requests.Session()
        for endpoint,kind,root in [
            ("https://api.pexels.com/v1/videos/search","video","videos"),
            ("https://api.pexels.com/v1/search","image","photos"),
        ]:
            r=session.get(endpoint,headers={"Authorization":key},params={
                "query":query,"orientation":"portrait","size":"medium","locale":"pt-BR","per_page":20
            },timeout=(5,12))
            if r.status_code==429: raise RuntimeError("RATE_LIMIT")
            r.raise_for_status()
            for item in r.json().get(root) or []:
                if kind=="video":
                    files=item.get("video_files") or []
                    portrait=[f for f in files if f.get("link") and int(f.get("width") or 0)<=int(f.get("height") or 0)]
                    pool=portrait or [f for f in files if f.get("link")]
                    if not pool: continue
                    selected=max(pool,key=lambda f:int(f.get("width") or 0)*int(f.get("height") or 0))
                    url=selected.get("link")
                    description=" ".join(str(x) for x in (item.get("url",""),item.get("user",{}).get("name",""),query) if x)
                    provenance={"provider":self.name,"asset_id":str(item.get("id") or ""),
                                "source_url":str(item.get("url") or ""),
                                "creator":str(item.get("user",{}).get("name") or ""),
                                "query":query,"width":selected.get("width"),"height":selected.get("height"),
                                "duration":item.get("duration")}
                else:
                    src=item.get("src") or {}
                    url=src.get("portrait") or src.get("large2x") or src.get("large") or src.get("original")
                    description=str(item.get("alt") or "")
                    provenance={"provider":self.name,"asset_id":str(item.get("id") or ""),
                                "source_url":str(item.get("url") or ""),
                                "creator":str(item.get("photographer") or ""),"query":query}
                if url:
                    out.append({"provider":self.name,"kind":kind,"id":str(item.get("id") or ""),
                                "url":url,"description":description,"provenance":provenance,"license":"Pexels"})
        return out

class PixabayAdapter(ProviderAdapter):
    name="pixabay"
    def status(self):
        return ProviderStatus(bool(os.getenv("PIXABAY_API_KEY")), "READY" if os.getenv("PIXABAY_API_KEY") else "NO_API_KEY")
    def search(self, query, must=None, soft_must=None, avoid=None):
        key=os.getenv("PIXABAY_API_KEY")
        if not key: return []
        out=[]
        for endpoint,kind in [("https://pixabay.com/api/videos/","video"),("https://pixabay.com/api/","image")]:
            params={"key":key,"q":query[:100],"per_page":25,"safesearch":"true","lang":"en"}
            if kind=="image": params.update({"image_type":"photo","orientation":"vertical"})
            else: params.update({"video_type":"film"})
            r=_request(endpoint,params=params)
            if r.status_code==429: raise RuntimeError("RATE_LIMIT")
            r.raise_for_status()
            for item in r.json().get("hits") or []:
                if kind=="video":
                    videos=item.get("videos") or {}; variant=videos.get("medium") or videos.get("small") or videos.get("tiny")
                    url=variant.get("url") if isinstance(variant,dict) else None
                else:
                    url=item.get("largeImageURL") or item.get("webformatURL")
                if not url: continue
                tags=str(item.get("tags") or "")
                out.append({"provider":self.name,"kind":kind,"id":str(item.get("id") or ""),"url":url,
                            "description":tags,"tags":tags,
                            "provenance":{"provider":self.name,"asset_id":str(item.get("id") or ""),
                                          "source_url":str(item.get("pageURL") or ""),
                                          "creator":str(item.get("user") or ""),"query":query,"tags":tags},
                            "license":"Pixabay Content License"})
        return out

class WikimediaAdapter(ProviderAdapter):
    name="wikimedia"
    def search(self, query, must=None, soft_must=None, avoid=None):
        r=_request("https://commons.wikimedia.org/w/api.php",params={
            "action":"query","generator":"search","gsrsearch":query,"gsrnamespace":6,"gsrlimit":20,
            "prop":"imageinfo","iiprop":"url|mime|size|extmetadata","iiurlwidth":1400,
            "format":"json","formatversion":2
        },headers={"User-Agent":"ShortAutoPro/1.0 (media acquisition)"})
        if r.status_code==429: raise RuntimeError("RATE_LIMIT")
        r.raise_for_status(); out=[]
        for item in (r.json().get("query") or {}).get("pages") or []:
            info=(item.get("imageinfo") or [{}])[0]; url=info.get("thumburl") or info.get("url"); mime=str(info.get("mime") or "")
            if not url or not mime.startswith("image/"): continue
            meta=info.get("extmetadata") or {}; title=str(item.get("title") or "")
            desc=" ".join(x for x in (title,str((meta.get("ImageDescription") or {}).get("value") or ""),
                                      str((meta.get("Categories") or {}).get("value") or "")) if x)
            creator=str((meta.get("Artist") or {}).get("value") or "")
            license_name=str((meta.get("LicenseShortName") or {}).get("value") or "")
            out.append({"provider":self.name,"kind":"image","id":str(item.get("pageid") or ""),"url":url,
                        "description":desc,"tags":str((meta.get("Categories") or {}).get("value") or ""),
                        "license":license_name or "Wikimedia Commons",
                        "provenance":{"provider":self.name,"asset_id":str(item.get("pageid") or ""),
                                      "source_url":f"https://commons.wikimedia.org/wiki/{title.replace(' ','_')}",
                                      "creator":creator,"license":license_name,"query":query}})
        return out

class CoverrAdapter(ProviderAdapter):
    name="coverr"
    def status(self):
        key=os.getenv("COVERR_API_KEY")
        return ProviderStatus(bool(key), "READY" if key else "NO_API_KEY")
    def search(self, query, must=None, soft_must=None, avoid=None):
        key=os.getenv("COVERR_API_KEY")
        if not key: return []
        r=_request("https://api.coverr.co/videos/search",headers={"Authorization":f"Bearer {key}"},
                   params={"query":query,"page":0,"page_size":20,"urls":"true"})
        if r.status_code==429: raise RuntimeError("RATE_LIMIT")
        r.raise_for_status(); out=[]
        for item in r.json().get("hits") or []:
            urls=item.get("urls") or {}; url=None
            if isinstance(urls,dict):
                for name in ("mp4_download","mp4","mp4_preview"):
                    if isinstance(urls.get(name),str) and urls[name].startswith("http"):
                        url=urls[name]; break
            if not url: continue
            tags=item.get("tags") or []
            desc=" ".join(x for x in (str(item.get("title") or ""),str(item.get("description") or ""),
                                      " ".join(map(str,tags)) if isinstance(tags,list) else str(tags)) if x)
            aid=str(item.get("id") or item.get("slug") or "")
            out.append({"provider":self.name,"kind":"video","id":aid,"url":url,"description":desc,"tags":tags,
                        "provenance":{"provider":self.name,"asset_id":aid,"source_url":str(item.get("url") or ""),
                                      "license":"Coverr","query":query},"license":"Coverr"})
        return out

class NASAAdapter(ProviderAdapter):
    name="nasa"
    def status(self): return ProviderStatus(True,"READY")
    def search(self, query, must=None, soft_must=None, avoid=None):
        r=_request("https://images-api.nasa.gov/search",params={"q":query,"media_type":"image","page_size":20})
        r.raise_for_status(); out=[]
        for item in (r.json().get("collection") or {}).get("items") or []:
            data=(item.get("data") or [{}])[0]; href=next((x.get("href") for x in item.get("links") or [] if x.get("href")),"")
            if href: out.append({"provider":self.name,"kind":"image","id":str(data.get("nasa_id") or ""),
                                  "url":href,"description":str(data.get("title") or ""),
                                  "provenance":{"provider":self.name,"asset_id":str(data.get("nasa_id") or ""),"query":query}})
        return out

class LocalLibraryAdapter(ProviderAdapter):
    name="local_v3"

    def search(self, query, must=None, soft_must=None, avoid=None):
        try:
            from .library import search_candidates
            return search_candidates(query, must or [], soft_must or [], avoid or [], limit=12)
        except Exception:
            return []

class ProviderRegistry:
    """Compatibility name for the canonical provider router boundary."""

    def __init__(self, providers=None):
        self.providers=list(providers or [
            LocalLibraryAdapter(), PexelsAdapter(), PixabayAdapter(),
            WikimediaAdapter(), CoverrAdapter()
        ])

    def enabled(self):
        return [(p, p.status()) for p in self.providers]

ProviderRouter = ProviderRegistry
