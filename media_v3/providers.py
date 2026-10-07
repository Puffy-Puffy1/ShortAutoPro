from __future__ import annotations
import os, re
from dataclasses import dataclass
from typing import Any, Callable
import requests

@dataclass(frozen=True)
class ProviderStatus:
    enabled: bool
    reason: str = "READY"

class ProviderAdapter:
    name="base"
    def status(self) -> ProviderStatus: return ProviderStatus(True)
    def search(self, query: str) -> list[dict[str, Any]]: raise NotImplementedError

class PexelsAdapter(ProviderAdapter):
    name="pexels"
    def status(self): return ProviderStatus(bool(os.getenv("PEXELS_API_KEY")), "READY" if os.getenv("PEXELS_API_KEY") else "NO_API_KEY")
    def search(self, query, must=None, soft_must=None, avoid=None):
        key=os.getenv("PEXELS_API_KEY")
        if not key: return []
        out=[]
        s=requests.Session()
        for endpoint,kind,root in [("https://api.pexels.com/v1/videos/search","video","videos"),("https://api.pexels.com/v1/search","image","photos")]:
            r=s.get(endpoint,headers={"Authorization":key},params={"query":query,"orientation":"portrait","size":"medium","locale":"pt-BR","per_page":20},timeout=(5,12))
            if r.status_code==429: raise RuntimeError("RATE_LIMIT")
            r.raise_for_status()
            for item in (r.json().get(root) or []):
                if kind=="video":
                    files=item.get("video_files") or []; urls=[x.get("link") for x in files if x.get("link")]
                    if not urls: continue
                    url=max(urls,key=lambda x:int("portrait" in x))
                    desc=f'{item.get("url","")} {item.get("user",{}).get("name","")}'
                else:
                    src=item.get("src") or {}; url=src.get("portrait") or src.get("large2x") or src.get("large") or src.get("original"); desc=str(item.get("alt") or "")
                if url: out.append({"provider":self.name,"kind":kind,"id":str(item.get("id") or ""),"url":url,"description":desc})
        return out

class PixabayAdapter(ProviderAdapter):
    name="pixabay"
    def status(self): return ProviderStatus(bool(os.getenv("PIXABAY_API_KEY")), "READY" if os.getenv("PIXABAY_API_KEY") else "NO_API_KEY")
    def search(self, query):
        key=os.getenv("PIXABAY_API_KEY")
        if not key: return []
        out=[]
        for endpoint,kind in [("https://pixabay.com/api/videos/","video"),("https://pixabay.com/api/","image")]:
            params={"key":key,"q":query,"per_page":25,"safesearch":"true"}
            if kind=="image": params.update({"image_type":"photo","orientation":"vertical"})
            r=requests.get(endpoint,params=params,timeout=(5,12))
            if r.status_code==429: raise RuntimeError("RATE_LIMIT")
            r.raise_for_status()
            for item in (r.json().get("hits") or []):
                if kind=="video":
                    videos=item.get("videos") or {}; variant=videos.get("medium") or videos.get("small") or videos.get("tiny"); url=variant.get("url") if isinstance(variant,dict) else None; desc=str(item.get("tags") or "")
                else: url=item.get("largeImageURL") or item.get("webformatURL"); desc=str(item.get("tags") or "")
                if url: out.append({"provider":self.name,"kind":kind,"id":str(item.get("id") or ""),"url":url,"description":desc})
        return out

class WikimediaAdapter(ProviderAdapter):
    name="wikimedia"
    def search(self, query):
        r=requests.get("https://commons.wikimedia.org/w/api.php",params={"action":"query","generator":"search","gsrsearch":query,"gsrnamespace":6,"gsrlimit":20,"prop":"imageinfo","iiprop":"url|mime|size","iiurlwidth":1400,"format":"json"},timeout=(5,12))
        if r.status_code==429: raise RuntimeError("RATE_LIMIT")
        r.raise_for_status(); out=[]
        for item in ((r.json().get("query") or {}).get("pages") or {}).values():
            info=(item.get("imageinfo") or [{}])[0]; url=info.get("thumburl") or info.get("url"); mime=str(info.get("mime") or "")
            if url and mime.startswith("image/"): out.append({"provider":self.name,"kind":"image","id":str(item.get("pageid") or ""),"url":url,"description":str(item.get("title") or ""),"license":"Wikimedia Commons"})
        return out

class CoverrAdapter(ProviderAdapter):
    name="coverr"
    def status(self):
        key=os.getenv("COVERR_API_KEY")
        return ProviderStatus(bool(key), "READY" if key else "NO_API_KEY")
    def search(self, query, must=None, soft_must=None, avoid=None):
        key=os.getenv("COVERR_API_KEY")
        if not key: return []
        r=requests.get(
            "https://api.coverr.co/videos/search",
            headers={"Authorization": f"Bearer {key}"},
            params={"query":query,"page":0,"page_size":20,"urls":"true"},
            timeout=(5,12),
        )
        if r.status_code == 429: raise RuntimeError("RATE_LIMIT")
        r.raise_for_status()
        out=[]
        for item in (r.json().get("hits") or []):
            urls=item.get("urls") or {}
            url=(urls.get("mp4_download") or urls.get("mp4") or urls.get("mp4_preview")) if isinstance(urls,dict) else None
            if not url: continue
            tags=item.get("tags") or []
            desc=" ".join([str(item.get("title") or ""),str(item.get("description") or ""), " ".join(map(str,tags))])
            aid=str(item.get("id") or item.get("slug") or "")
            out.append({
                "provider":self.name,"kind":"video","id":aid,"url":url,"description":desc,
                "provenance":{"provider":self.name,"asset_id":aid,"source_url":str(item.get("url") or ""),"license":"Coverr"},
                "license":"Coverr",
            })
        return out

class NASAAdapter(ProviderAdapter):
    name="nasa"
    def status(self): return ProviderStatus(True, "READY")
    def search(self, query):
        key=os.getenv("NASA_API_KEY","DEMO_KEY")
        r=requests.get("https://images-api.nasa.gov/search",params={"q":query,"media_type":"image","page_size":20},timeout=(5,12)); r.raise_for_status(); out=[]
        for item in ((r.json().get("collection") or {}).get("items") or []):
            data=(item.get("data") or [{}])[0]; links=item.get("links") or []
            href=next((x.get("href") for x in links if x.get("href")),"")
            if href: out.append({"provider":self.name,"kind":"image","id":str(data.get("nasa_id") or ""),"url":href,"description":str(data.get("title") or "")})
        return out

class LocalLibraryAdapter(ProviderAdapter):
    name="local"
    def search(self, query):
        try:
            from shortauto_asset_library import search_candidates
            rows=search_candidates(query,must or [],avoid or [],limit=12)
        except Exception: return []
        out=[]
        for row in rows or []:
            path=str(row.get("local_path") or ""); digest=str(row.get("sha256") or "")
            if path: out.append({"provider":"local","kind":"image","id":str(row.get("id") or path),"url":"file://"+path,"description":str(row.get("description") or row.get("title") or query),"local_path":path,"sha256":digest})
        return out

class ProviderRegistry:
    def __init__(self, providers=None):
        self.providers=list(providers or [PexelsAdapter(),PixabayAdapter(),WikimediaAdapter(),CoverrAdapter(),LocalLibraryAdapter()])
    def enabled(self): return [(p,p.status()) for p in self.providers]
