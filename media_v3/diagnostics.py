from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any

ERROR_CLASSES = {
    "INVALID_URL","DOWNLOAD_FAILED","HTTP_ERROR","TIMEOUT","FILE_TOO_SMALL","CORRUPTED_FILE",
    "UNSUPPORTED_FORMAT","NO_VIDEO_STREAM","NO_IMAGE_STREAM","DURATION_INVALID","RESOLUTION_INVALID",
    "MUST_NOT_MATCH","AVOID_MATCH","LOW_RELEVANCE","DUPLICATE","PROVIDER_UNAVAILABLE","NO_API_KEY",
    "RATE_LIMIT","ASSET_QUARANTINED","VALIDATION_FAILED"
}

@dataclass
class SceneDiagnostics:
    scene_id: str
    query: str
    query_variants: list[str] = field(default_factory=list)
    must: list[str] = field(default_factory=list)
    soft_must: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)
    providers_attempted: list[str] = field(default_factory=list)
    provider_results: dict[str, Any] = field(default_factory=dict)
    candidates_found: int = 0
    candidates_downloaded: int = 0
    candidates_valid: int = 0
    rejections: list[dict[str, Any]] = field(default_factory=list)
    fallbacks: list[dict[str, Any]] = field(default_factory=list)
    final_status: str = "PENDING"
    selected_provider: str = ""
    selected_asset_id: str = ""
    error: str = ""
    def reject(self, reason: str, **extra: Any) -> None:
        self.rejections.append({"reason": reason if reason in ERROR_CLASSES else "VALIDATION_FAILED", **extra})
    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
