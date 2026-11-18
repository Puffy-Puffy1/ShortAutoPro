"""Minimal ComfyUI API transport for the isolated POC; no model workflow is bundled."""
from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4

class ComfyUIError(RuntimeError):
    """Bounded, user-actionable ComfyUI request or job failure."""

class ComfyUIClient:
    def __init__(self, base_url: str, *, request_timeout: float = 20.0,
                 job_timeout: float = 900.0, poll_interval: float = 2.0,
                 client_id: str | None = None) -> None:
        base_url = str(base_url or "").strip().rstrip("/")
        if not (base_url.startswith("http://") or base_url.startswith("https://")):
            raise ValueError("ComfyUI base_url must use http:// or https://")
        if min(request_timeout, job_timeout, poll_interval) <= 0:
            raise ValueError("timeouts and poll_interval must be positive")
        self.base_url, self.request_timeout = base_url, request_timeout
        self.job_timeout, self.poll_interval = job_timeout, poll_interval
        self.client_id = client_id or str(uuid4())

    def _request(self, path: str, payload: dict[str, Any] | None = None) -> bytes:
        data = json.dumps(payload).encode("utf-8") if payload is not None else None
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        try:
            with urlopen(Request(self.base_url + path, data=data, headers=headers,
                                 method="POST" if data is not None else "GET"),
                         timeout=self.request_timeout) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise ComfyUIError(f"ComfyUI request failed: {type(exc).__name__}") from exc

    def _json(self, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        try:
            result = json.loads(self._request(path, payload).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ComfyUIError("ComfyUI returned invalid JSON") from exc
        if not isinstance(result, dict):
            raise ComfyUIError("ComfyUI returned an unexpected response")
        return result

    def submit(self, workflow: dict[str, Any]) -> str:
        if not isinstance(workflow, dict) or not workflow:
            raise ValueError("workflow must be a non-empty ComfyUI API workflow object")
        result = self._json("/prompt", {"prompt": workflow, "client_id": self.client_id})
        prompt_id = str(result.get("prompt_id") or "").strip()
        if not prompt_id:
            raise ComfyUIError("ComfyUI did not return a prompt_id")
        return prompt_id

    @staticmethod
    def _video_outputs(item: dict[str, Any]) -> list[dict[str, str]]:
        outputs = item.get("outputs", {})
        found = []
        if not isinstance(outputs, dict):
            return found
        for node in outputs.values():
            if not isinstance(node, dict):
                continue
            for key in ("videos", "gifs", "images"):
                entries = node.get(key, [])
                if not isinstance(entries, list):
                    continue
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    filename = Path(str(entry.get("filename") or "")).name
                    if Path(filename).suffix.lower() in {".mp4", ".webm", ".mov", ".mkv"}:
                        found.append({"filename": filename, "subfolder": str(entry.get("subfolder") or ""),
                                      "type": str(entry.get("type") or "output")})
        return found

    def wait(self, prompt_id: str) -> list[dict[str, str]]:
        deadline = time.monotonic() + self.job_timeout
        while time.monotonic() < deadline:
            history = self._json(f"/history/{prompt_id}")
            item = history.get(prompt_id)
            if isinstance(item, dict):
                status = item.get("status", {})
                status = status if isinstance(status, dict) else {}
                if str(status.get("status_str") or "").lower() in {"error", "failed", "failure"}:
                    raise ComfyUIError(f"ComfyUI job {prompt_id} failed")
                files = self._video_outputs(item)
                if files:
                    return files
                if status.get("completed") is True:
                    raise ComfyUIError(f"ComfyUI job {prompt_id} completed without video output")
            time.sleep(self.poll_interval)
        raise ComfyUIError(f"ComfyUI job {prompt_id} timed out")

    def download(self, output: dict[str, str], destination: Path) -> Path:
        filename = Path(str(output.get("filename") or "")).name
        if not filename or filename in {".", ".."}:
            raise ValueError("output filename is invalid")
        query = urlencode({"filename": filename, "subfolder": str(output.get("subfolder") or ""),
                           "type": str(output.get("type") or "output")})
        data = self._request("/view?" + query)
        if not data:
            raise ComfyUIError("ComfyUI returned an empty video file")
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        target = destination / filename
        temporary = target.with_name("." + target.name + ".part")
        try:
            temporary.write_bytes(data)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)
        return target

    def generate(self, workflow: dict[str, Any], destination: Path) -> list[Path]:
        prompt_id = self.submit(workflow)
        return [self.download(output, destination) for output in self.wait(prompt_id)]
