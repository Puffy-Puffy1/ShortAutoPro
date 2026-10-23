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
ENGINE_VERSION = "2.0.8"
MIN_VISUAL_PIXELS = 320 * 180


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
        "query": re.sub(r"\s+", " ", query).strip().casefold(),
        "segment": re.sub(r"\s+", " ", segment).strip().casefold(),
        "visual_mode": re.sub(r"\s+", " ", visual_mode).strip().casefold(),
        "must_have": _contract_values(scene.get("must_have") or []),
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
        raw_musts = scene.get("must_have") or []
        musts, events = normalize_visual_musts(
            raw_musts,
            context=scene_query,
        )
        scene["must_have"] = musts
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
        record = dict(candidate)
        record["fonte"] = "LocalLibrary"
        record["_sap_must_total"] = len(must)
        record["must_hits"] = len(must)
        return _candidate_record(record, path, probe)
    return None


def _visual_fallback_candidates(
    query: str,
    candidates: list[dict[str, Any]],
    must: list[str] | None = None,
    limit: int = 2,
) -> list[dict[str, Any]]:
    """Choose a tiny set of relevant real images for pixel-level verification.

    This is discovery only. No candidate is accepted until its downloaded pixels
    pass media_visual_verifier and the existing media validator.
    """
    from media_provider_router_v2 import query_relevance

    image_types = {"image", "imagem", "photo", "photograph", "fotografia", "picture"}
    image_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}

    for candidate in candidates:
        if not isinstance(candidate, dict):
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

        relevance = query_relevance(query, candidate)
        relevance_candidate = {**candidate, "query_relevance": relevance}
        # A below-threshold relevance score may still be inspected when at least
        # one independent scene-context term matches outside the MUST anchors.
        # Pixel verification remains the only path that can accept these assets.
        if not _relaxed_relevance_acceptable(relevance_candidate, must or []):
            continue
        # Copy only eligible candidates: a rejected result must not be mutated
        # and affect a later retry or a different acquisition attempt.
        candidate = dict(relevance_candidate)
        candidate["_sap_metadata_must_hits"] = int(candidate.get("must_hits", 0) or 0)
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
            int(candidate.get("_sap_metadata_must_hits", 0) or 0),
            int((candidate.get("query_relevance") or {}).get("matched_count", 0) or 0),
            float(candidate.get("score", 0) or 0),
        ),
        reverse=True,
    )
    return ranked[:max(1, min(int(limit), 3))]


def acquire_scene(
    short_id: str,
    number: int,
    scene: dict[str, Any],
    media_dir: Path,
    used_asset_hashes: set[str] | None = None,
) -> dict[str, Any]:
    query = str(scene.get("query") or scene.get("busca") or scene.get("segment") or "").strip()
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
    strict = [
        candidate for candidate in PROVIDER.prepare(candidates, len(must))
        if not isinstance(candidate.get("query_relevance"), dict)
        or candidate["query_relevance"].get("ok") is True
    ]
    for candidate in strict:
        candidate["_sap_scene_contract_fingerprint"] = contract_fingerprint
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
    if not strict and must:
        visual_fallback_candidates = _visual_fallback_candidates(
            query,
            [*candidates, *relaxed],
            must=must,
            limit=2,
        )
        for candidate in visual_fallback_candidates:
            candidate["_sap_must_total"] = len(must)
            candidate["_sap_short_id"] = short_id
            candidate["_sap_scene_number"] = number
            candidate["_sap_scene_contract_fingerprint"] = contract_fingerprint
            candidate["_sap_visual_verification_required"] = True
            candidate["verification_mode"] = "gemini_visual_must"
            candidate["verification_note"] = (
                "pixel-level verification required; metadata hits remain separately recorded"
            )
        if visual_fallback_candidates:
            verification_mode = "gemini_visual_must"
            print(
                f"MEDIA_VISUAL_FALLBACK=START scene={number:02d} "
                f"candidates={len(visual_fallback_candidates)}"
            )
        strict = visual_fallback_candidates

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
                    from media_visual_verifier import verify_image_requirements
                    visual_result = verify_image_requirements(path, must, avoid)
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
                    f"MEDIA_VISUAL_FALLBACK=PASS scene={number:02d} "
                    f"must={len(must)} avoid={len(avoid)}"
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

    # If all bounded pixel checks failed, these assets are still unverified and
    # must not leave the gate in a partially accepted state.
    if visual_fallback_candidates:
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
            f"relaxed={len(relaxed)};"
            f"verified_relaxed={len(verified_relaxed) if must else 0}"
        )
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
