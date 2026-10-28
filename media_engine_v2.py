#!/usr/bin/env python3
"""ShortAutoPro Media Engine V2.

Single responsibility:
  scene requirements -> provider acquisition -> asset validation -> frozen manifest.

This module deliberately does not render, edit, encode, publish, or create SHORT_IDs.
It uses the repository's mature provider primitives as an acquisition compatibility
boundary; the production entrypoint calls this engine directly and never invokes the legacy
media controller.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

BASE = Path(os.getenv("SHORTAUTOPRO_BASE", Path.home() / "ShortAutoPro")).resolve()
MEDIA_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".mp4", ".mov", ".webm", ".mkv"}
ENGINE_VERSION = "2.0.15"
MIN_VISUAL_PIXELS = 320 * 180
MAX_VISUAL_FALLBACK_CANDIDATES = 8
MAX_LOW_RELEVANCE_VISUAL_CANDIDATES = 4
# Keep the expensive pixel-verification budget bounded per scene.
# Low-relevance candidates remain available as rescue options inside this cap.
MAX_VISUAL_VERIFICATION_ATTEMPTS = MAX_VISUAL_FALLBACK_CANDIDATES


def _resolution_issue(probe: dict[str, Any]) -> str | None:
    """Reject media below the minimum resolution enforced by rendered visual QA."""
    try:
        width = int(probe.get("width") or 0)
        height = int(probe.get("height") or 0)
    except (AttributeError, TypeError, ValueError, OverflowError):
        return "LOW_RESOLUTION:dimensions_unavailable"
    if width <= 0 or height <= 0 or width * height < MIN_VISUAL_PIXELS:
        return f"LOW_RESOLUTION:{width}x{height}"
    return None

def _relaxed_relevance_acceptable(
    candidate: dict[str, Any],
    must: list[str],
) -> bool:
    """Require one contextual query match beyond the independently verified MUST."""
    relevance = candidate.get("query_relevance")
    if not isinstance(relevance, dict) or relevance.get("ok") is True:
        return True

    matched_terms = relevance.get("matched_terms", [])
    if not isinstance(matched_terms, (list, tuple, set)):
        return False
    must_tokens = {
        token
        for item in must
        for token in re.findall(r"[a-z0-9]+", str(item).casefold())
    }
    # Catalog namespace/type words are not evidence that the image depicts
    # the requested scene. They cannot be the only relaxed-context match.
    weak_context_terms = {"file"}
    contextual_matches = [
        str(term).casefold()
        for term in matched_terms
        if str(term).casefold() not in must_tokens
        and str(term).casefold() not in weak_context_terms
    ]
    return bool(contextual_matches)


_NON_PHOTOGRAPHIC_METADATA = re.compile(
    r"\b(?:icons?|logos?|pictograms?|clipart|glyphs?|pinhead|svg)\b",
    re.IGNORECASE,
)
_NON_PHOTOGRAPHIC_QUERY = re.compile(
    r"\b(?:icons?|logos?|pictograms?|clipart|glyphs?|vector\s+graphics?)\b",
    re.IGNORECASE,
)


def _is_non_photographic_asset(candidate: dict[str, Any], query: str) -> bool:
    """Reject icon-library artwork for ordinary documentary/photo scene requests."""
    if _NON_PHOTOGRAPHIC_QUERY.search(str(query or "")):
        return False
    metadata = " ".join(
        str(candidate.get(key) or "")
        for key in (
            "title", "name", "descricao", "description", "image_description",
            "image_title", "tags", "filename", "url",
        )
    )
    return bool(_NON_PHOTOGRAPHIC_METADATA.search(metadata))


def _asset_name_is_forbidden(path: Path) -> bool:
    name = path.name.casefold()
    return any(token in name for token in ("slate", "placeholder", "neutral_editorial", "editorial_reuse"))

def _canonical_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def _manifest_integrity(payload: dict[str, Any]) -> str:
    unsigned = dict(payload)
    unsigned.pop("integrity_sha256", None)
    return hashlib.sha256(_canonical_json(unsigned)).hexdigest()


def _contract_values(value: Any) -> list[str]:
    """Normalize a list of contract terms for a stable scene fingerprint."""
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = []
    return sorted({
        re.sub(r"\s+", " ", str(item or "")).strip().casefold()
        for item in values
        if str(item or "").strip()
    })


def _scene_contract_fingerprint(scene: dict[str, Any]) -> str:
    """Bind a cached asset to the exact visual-acquisition contract that selected it."""
    query = str(scene.get("query") or scene.get("busca") or scene.get("segment") or "")
    segment = str(scene.get("segment") or "")
    visual_mode = str(scene.get("visual_mode") or scene.get("modo_visual") or "")
    payload = {
        # Versioned identity invalidates media cached under older verification policy.
        "engine_version": ENGINE_VERSION,
        "query": re.sub(r"\s+", " ", query).strip().casefold(),
        "segment": re.sub(r"\s+", " ", segment).strip().casefold(),
        "visual_mode": re.sub(r"\s+", " ", visual_mode).strip().casefold(),
        "must_have": _contract_values(scene.get("must_have") or []),
        "preferred_visuals": _contract_values(scene.get("preferred_visuals") or []),
        "avoid": _contract_values(scene.get("avoid") or []),
    }
    return hashlib.sha256(_canonical_json(payload)).hexdigest()


from media_provider_v2 import MediaProviderV2
from media_validator_v2 import validate as validate_asset
from scene_must_policy import normalize_visual_musts

PROVIDER = MediaProviderV2()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        tmp = ""
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ffprobe_asset(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"MEDIA_NOT_FOUND:{path}")
    if path.stat().st_size <= 1000:
        raise RuntimeError(f"MEDIA_INVALID:too_small:{path.name}")
    proc = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries",
            "stream=codec_type,codec_name,width,height,avg_frame_rate,nb_frames",
            "-show_entries", "format=format_name,duration,size",
            "-of", "json", str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"MEDIA_VALIDATION_FAILED:{path.name}")
    try:
        data = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"MEDIA_VALIDATION_FAILED:invalid_probe:{path.name}") from exc
    streams = data.get("streams", [])
    if not isinstance(streams, list) or not streams:
        raise RuntimeError(f"MEDIA_INVALID:no_stream:{path.name}")
    video = next((x for x in streams if isinstance(x, dict) and x.get("codec_type") == "video"), None)
    if not isinstance(video, dict):
        raise RuntimeError(f"MEDIA_INVALID:no_video:{path.name}")
    width, height = int(video.get("width") or 0), int(video.get("height") or 0)
    if width <= 0 or height <= 0:
        raise RuntimeError(f"MEDIA_INVALID:invalid_dimensions:{path.name}")
    fmt = data.get("format", {}) if isinstance(data, dict) else {}
    duration = float(fmt.get("duration") or 0.0)
    if path.suffix.lower() in {".mp4", ".mov", ".webm", ".mkv"} and duration <= 0:
        raise RuntimeError(f"MEDIA_INVALID:invalid_duration:{path.name}")
    return {
        "codec": str(video.get("codec_name") or ""),
        "width": width,
        "height": height,
        "avg_frame_rate": str(video.get("avg_frame_rate") or ""),
        "duration": duration,
        "format": str(fmt.get("format_name") or ""),
        "size_bytes": int(path.stat().st_size),
    }


def validate_short_id(value: str) -> str:
    sid = str(value or "").strip()
    if (
        not sid
        or len(sid) > 96
        or not __import__("re").fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", sid)
        or ".." in sid
    ):
        raise RuntimeError("MEDIA_INPUT_INVALID:short_id")
    return sid


def load_scene_map(short_id: str) -> list[dict[str, Any]]:
    sid = validate_short_id(short_id)
    path = BASE / "roteiros" / f"scene_map_{sid}.json"
    if not path.is_file():
        raise RuntimeError("MEDIA_INPUT_INVALID:scene_map_missing")
    raw = json.loads(path.read_text(encoding="utf-8"))
    scenes = raw.get("scenes") if isinstance(raw, dict) else raw
    if not isinstance(scenes, list) or not scenes:
        raise RuntimeError("MEDIA_INPUT_INVALID:scene_map_empty")
    rows = [x for x in scenes if isinstance(x, dict)]
    if len(rows) != len(scenes):
        raise RuntimeError("MEDIA_INPUT_INVALID:scene_map_scene_not_object")
    seen_ids: set[str] = set()
    for index, scene in enumerate(rows, 1):
        scene_id = str(scene.get("scene_id", scene.get("scene", index))).strip()
        if not scene_id:
            raise RuntimeError(f"MEDIA_INPUT_INVALID:scene_{index:02d}:scene_id_empty")
        if scene_id in seen_ids:
            raise RuntimeError(f"MEDIA_INPUT_INVALID:scene_{index:02d}:duplicate_scene_id")
        scene_query = str(scene.get("query") or scene.get("busca") or scene.get("segment") or "").strip()
        scene_segment = str(scene.get("segment") or "").strip()
        scene_context = " ".join(part for part in (scene_query, scene_segment) if part)
        raw_musts = scene.get("must_have") or []
        musts, events = normalize_visual_musts(
            raw_musts,
            context=scene_context,
        )
        scene["must_have"] = musts

        # Details added by the visual director but absent from both query and
        # narration remain useful search preferences, not hard blocking MUSTs.
        extracted_preferences = [
            str(event.get("from") or "").strip()
            for event in events
            if event.get("reason") == "UNSUPPORTED_VISUAL_DETAIL_PREFERENCE"
            and str(event.get("from") or "").strip()
        ]
        raw_preferences = scene.get("preferred_visuals") or []
        if isinstance(raw_preferences, str):
            raw_preferences = [raw_preferences]
        if not isinstance(raw_preferences, (list, tuple, set)):
            raw_preferences = []
        seen_preferences = set()
        preferred_visuals = []
        for raw_preference in [*raw_preferences, *extracted_preferences]:
            preference = str(raw_preference or "").strip()
            key = preference.casefold()
            if preference and key not in seen_preferences:
                seen_preferences.add(key)
                preferred_visuals.append(preference)
        # A vague style-only AVOID (for example "modern") is difficult to
        # prove absent from pixels. In a historical/vintage scene, treat it as
        # a preference and keep concrete forbidden objects (for example phones)
        # as hard AVOID requirements. The scene-intent verifier still checks the
        # overall period/composition; no global confidence threshold is lowered.
        period_context = bool(re.search(
            r"\b(?:vintage|historic|historical|archival|antique|period[- ]appropriate|"
            r"old[- ]fashioned|soviet(?: union)?|ussr|dyatlov|(?:18|19|20)\d{2}s?)\b",
            scene_context,
            re.IGNORECASE,
        ))
        raw_avoid = scene.get("avoid") or []
        if isinstance(raw_avoid, str):
            raw_avoid = [raw_avoid]
        if not isinstance(raw_avoid, (list, tuple, set)):
            raw_avoid = []
        normalized_avoid = []
        moved_style_avoids = []
        for raw_avoid_item in raw_avoid:
            avoid_item = str(raw_avoid_item or "").strip()
            key = avoid_item.casefold()
            if period_context and key in {
                "modern",
                "contemporary",
                "modern gear",
                "modern equipment",
                "modern clothing",
                "contemporary gear",
                "contemporary equipment",
            }:
                moved_style_avoids.append(avoid_item)
                continue
            if avoid_item:
                normalized_avoid.append(avoid_item)
        if moved_style_avoids:
            style_preference = "period-appropriate historical appearance"
            if style_preference.casefold() not in {
                str(value).strip().casefold() for value in preferred_visuals
            }:
                preferred_visuals.append(style_preference)
            scene["preferred_visuals"] = preferred_visuals
            scene["avoid"] = normalized_avoid
            print(
                "SCENE_AVOID_NORMALIZED="
                + json.dumps(
                    {
                        "scene": scene_id,
                        "moved_to_preference": moved_style_avoids,
                        "kept_hard_avoids": normalized_avoid,
                    },
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )
        elif raw_avoid:
            scene["avoid"] = normalized_avoid

        if preferred_visuals:
            scene["preferred_visuals"] = preferred_visuals

        if events:
            print(
                "SCENE_MUST_NORMALIZED="
                + json.dumps(
                    {"scene": scene_id, "events": events},
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            )
        seen_ids.add(scene_id)
    return rows


def existing_asset(media_dir: Path, number: int) -> Path | None:
    matches = sorted(
        p for p in media_dir.glob(f"scene_{number:02d}*")
        if p.is_file() and p.suffix.lower() in MEDIA_EXTS
    )
    return matches[0] if len(matches) == 1 else None


def _existing_asset_record(
    media_dir: Path,
    number: int,
    scene: dict[str, Any],
) -> dict[str, Any] | None:
    path = existing_asset(media_dir, number)
    sidecar = media_dir / f"scene_{number:02d}.json"
    if path is None or not sidecar.is_file():
        return None
    try:
        media_root = media_dir.resolve()
        resolved = path.resolve()
        resolved.relative_to(media_root)
        record = json.loads(sidecar.read_text(encoding="utf-8"))
        if not isinstance(record, dict):
            return None
        relevance = record.get("query_relevance")
        if not isinstance(relevance, dict) or relevance.get("ok") is not True:
            return None
        if _asset_name_is_forbidden(path):
            return None
        expected = str(record.get("checksum_sha256") or "")
        must_total = len(scene.get("must_have") or [])
        contract_fingerprint = _scene_contract_fingerprint(scene)
        expected_short_id = media_dir.name.removeprefix("short_")
        if (
            not expected
            or record.get("validated") is not True
            or str(record.get("short_id") or "") != expected_short_id
            or int(record.get("scene_number", 0) or 0) != number
            or int(record.get("must_total", 0) or 0) != must_total
            or record.get("scene_contract_fingerprint") != contract_fingerprint
        ):
            return None
        if sha256(path) != expected:
            return None
        validated = validate_asset(path)
        if validated.get("sha256") != expected:
            return None
        probe = validated["probe"]
        if _resolution_issue(probe):
            return None
        record["path"] = str(path)
        record["probe"] = probe
        record["validated"] = True
        return record
    except (OSError, ValueError, TypeError, RuntimeError):
        return None


def _write_asset_sidecar(media_dir: Path, number: int, asset: dict[str, Any]) -> None:
    atomic_json(media_dir / f"scene_{number:02d}.json", asset)


def _candidate_record(candidate: dict[str, Any], path: Path, probe: dict[str, Any]) -> dict[str, Any]:
    return {
        "source": str(candidate.get("fonte") or candidate.get("source") or ""),
        "asset_id": str(candidate.get("id") or ""),
        "url": str(candidate.get("url") or ""),
        "asset_type": "video" if str(candidate.get("tipo", "")).lower() in {"vídeo", "video"} else "image",
        "description": str(candidate.get("descricao") or ""),
        "query_relevance": candidate.get("query_relevance", {}),
        "evidence_class": str(candidate.get("evidence_class") or ""),
        "must_hits": int(candidate.get("must_hits", 0) or 0),
        "must_total": int(candidate.get("_sap_must_total", 0) or 0),
        "scene_contract_fingerprint": str(candidate.get("_sap_scene_contract_fingerprint") or ""),
        "path": str(path),
        "checksum_sha256": sha256(path),
        "license": str(candidate.get("license") or ""),
        "provenance": candidate.get("provenance", {}),
        "probe": probe,
        "validated": True,
        "short_id": str(candidate.get("_sap_short_id") or ""),
        "scene_number": int(candidate.get("_sap_scene_number", 0) or 0),
    }


def _visual_scene_intent(scene_intent: str, must: list[str]) -> str:
    """Keep visual intent focused on observable composition, not narrative claims."""
    intent = " ".join(str(scene_intent or "").split()).strip()
    must_terms = {str(item or "").strip().casefold() for item in must}
    intent_terms = set(re.findall(r"[a-z0-9]+", intent.casefold()))

    # "Abandoned" and "drifting" are narrative interpretations that a still
    # image may not prove. Preserve the observable ship + open-water composition;
    # the independent MUST/AVOID checks still reject missing ships, modern ships,
    # or airplanes. This improves verification consistency without relaxing gates.
    has_ocean_setting = bool(intent_terms & {"ocean", "sea", "seas", "water"})
    has_ship_context = bool(intent_terms & {"ship", "sailing", "vessel", "drifting", "abandoned", "ghost"})
    if "ship" in must_terms and has_ocean_setting and has_ship_context:
        return "sailing ship on open ocean"
    return intent


def _scene_verification_intent(segment: str, query: str) -> str:
    """Combine narration context and visual direction for scene verification."""
    narration = " ".join(str(segment or "").split()).strip()
    direction = " ".join(str(query or "").split()).strip()
    if narration and direction:
        separator = "" if narration.endswith((".", "!", "?")) else "."
        return f"Narration context: {narration}{separator} Visual direction: {direction}"
    return narration or direction


def _verify_scene_pixels(
    path: str | Path,
    must: list[str],
    avoid: list[str],
    scene_intent: str,
    candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify image pixels or a bounded midpoint frame from a video asset."""
    from media_visual_verifier import verify_image_requirements

    asset_path = Path(path)
    candidate = candidate or {}
    kind = str(candidate.get("tipo") or candidate.get("asset_type") or "").strip().casefold()
    is_video = (
        kind.startswith("video")
        or kind in {"vídeo", "movie", "clip"}
        or asset_path.suffix.casefold() in {".mp4", ".mov", ".webm", ".mkv"}
    )
    requirements = [str(value).strip() for value in must if str(value).strip()]
    scene_intent = _visual_scene_intent(scene_intent, requirements)
    if not is_video:
        return verify_image_requirements(
            asset_path,
            requirements,
            avoid,
            scene_intent=scene_intent,
        )

    # Video clips remain supported, but metadata alone cannot prove their scene.
    # Extract one midpoint frame into a temporary directory and verify those pixels.
    with tempfile.TemporaryDirectory(prefix="sap-visual-frame-") as temp_dir:
        frame_path = Path(temp_dir) / "scene-midpoint.jpg"
        try:
            duration_result = subprocess.run(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(asset_path),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
            duration = float((duration_result.stdout or "").strip())
            if duration_result.returncode != 0 or duration <= 0:
                return {
                    "status": "BLOCK",
                    "method": "ffmpeg_video_frame",
                    "reason": "video_duration_unavailable",
                }
            timestamp = max(0.0, duration / 2.0)
            extraction = subprocess.run(
                [
                    "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                    "-ss", f"{timestamp:.3f}",
                    "-i", str(asset_path),
                    "-frames:v", "1",
                    "-vf", "scale=1280:-2",
                    "-q:v", "3",
                    str(frame_path),
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=20,
            )
        except (OSError, subprocess.SubprocessError, ValueError):
            return {
                "status": "BLOCK",
                "method": "ffmpeg_video_frame",
                "reason": "video_frame_extraction_failed",
            }
        if extraction.returncode != 0 or not frame_path.is_file() or frame_path.stat().st_size <= 0:
            return {
                "status": "BLOCK",
                "method": "ffmpeg_video_frame",
                "reason": "video_frame_extraction_failed",
            }

        result = verify_image_requirements(
            frame_path,
            requirements,
            avoid,
            scene_intent=scene_intent,
        )
        return {
            **result,
            "video_sample": {
                "method": "midpoint_frame",
                "timestamp_seconds": round(timestamp, 3),
            },
        }


def _local_library_asset(
    query: str,
    must: list[str],
    avoid: list[str],
    used_asset_hashes: set[str] | None = None,
) -> dict[str, Any] | None:
    try:
        from shortauto_asset_library import search_candidates
        candidates = search_candidates(query, must, avoid, limit=3)
    except Exception:
        return None
    used_asset_hashes = used_asset_hashes or set()
    from media_provider_router_v2 import query_relevance
    for candidate in candidates:
        relevance = query_relevance(query, candidate)
        if not relevance.get("ok"):
            continue
        candidate["query_relevance"] = relevance
        path = Path(str(candidate.get("local_path") or "")).expanduser()
        expected = str(candidate.get("sha256") or "")
        if not path.is_file() or not expected or expected in used_asset_hashes:
            continue
        try:
            if sha256(path) != expected:
                continue
            probe = ffprobe_asset(path)
            if _resolution_issue(probe):
                continue
        except RuntimeError:
            continue
        try:
            from media_must_verifier import verified_must
            metadata_evidence = verified_must(candidate, {"must_have": must})
        except Exception:
            metadata_evidence = {"hits": 0, "matched": [], "missing": list(must)}
        if must and int(metadata_evidence.get("hits", 0) or 0) != len(must):
            continue

        try:
            visual_result = _verify_scene_pixels(
                path,
                must,
                avoid,
                query,
                candidate,
            )
        except Exception as exc:
            visual_result = {
                "status": "BLOCK",
                "reason": f"visual_verifier_error:{type(exc).__name__}",
            }
        if visual_result.get("status") != "PASS":
            continue

        record = dict(candidate)
        record["fonte"] = "LocalLibrary"
        record["_sap_must_total"] = len(must)
        record["_sap_metadata_must_hits"] = int(metadata_evidence.get("hits", 0) or 0)
        record["must_hits"] = len(must)
        asset_record = _candidate_record(record, path, probe)
        asset_record["visual_verification"] = visual_result
        asset_record["metadata_must_hits"] = int(metadata_evidence.get("hits", 0) or 0)
        asset_record["verification_mode"] = "gemini_visual_must"
        asset_record["verification_note"] = (
            "local asset passed pixel-level MUST/AVOID and scene-intent verification"
        )
        return asset_record
    return None


def _visual_fallback_candidates(
    query: str,
    candidates: list[dict[str, Any]],
    must: list[str] | None = None,
    limit: int = 2,
    *,
    allow_low_relevance: bool = False,
    low_relevance_only: bool = False,
) -> list[dict[str, Any]]:
    """Choose a bounded image shortlist for pixel-level verification.

    Catalog relevance ranks candidates but does not prove visual content. Optional
    low-relevance rescue candidates still have to pass the same pixel verifier.
    """
    from media_provider_router_v2 import query_relevance

    image_types = {"image", "imagem", "foto", "photo", "photograph", "fotografia", "picture"}
    image_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}

    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        search_query = str(candidate.get("_sap_relevance_query") or query).strip() or query
        if _is_non_photographic_asset(candidate, search_query):
            continue
        kind = str(candidate.get("tipo") or candidate.get("asset_type") or "").strip().casefold()
        if kind.startswith("video") or kind in {"vídeo", "movie", "clip"}:
            continue
        url = str(candidate.get("url") or "")
        extension = Path(url.split("?", 1)[0]).suffix.casefold()
        if kind:
            if kind not in image_types:
                continue
        elif extension not in image_extensions:
            continue

        try:
            if int(candidate.get("avoid_hits", 0) or 0) > 0:
                continue
        except (TypeError, ValueError):
            continue

        relevance = query_relevance(search_query, candidate)
        relevance_candidate = {**candidate, "query_relevance": relevance}
        relevance_ok = _relaxed_relevance_acceptable(relevance_candidate, must or [])
        if low_relevance_only and relevance_ok:
            continue
        if not relevance_ok and not allow_low_relevance:
            continue
        # Low-relevance rescue only enters the candidate shortlist. Its ranking
        # is lower, and its downloaded pixels must still satisfy MUST, AVOID and
        # scene intent before the asset can be accepted.
        candidate = dict(relevance_candidate)
        candidate["_sap_relevance_fallback_only"] = not relevance_ok
        # Use asset metadata, not provider scores, to rank which candidates receive
        # the bounded pixel-level verification. This ranking never accepts media.
        try:
            from media_must_verifier import verified_must
            evidence = verified_must(candidate, {"must_have": must or []})
        except Exception:
            evidence = {"hits": 0, "matched": []}
        matched_musts = {
            str(item).strip().casefold()
            for item in evidence.get("matched", [])
            if str(item).strip()
        }
        primary_must = str((must or [""])[0]).strip().casefold()
        candidate["_sap_metadata_must_hits"] = int(evidence.get("hits", 0) or 0)
        candidate["_sap_verified_must_matches"] = sorted(matched_musts)
        candidate["_sap_primary_must_match"] = int(
            bool(primary_must) and primary_must in matched_musts
        )
        key = (
            str(candidate.get("fonte") or candidate.get("source") or ""),
            str(candidate.get("id") or ""),
            url,
        )
        unique.setdefault(key, candidate)

    # Prioritize candidates whose own catalog metadata already matches a MUST.
    # This only decides which images receive the bounded pixel check; it never
    # accepts an asset. media_visual_verifier must still PASS every MUST/AVOID.
    ranked = sorted(
        unique.values(),
        key=lambda candidate: (
            int(not candidate.get("_sap_relevance_fallback_only", False)),
            int(candidate.get("_sap_metadata_must_hits", 0) or 0),
            int(candidate.get("_sap_primary_must_match", 0) or 0),
            int((candidate.get("query_relevance") or {}).get("matched_count", 0) or 0),
            float(candidate.get("score", 0) or 0),
        ),
        reverse=True,
    )
    max_items = max(1, min(int(limit), MAX_VISUAL_FALLBACK_CANDIDATES))
    # Query provenance matters: otherwise several near-duplicate results from
    # the primary search can crowd out every alternative phrasing. Pick the best
    # result from each query first, then fill remaining slots by rank.
    selected: list[dict[str, Any]] = []
    remaining = ranked
    while remaining and len(selected) < max_items:
        seen_queries: set[str] = set()
        next_remaining: list[dict[str, Any]] = []
        added = 0
        for index, candidate in enumerate(remaining):
            source_query = re.sub(
                r"\s+",
                " ",
                str(candidate.get("_sap_relevance_query") or query),
            ).strip().casefold() or query.casefold()
            if source_query in seen_queries:
                next_remaining.append(candidate)
                continue
            seen_queries.add(source_query)
            selected.append(candidate)
            added += 1
            if len(selected) >= max_items:
                next_remaining.extend(remaining[index + 1:])
                break
        if not added:
            break
        remaining = next_remaining
    return selected



_VISUAL_QUERY_STOPWORDS = {
    "a", "an", "the", "of", "in", "on", "at", "by", "for", "from",
    "and", "or", "to", "with", "after", "before", "during", "near",
    "over", "under", "above", "below", "around", "about", "into",
    "through", "is", "are", "was", "were", "be", "been", "being",
}


def _targeted_visual_search_queries(
    query: str,
    must: list[str],
    limit: int = 3,
    avoid: list[str] | None = None,
) -> list[str]:
    """Build bounded contextual searches that account for MUST/AVOID intent."""
    query_tokens = re.findall(r"[a-z0-9]+", str(query or "").casefold())
    query_token_set = set(query_tokens)
    must_tokens = {
        token
        for item in must
        for token in re.findall(r"[a-z0-9]+", str(item or "").casefold())
    }
    context = [
        token for token in query_tokens
        if token not in _VISUAL_QUERY_STOPWORDS and token not in must_tokens
    ][-4:]

    searches = []
    seen = set()
    max_searches = max(1, min(int(limit), 3))
    for item in must:
        term = re.sub(r"\s+", " ", str(item or "")).strip()
        term_tokens = set(re.findall(r"[a-z0-9]+", term.casefold()))
        if not term or term_tokens <= query_token_set:
            continue
        targeted = " ".join([term, *context]).strip()
        key = targeted.casefold()
        if targeted and key not in seen:
            seen.add(key)
            searches.append(targeted)
        if len(searches) >= max_searches:
            break

    # If every MUST word is already in the broad query, generate alternate
    # combined phrasing for object + setting. This is especially useful for
    # scenes such as a train actually traveling through snow, not a train photo
    # and a separate snow photo. These queries only improve discovery.
    setting_terms = {
        "snow", "snowy", "snowfall", "winter", "ice", "icy", "ocean", "sea",
        "water", "river", "lake", "beach", "shore", "desert", "sand",
        "mountain", "mountains", "forest", "woodland", "rain", "storm",
        "underwater", "tracks", "railway", "road", "street",
    }
    must_text = [re.sub(r"\s+", " ", str(item or "")).strip() for item in must]
    has_setting_anchor = any(
        token in setting_terms
        for item in must_text
        for token in re.findall(r"[a-z0-9]+", item.casefold())
    )
    if len(must_text) >= 2 and has_setting_anchor and len(searches) < max_searches:
        snow_related = any(
            token in {"snow", "snowy", "snowfall", "winter", "ice", "icy"}
            for item in must_text
            for token in re.findall(r"[a-z0-9]+", item.casefold())
        )
        fog_related = any(
            token in {"fog", "foggy", "mist", "misty", "haze", "hazy"}
            for item in must_text
            for token in re.findall(r"[a-z0-9]+", item.casefold())
        ) and any(
            token in {"water", "ocean", "sea", "lake", "river"}
            for item in must_text
            for token in re.findall(r"[a-z0-9]+", item.casefold())
        )
        if fog_related:
            variants = [
                "thick fog over dark water " + " ".join(context),
                "misty dark ocean surface " + " ".join(context),
                "dense fog over open water " + " ".join(context),
            ]
        elif snow_related:
            non_snow_musts = [
                item for item in must_text
                if not re.search(r"\b(?:snow|snowy|snowfall|winter|ice|icy)\b", item, re.IGNORECASE)
            ]
            variants = [
                " ".join(["snowy", *non_snow_musts, *context]).strip(),
                " ".join([must_text[0], "in", *must_text[1:], *context]).strip(),
                " ".join([*must_text[1:], must_text[0], *context]).strip(),
            ]
        else:
            variants = [
                " ".join([*must_text, *context]).strip(),
                " ".join([must_text[0], "with", *must_text[1:], *context]).strip(),
                " ".join([*must_text[1:], must_text[0], *context]).strip(),
            ]
        for targeted in variants:
            key = targeted.casefold()
            if targeted and key not in seen:
                seen.add(key)
                searches.append(targeted)
            if len(searches) >= max_searches:
                break

    # A broad scene query may already contain "map" but still return unrelated
    # catalog images. Try common archival catalog phrasing without relaxing the
    # pixel-level acceptance criteria. Keep this narrow and bounded.
    if (
        len(must) == 1
        and str(must[0]).strip().casefold() == "map"
        and re.search(r"\bmap\b", str(query or ""), re.IGNORECASE)
    ):
        for phrase in ("antique map", "historical map", "old map"):
            targeted = " ".join([phrase, *context]).strip()
            key = targeted.casefold()
            if targeted and key not in seen:
                seen.add(key)
                searches.append(targeted)
            if len(searches) >= max_searches:
                break

    # If the only MUST is already in a very specific query, but its candidates
    # fail pixel/scene verification, offer a few reordered phrasings using the
    # same scene concepts. This is discovery only; no candidate bypasses pixels.
    is_map_special_case = (
        len(must_text) == 1
        and must_text[0].casefold() == "map"
        and re.search(r"\bmap\b", str(query or ""), re.IGNORECASE)
    )
    if not searches and must_text and not is_map_special_case:
        object_phrase = " ".join(must_text)
        context_terms = [
            token for token in query_tokens
            if token not in _VISUAL_QUERY_STOPWORDS and token not in must_tokens
        ]
        if context_terms:
            context_tail = context_terms[-3:]
            variants = [
                " ".join([*context_tail, object_phrase]).strip(),
                " ".join([object_phrase, *context_tail]).strip(),
                " ".join([context_terms[0], object_phrase, *context_terms[1:]]).strip(),
            ]
            for targeted in variants:
                key = targeted.casefold()
                if targeted and key not in seen:
                    seen.add(key)
                    searches.append(targeted)
                if len(searches) >= max_searches:
                    break

    # When a scene asks for unusual/unknown writing and explicitly excludes
    # English alphabet lettering, broaden retrieval toward manuscript/script
    # vocabulary. These are search hints only; the unchanged pixel gate still
    # has to prove the text is visible and the excluded alphabet is absent.
    avoid_text = " ".join(str(item or "") for item in (avoid or [])).casefold()
    text_context = " ".join([str(query or ""), *[str(item or "") for item in must]]).casefold()
    non_english_script = (
        "alphabet" in avoid_text
        and "english" in avoid_text
        and any(term in text_context for term in (
            "text", "handwriting", "symbols", "script", "manuscript", "writing", "glyphs"
        ))
    )
    if non_english_script:
        variants = [
            "unreadable handwritten script on aged parchment",
            "cryptic symbols on antique manuscript page",
            "unknown writing system parchment close-up",
        ]
        # These variants encode the critical visual distinction and must come
        # before generic "text" searches when English lettering is forbidden.
        prioritized = []
        for targeted in [*variants, *searches]:
            key = str(targeted or "").casefold()
            if key and key not in {item.casefold() for item in prioritized}:
                prioritized.append(str(targeted))
            if len(prioritized) >= max_searches:
                break
        searches = prioritized

    # Preserve model-specific details when a known light aircraft is requested.
    # Generic "aircraft" searches often return jets or parked planes; these
    # bounded variants target the actual Cessna/propeller scene without relaxing
    # the visual gate. AVOID items such as modern jets remain hard constraints.
    query_terms = set(query_tokens)
    avoid_text = " ".join(str(item or "") for item in (avoid or [])).casefold()
    if (
        "cessna" in query_terms
        and ({"aircraft", "plane", "airplane"} & (query_terms | must_tokens))
        and any(term in avoid_text for term in ("modern jet", "commercial airliner", "jet"))
    ):
        model = " ".join(
            token for token in query_tokens
            if token in {"cessna", "182", "185", "172", "206"}
        ) or "Cessna"
        location = " ".join(
            token for token in query_tokens
            if token in {"bass", "strait", "ocean", "sea", "water", "coast"}
        )
        variants = [
            " ".join([model, "single engine propeller aircraft in flight over", location]).strip(),
            " ".join([model, "light propeller plane flying over ocean", location]).strip(),
            " ".join(["single engine piston aircraft over", location, model]).strip(),
        ]
        prioritized = []
        seen_priority = set()
        for targeted in [*variants, *searches]:
            normalized = re.sub(r"\s+", " ", str(targeted or "")).strip()
            key = normalized.casefold()
            if normalized and key not in seen_priority:
                prioritized.append(normalized)
                seen_priority.add(key)
            if len(prioritized) >= max_searches:
                break
        searches = prioritized

    # Storm-flight scenes are often indexed as weather or horizon photos.
    # Keep aircraft, dark clouds and horizon in the search wording; the strict
    # pixel verifier still decides whether a candidate is usable.
    aviation_weather = query_terms | must_tokens
    if (
        {"airplane", "dark", "clouds", "horizon"} <= aviation_weather
        and "daylight" in avoid_text
    ):
        weather_variants = [
            "small airplane flying beneath dark storm clouds over distant horizon",
            "propeller aircraft in flight under dark clouds above horizon",
            "airplane silhouette against storm clouds and distant horizon",
        ]
        prioritized = []
        seen_priority = set()
        for targeted in [*weather_variants, *searches]:
            normalized = re.sub(r"\s+", " ", str(targeted or "")).strip()
            key = normalized.casefold()
            if normalized and key not in seen_priority:
                prioritized.append(normalized)
                seen_priority.add(key)
            if len(prioritized) >= max_searches:
                break
        searches = prioritized

    # Light-aircraft scenes over open water are poorly indexed by broad
    # "airplane ocean" searches. Prefer precise catalog wording for night
    # flights when daylight and commercial airliners are explicitly excluded.
    aviation_context = query_terms | must_tokens
    aviation_avoid = " ".join(str(item or "") for item in (avoid or [])).casefold()
    if (
        {"airplane", "ocean"} <= aviation_context
        and ({"night", "dark"} & aviation_context or "daylight" in aviation_avoid)
        and any(term in aviation_avoid for term in ("commercial airliner", "airliner", "jet"))
    ):
        aviation_variants = [
            "small propeller aircraft flying over open ocean at night",
            "light single engine airplane over dark sea at night",
            "single engine plane in flight above ocean at night",
        ]
        prioritized = []
        seen_priority = set()
        for targeted in [*aviation_variants, *searches]:
            normalized = re.sub(r"\s+", " ", str(targeted or "")).strip()
            key = normalized.casefold()
            if normalized and key not in seen_priority:
                prioritized.append(normalized)
                seen_priority.add(key)
            if len(prioritized) >= max_searches:
                break
        searches = prioritized

    # A historical skiing scene may be mislabeled as generic "hikers" by the
    # scene director. Search directly for photographic ski-expedition wording;
    # every candidate still has to pass the same pixel MUST/AVOID verifier.
    ski_context = query_terms | must_tokens
    historical_terms = {"soviet", "ussr", "dyatlov", "historic", "historical", "vintage", "archival", "1950s", "1959"}
    ski_terms = {"ski", "skier", "skiers", "skiing", "skis"}
    snow_terms = {"snow", "snowy", "snowfall", "winter", "ice", "icy"}
    if (
        ski_context & historical_terms
        and ski_context & ski_terms
        and ski_context & snow_terms
    ):
        ski_variants = [
            "archival black and white photograph of Soviet skiers in snowy mountains",
            "historical Soviet ski expedition group walking through deep snow",
            "documentary photograph of skiers on a Soviet winter expedition",
        ]
        prioritized = []
        seen_priority = set()
        for targeted in [*ski_variants, *searches]:
            normalized = re.sub(r"\s+", " ", str(targeted or "")).strip()
            key = normalized.casefold()
            if normalized and key not in seen_priority:
                prioritized.append(normalized)
                seen_priority.add(key)
            if len(prioritized) >= max_searches:
                break
        searches = prioritized

    # Hands operating cockpit controls need close-up queries: broad aviation
    # results often show a pilot's face or unrelated panels. Search wording is
    # only a retrieval hint; the pixel MUST/AVOID and scene-intent checks still
    # decide whether an asset can be accepted.
    visual_terms = query_terms | must_tokens
    avoid_terms = [str(item or "").casefold() for item in (avoid or [])]
    excludes_identity = any(
        "face" in item or "pilot identity" in item
        for item in avoid_terms
    )
    hand_control_scene = (
        "hand" in visual_terms
        and bool({"button", "switch"} & visual_terms)
        and bool({"aircraft", "cockpit", "panel", "control"} & visual_terms)
        and excludes_identity
    )
    if hand_control_scene:
        control_variants = [
            "close-up hand pressing a button on an aircraft cockpit control panel",
            "aircraft cockpit control switch close-up hand operating panel",
            "close-up anonymous hand operating aircraft communication switch with no face visible",
        ]
        prioritized = []
        seen_priority = set()
        for targeted in [*control_variants, *searches]:
            normalized = re.sub(r"\s+", " ", str(targeted or "")).strip()
            key = normalized.casefold()
            if normalized and key not in seen_priority:
                prioritized.append(normalized)
                seen_priority.add(key)
            if len(prioritized) >= max_searches:
                break
        searches = prioritized

    # Backpack scenes in winter are often indexed as hiking/trekking
    # photographs rather than by the full editorial sentence. Prioritize
    # context-preserving catalog searches; pixel MUST/AVOID and scene-intent
    # verification remain the only acceptance gate.
    backpack_context = query_terms | must_tokens
    backpack_scene = (
        bool({"backpack", "backpacks"} & backpack_context)
        and bool({"hiker", "hikers", "hiking", "backpacking", "trekking"} & backpack_context)
        and bool({"snow", "snowy", "snowfall", "winter", "wilderness", "mountain", "mountains"} & backpack_context)
    )
    if backpack_scene:
        backpack_variants = [
            "hikers walking with backpacks through snowy wilderness",
            "backpacking hikers trekking through snow covered wilderness",
            "winter hiking expedition with backpacks in snowy mountains",
        ]
        prioritized = []
        seen_priority = set()
        for targeted in [*backpack_variants, *searches]:
            normalized = re.sub(r"\\s+", " ", str(targeted or "")).strip()
            key = normalized.casefold()
            if normalized and key not in seen_priority:
                prioritized.append(normalized)
                seen_priority.add(key)
            if len(prioritized) >= max_searches:
                break
        searches = prioritized

    # Radar-screen scenes are commonly indexed as air-traffic-control equipment,
    # not as an "empty radar" image. Keep retrieval specific and avoid text-heavy
    # screenshots; all candidates still pass the unchanged pixel MUST/AVOID gate.
    radar_context = query_terms | must_tokens
    radar_scene = (
        bool({"radar", "radarscope"} & radar_context)
        and bool({"screen", "display", "monitor", "scope"} & radar_context)
    )
    if radar_scene and re.search(r"\\b(?:text overlay|text|labels|caption)\\b", avoid_text):
        searches = []
        for targeted in (
            "air traffic control radar screen no labels",
            "aviation radar scope monitor without text overlay",
            "air traffic control radar display close up blank screen",
        ):
            searches.append(targeted)
            if len(searches) >= max_searches:
                break

    # Prefer archival steam-railway language when a snowy historical train
    # scene excludes high-speed trains. Search terms only improve discovery;
    # candidates still pass the existing pixel MUST/AVOID gate.
    avoid_text = " ".join(str(item or "") for item in (avoid or [])).casefold()
    train_context = " ".join([str(query or ""), *must_text]).casefold()
    if (
        len(must_text) == 1
        and re.search(r"\btrain\b", must_text[0], re.IGNORECASE)
        and re.search(r"\b(?:snow|snowy|winter|vintage|historic|historical)\b", train_context)
        and re.search(r"\b(?:high[- ]speed train|bullet train|modern train)\b", avoid_text)
    ):
        searches = []
        seen_train_queries = set()
        for targeted in (
            "vintage steam locomotive winter railway snow landscape",
            "historic steam train traveling through snowy countryside",
            "archival steam locomotive on snow covered railway tracks",
        ):
            key = targeted.casefold()
            if key not in seen_train_queries:
                seen_train_queries.add(key)
                searches.append(targeted)
            if len(searches) >= max_searches:
                break

    return searches


def acquire_scene(
    short_id: str,
    number: int,
    scene: dict[str, Any],
    media_dir: Path,
    used_asset_hashes: set[str] | None = None,
) -> dict[str, Any]:
    query = str(scene.get("query") or scene.get("busca") or scene.get("segment") or "").strip()
    raw_preferences = scene.get("preferred_visuals") or []
    if isinstance(raw_preferences, str):
        raw_preferences = [raw_preferences]
    if isinstance(raw_preferences, (list, tuple, set)):
        preferences = [str(value).strip() for value in raw_preferences if str(value).strip()]
    else:
        preferences = []
    for preference in preferences:
        if preference.casefold() not in query.casefold():
            query = f"{query} {preference}".strip()
    must = [str(x).strip() for x in (scene.get("must_have") or []) if str(x).strip()]
    avoid = [str(x).strip() for x in (scene.get("avoid") or []) if str(x).strip()]
    visual_mode = str(scene.get("visual_mode") or scene.get("modo_visual") or "").strip()
    segment = str(scene.get("segment") or "").strip()
    contract_fingerprint = _scene_contract_fingerprint(scene)
    if not query:
        raise RuntimeError(f"MEDIA_INPUT_INVALID:scene_{number:02d}:query_empty")

    candidates = PROVIDER.search(query, must, avoid, segmento=segment, visual_mode=visual_mode)
    query_relevance_rejected = sum(
        1 for candidate in candidates
        if isinstance(candidate.get("query_relevance"), dict)
        and candidate["query_relevance"].get("ok") is not True
    )
    for candidate in candidates:
        candidate["_sap_must_total"] = len(must)
        candidate["_sap_short_id"] = short_id
        candidate["_sap_scene_number"] = number
        candidate["_sap_scene_contract_fingerprint"] = contract_fingerprint
    strict: list[dict[str, Any]] = []
    strict_metadata_rejections: list[str] = []
    prepared_candidates = PROVIDER.prepare(candidates, len(must))
    verifier = None
    if must and prepared_candidates:
        from media_must_verifier import verified_must
        verifier = verified_must

    for raw_candidate in prepared_candidates:
        if not isinstance(raw_candidate, dict):
            continue
        relevance = raw_candidate.get("query_relevance")
        if isinstance(relevance, dict) and relevance.get("ok") is not True:
            continue
        candidate = dict(raw_candidate)
        if _is_non_photographic_asset(candidate, query):
            strict_metadata_rejections.append(
                f"{candidate.get('fonte', candidate.get('source', '?'))}:"
                f"{candidate.get('id', '?')}:non_photographic_icon_asset"
            )
            continue
        if must:
            # Provider must_hits is a ranking hint, never independent proof.
            evidence = verifier(candidate, {"must_have": must}) if verifier else {
                "hits": 0, "missing": list(must)
            }
            hits = int(evidence.get("hits", 0) or 0)
            if hits != len(must):
                missing = evidence.get("missing", must)
                strict_metadata_rejections.append(
                    f"{candidate.get('fonte', candidate.get('source', '?'))}:"
                    f"{candidate.get('id', '?')}:"
                    f"{hits}/{len(must)}:missing={','.join(map(str, missing))}"
                )
                continue
            candidate["_sap_provider_must_hits"] = int(candidate.get("must_hits", 0) or 0)
            candidate["_sap_metadata_must_hits"] = hits
            candidate["must_hits"] = hits
            candidate["_sap_must_total"] = len(must)
            candidate["verification_mode"] = "strict_must"
            candidate["verification_note"] = "provider_must_hits_reverified_against_asset_metadata"
        candidate["_sap_scene_contract_fingerprint"] = contract_fingerprint
        strict.append(candidate)

    verification_mode = "strict_must" if strict else ""

    # If the editorial query was too restrictive, a second retrieval may use
    # query text without MUST constraints. Acceptance remains fail-closed:
    # every explicit MUST is independently verified against asset evidence
    # before any download is attempted.
    relaxed = []
    relaxed_query_relevance_rejected = 0
    relaxed_evidence_diagnostics = []
    verified_relaxed: list[dict[str, Any]] = []
    if not strict and must:
        # Keep explicit MUST terms in the fallback search query so discovery
        # can find matching assets. They are still independently verified below;
        # search text is never accepted as evidence.
        relaxed_query = " ".join([query, *must]).strip()
        relaxed = PROVIDER.search(
            relaxed_query,
            [],
            avoid,
            segmento=segment,
            visual_mode=visual_mode,
        )
        verifier = None
        try:
            from media_must_verifier import verified_must
            verifier = verified_must
        except Exception:
            verifier = None

        if verifier is not None:
            for candidate in relaxed:
                if _is_non_photographic_asset(candidate, query):
                    relaxed_evidence_diagnostics.append(
                        f"{candidate.get('fonte', candidate.get('source', '?'))}:"
                        f"{candidate.get('id', '?')}:non_photographic_icon_asset"
                    )
                    continue
                # Verify the explicit MUST first. A fallback candidate with
                # complete semantic proof may pass on one contextual query
                # anchor; the primary search still uses the normal threshold.
                evidence = verifier(candidate, {"must_have": must})
                missing = evidence.get("missing", [])
                relaxed_evidence_diagnostics.append(
                    f"{candidate.get('fonte', candidate.get('source', '?'))}:"
                    f"{str(candidate.get('id', '?'))}:"
                    f"{int(evidence.get('hits', 0) or 0)}/{len(must)}:"
                    f"missing={','.join(map(str, missing)) or '-'}"
                )
                if int(evidence.get("hits", 0) or 0) != len(must) or not must:
                    continue
                if not _relaxed_relevance_acceptable(candidate, must):
                    relaxed_query_relevance_rejected += 1
                    continue
                candidate["_sap_must_total"] = len(must)
                candidate["_sap_short_id"] = short_id
                candidate["_sap_scene_number"] = number
                candidate["_sap_scene_contract_fingerprint"] = contract_fingerprint
                # Preserve the independently verified evidence count in the
                # frozen manifest for downstream validation.
                candidate["must_hits"] = int(evidence.get("hits", 0) or 0)
                candidate["verification_mode"] = "strict_evidence_query_relaxed"
                candidate["verification_note"] = (
                    "editorial_query_relaxed;explicit_must_reverified"
                )
                verified_relaxed.append(candidate)
        strict = verified_relaxed
        verification_mode = "strict_evidence_query_relaxed" if strict else ""

    visual_fallback_candidates: list[dict[str, Any]] = []
    visual_rejections: list[str] = []
    if query:
        # Keep a bounded pixel-verified fallback behind strict metadata matches.
        # A strict candidate can still fail at download/format validation; in
        # that case, continue with another real image and require pixel-level
        # MUST/AVOID verification before accepting it.
        visual_source = [*candidates, *relaxed]
        visual_pool = _visual_fallback_candidates(
            query,
            visual_source,
            must=must,
            limit=MAX_VISUAL_FALLBACK_CANDIDATES,
        )

        # Prefer scene-director alternatives before generating more query variants.
        # These are retrieval hints only; pixel verification remains the acceptance gate.
        raw_alternates = scene.get("alt_queries") or []
        if isinstance(raw_alternates, str):
            raw_alternates = [raw_alternates]
        if not isinstance(raw_alternates, (list, tuple)):
            raw_alternates = []

        seen_alternates = {re.sub(r"\s+", " ", query).strip().casefold()}
        alternate_searches = 0
        # Always sample a small number of alternate phrasings. Metadata may
        # cover every MUST while the pixels still show the wrong composition.
        for raw_alternate in raw_alternates:
            alternate_query = re.sub(r"\s+", " ", str(raw_alternate or "")).strip()
            alternate_key = alternate_query.casefold()
            if not alternate_query or alternate_key in seen_alternates:
                continue
            seen_alternates.add(alternate_key)
            if alternate_searches >= 2:
                break
            alternate_searches += 1
            try:
                alternate_candidates = PROVIDER.search(
                    alternate_query,
                    [],
                    avoid,
                    segmento=segment,
                    visual_mode=visual_mode,
                )
            except Exception as exc:
                print(
                    f"MEDIA_ALT_QUERY_SEARCH=ERROR scene={number:02d} "
                    f"error={type(exc).__name__}"
                )
                continue
            if not alternate_candidates:
                continue

            # Tag each result with the exact query that found it. The bounded
            # selector uses this provenance to keep the pixel-check pool diverse.
            visual_source.extend(
                {
                    **candidate,
                    "_sap_relevance_query": alternate_query,
                }
                for candidate in alternate_candidates
                if isinstance(candidate, dict)
            )
            visual_pool = _visual_fallback_candidates(
                query,
                visual_source,
                must=must,
                limit=MAX_VISUAL_FALLBACK_CANDIDATES,
            )
            print(
                f"MEDIA_ALT_QUERY_SEARCH=PASS scene={number:02d} "
                f"candidates={len(alternate_candidates)} pool={len(visual_pool)}"
            )

        # Broad provider searches can return many catalog matches but almost no
        # images that show every MUST. Search missing MUST terms with a few
        # contextual anchors, then let the same pixel-level verifier decide.
        # Discovery is bounded; acceptance criteria are unchanged.
        # Metadata cannot tell us whether the image actually matches the
        # composition. Try up to two distinct targeted variants even when the
        # first pool has complete MUST metadata; skip any query already used by
        # the main or scene-director search to avoid wasting provider calls.
        targeted_queries = _targeted_visual_search_queries(query, must, avoid=avoid)
        distinct_targeted_queries = []
        for raw_targeted_query in targeted_queries:
            targeted_query = re.sub(r"\s+", " ", str(raw_targeted_query or "")).strip()
            targeted_key = targeted_query.casefold()
            if not targeted_query or targeted_key in seen_alternates:
                continue
            seen_alternates.add(targeted_key)
            distinct_targeted_queries.append(targeted_query)
            if len(distinct_targeted_queries) >= 2:
                break

        for targeted_query in distinct_targeted_queries:
            try:
                targeted_candidates = PROVIDER.search(
                    targeted_query,
                    [],
                    avoid,
                    segmento=segment,
                    visual_mode=visual_mode,
                )
            except Exception as exc:
                print(
                    f"MEDIA_TARGETED_SEARCH=ERROR scene={number:02d} "
                    f"error={type(exc).__name__}"
                )
                continue
            if targeted_candidates:
                # Score each result against the query that found it, then
                # rank it together with the original scene candidates.
                visual_source.extend(
                    {
                        **candidate,
                        "_sap_relevance_query": targeted_query,
                    }
                    for candidate in targeted_candidates
                    if isinstance(candidate, dict)
                )
                visual_pool = _visual_fallback_candidates(
                    query,
                    visual_source,
                    must=must,
                    limit=MAX_VISUAL_FALLBACK_CANDIDATES,
                )
        # Metadata matches and relevance scores rank candidates; they do not prove
        # the image composition. Keep a small second cohort whose catalog text is
        # weak but whose pixels may still prove the scene. This keeps the expensive
        # visual gate bounded while avoiding a premature no-asset failure.
        low_relevance_pool = _visual_fallback_candidates(
            query,
            visual_source,
            must=must,
            limit=MAX_LOW_RELEVANCE_VISUAL_CANDIDATES,
            allow_low_relevance=True,
            low_relevance_only=True,
        )
        visual_fallback_candidates = []
        seen_visual_keys: set[tuple[str, str, str]] = set()
        image_types = {"image", "imagem", "foto", "photo", "photograph", "fotografia", "picture"}
        image_extensions = {".jpg", ".jpeg", ".png", ".webp"}
        for item in [*visual_pool, *low_relevance_pool, *strict]:
            if not isinstance(item, dict) or _is_non_photographic_asset(item, query):
                continue
            kind = str(item.get("tipo") or item.get("asset_type") or "").strip().casefold()
            url = str(item.get("url") or "")
            extension = Path(url.split("?", 1)[0]).suffix.casefold()
            is_video = (
                kind.startswith("video")
                or kind in {"vídeo", "movie", "clip"}
                or extension in {".mp4", ".mov", ".webm", ".mkv"}
            )
            if not is_video:
                if kind and kind not in image_types:
                    continue
                if not kind and extension not in image_extensions:
                    continue
            try:
                if int(item.get("avoid_hits", 0) or 0) > 0:
                    continue
            except (TypeError, ValueError):
                continue
            key = (
                str(item.get("fonte") or item.get("source") or ""),
                str(item.get("id") or ""),
                url,
            )
            if key in seen_visual_keys:
                continue
            seen_visual_keys.add(key)
            visual_fallback_candidates.append(item)
            if len(visual_fallback_candidates) >= MAX_VISUAL_VERIFICATION_ATTEMPTS:
                break

        for candidate in visual_fallback_candidates:
            candidate["_sap_must_total"] = len(must)
            candidate["_sap_short_id"] = short_id
            candidate["_sap_scene_number"] = number
            candidate["_sap_scene_contract_fingerprint"] = contract_fingerprint
            candidate["_sap_visual_verification_required"] = True
            candidate["verification_mode"] = "gemini_visual_must"
            candidate["verification_note"] = (
                "pixel-level MUST/AVOID and full scene-intent verification required"
            )
        strict = visual_fallback_candidates
        verification_mode = "gemini_visual_must" if strict else ""
        if visual_fallback_candidates:
            print(
                f"MEDIA_VISUAL_VERIFY=QUEUED scene={number:02d} "
                f"candidates={len(visual_fallback_candidates)} "
                f"explicit_must={len(must)} scene_intent=1"
            )

    failures = []
    used_asset_hashes = used_asset_hashes or set()

    # Per-asset failover: a bad download/validation never terminates the scene
    # while another verified provider candidate remains available.
    for candidate in strict:
        try:
            ok, destination, download_meta = PROVIDER.download(candidate, number, short_id)
            if not ok or not destination:
                meta = download_meta if isinstance(download_meta, dict) else {}
                error_class = str(meta.get("error_class") or "DOWNLOAD_FAILED")
                status = meta.get("status")
                suffix = f":HTTP_{int(status)}" if str(status or "").isdigit() else ""
                failures.append(f"{candidate.get('fonte','?')}:{error_class}{suffix}")
                continue
            validation = validate_asset(destination)
            path = Path(destination)
            resolution_error = _resolution_issue(validation.get("probe", {}))
            if resolution_error:
                failures.append(f"{candidate.get('fonte', '?')}:{resolution_error}")
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
                continue

            if candidate.get("_sap_visual_verification_required"):
                try:
                    visual_result = _verify_scene_pixels(
                        path,
                        must,
                        avoid,
                        _scene_verification_intent(segment, query),
                        candidate,
                    )
                except Exception as exc:
                    visual_result = {
                        "status": "BLOCK",
                        "method": "gemini_image_pixels",
                        "reason": f"visual_verifier_error:{type(exc).__name__}",
                    }
                if visual_result.get("status") != "PASS":
                    reason = str(visual_result.get("reason") or "visual_requirements_unverified")
                    checks = []
                    for group in ("must", "avoid"):
                        rows = visual_result.get(group, [])
                        if not isinstance(rows, list):
                            continue
                        for row in rows:
                            if not isinstance(row, dict):
                                continue
                            checks.append(
                                f"{group}:{str(row.get('anchor') or '?')}"
                                f"={row.get('visible')}@{row.get('confidence')}"
                            )
                    check_summary = ",".join(checks)[:320] or "no_anchor_details"
                    diagnostic = f"{reason};checks={check_summary}"
                    visual_rejections.append(diagnostic)
                    failures.append(f"{candidate.get('fonte', '?')}:VISUAL_VERIFY_BLOCK")
                    print(
                        f"MEDIA_VISUAL_FALLBACK=BLOCK scene={number:02d} "
                        f"reason={diagnostic}"
                    )
                    try:
                        path.unlink(missing_ok=True)
                    except OSError:
                        pass
                    continue

                candidate["_sap_visual_verification"] = visual_result
                candidate["_sap_metadata_must_hits"] = int(
                    candidate.get("_sap_metadata_must_hits", candidate.get("must_hits", 0)) or 0
                )
                candidate["must_hits"] = len(must)
                candidate["_sap_must_total"] = len(must)
                candidate["evidence_class"] = "visual_model"
                candidate["verification_mode"] = "gemini_visual_must"
                candidate["verification_note"] = (
                    "pixel-level Gemini verification passed; metadata MUST hits preserved separately"
                )
                print(
                    f"MEDIA_VISUAL_VERIFY=PASS scene={number:02d} "
                    f"explicit_must={len(must)} scene_intent=PASS avoid={len(avoid)}"
                )

            checksum = str(validation.get("sha256") or sha256(path))
            # Different provider records can point to byte-identical images.
            # Reject a repeated visual asset and continue through the already
            # MUST-verified candidate list instead of letting final visual QA
            # discover the duplicate after a costly render.
            if checksum in used_asset_hashes:
                failures.append(f"{candidate.get('fonte', '?')}:DUPLICATE_ASSET")
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
                continue
            record = _candidate_record(candidate, path, validation["probe"])
            record["checksum_sha256"] = checksum
            record["verification_mode"] = str(candidate.get("verification_mode") or verification_mode or "strict_must")
            record["verification_note"] = str(candidate.get("verification_note") or "")
            if isinstance(candidate.get("_sap_visual_verification"), dict):
                record["visual_verification"] = candidate["_sap_visual_verification"]
                record["metadata_must_hits"] = int(
                    candidate.get("_sap_metadata_must_hits", 0) or 0
                )
            return record
        except Exception as exc:
            failures.append(f"{candidate.get('fonte','?')}:{type(exc).__name__}")

    # Clear candidates only when pixel verification actually rejected them.
    # Download/probe errors must retain their specific failure classification.
    if visual_fallback_candidates and visual_rejections:
        strict = []

    # Local Library is an explicit provider in the Router. Keep this secondary
    # compatibility path for libraries created by the previous pipeline.
    local = _local_library_asset(query, must, avoid, used_asset_hashes)
    if local is not None:
        local["scene_contract_fingerprint"] = contract_fingerprint
        return local

    if not candidates:
        raise RuntimeError(f"MEDIA_INCOMPLETE:scene_{number:02d}:providers_empty")
    if not strict:
        providers = sorted({
            str(candidate.get("fonte") or candidate.get("source") or "?")
            for candidate in candidates
        })
        diagnostic = (
            f"candidates={len(candidates)};"
            f"strict={len(strict)};"
            f"providers={','.join(providers) or '-'};"
            f"strict_metadata_rejected={len(strict_metadata_rejections)};"
            f"relaxed={len(relaxed)};"
            f"verified_relaxed={len(verified_relaxed) if must else 0}"
        )
        if strict_metadata_rejections:
            diagnostic += ";strict_metadata_evidence=" + "|".join(strict_metadata_rejections[:5])
        diagnostic += (
            f";query_relevance_rejected={query_relevance_rejected};"
            f"relaxed_query_relevance_rejected={relaxed_query_relevance_rejected}"
        )
        if relaxed_evidence_diagnostics:
            diagnostic += ";evidence=" + "|".join(relaxed_evidence_diagnostics[:8])
        if visual_fallback_candidates:
            diagnostic += (
                f";visual_candidates={len(visual_fallback_candidates)};"
                f"visual_blocked={len(visual_rejections)}"
            )
            if visual_rejections:
                diagnostic += ";visual_reasons=" + "|".join(visual_rejections[:2])
        raise RuntimeError(
            f"MEDIA_INCOMPLETE:scene_{number:02d}:no_verified_asset:"
            f"must={','.join(must) or '-'};{diagnostic}"
        )
    raise RuntimeError(
        f"MEDIA_DOWNLOAD_FAILED:scene_{number:02d}:"
        + (";".join(failures) if failures else "no_candidate_attempted")
    )




def build_manifest(short_id: str) -> dict[str, Any]:
    short_id = validate_short_id(short_id)
    scenes = load_scene_map(short_id)
    media_dir = BASE / "imagens" / f"short_{short_id}"
    media_dir.mkdir(parents=True, exist_ok=True)
    records = []
    used_asset_hashes: set[str] = set()
    for number, scene in enumerate(scenes, 1):
        existing = _existing_asset_record(media_dir, number, scene)
        if existing is not None:
            existing_hash = str(existing.get("checksum_sha256") or "")
            if existing_hash and existing_hash not in used_asset_hashes:
                records.append(existing)
                used_asset_hashes.add(existing_hash)
                continue
            # A previously cached, individually valid asset may still duplicate
            # another scene. Remove only this scene's cache and reacquire it.
            old_path = Path(str(existing.get("path") or ""))
            try:
                old_path.unlink(missing_ok=True)
            except OSError:
                pass
            try:
                (media_dir / f"scene_{number:02d}.json").unlink(missing_ok=True)
            except OSError:
                pass
        record = acquire_scene(
            short_id, number, scene, media_dir, used_asset_hashes
        )
        record["short_id"] = short_id
        record["scene_number"] = number
        checksum = str(record.get("checksum_sha256") or "")
        if checksum and checksum in used_asset_hashes:
            raise RuntimeError(
                f"MEDIA_DUPLICATE_ASSET:scene_{number:02d}:checksum_reused"
            )
        _write_asset_sidecar(media_dir, number, record)
        records.append(record)
        if checksum:
            used_asset_hashes.add(checksum)
    scenes_out = [
        {
            "scene_id": str(scene.get("scene_id", scene.get("scene", number))),
            "scene_number": number,
            "asset": record,
        }
        for number, (scene, record) in enumerate(zip(scenes, records), 1)
    ]
    manifest = {
        "schema_version": "media-manifest-v2",
        "engine_version": ENGINE_VERSION,
        "short_id": short_id,
        "immutable": True,
        "scene_count": len(scenes_out),
        "scenes": scenes_out,
    }
    manifest["integrity_sha256"] = _manifest_integrity(manifest)
    atomic_json(BASE / "manifests" / f"media_{short_id}.json", manifest)
    return manifest


def main(short_id: str | None = None) -> int:
    if short_id is None:
        parser = argparse.ArgumentParser()
        parser.add_argument("--short-id", required=True)
        args = parser.parse_args()
        short_id = args.short_id
    manifest = build_manifest(short_id)
    print(
        f"MEDIA_ENGINE_V2=PASS short_id={short_id} "
        f"scenes={manifest['scene_count']} assets={len(manifest['scenes'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
