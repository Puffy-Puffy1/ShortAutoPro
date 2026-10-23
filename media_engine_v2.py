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
ENGINE_VERSION = "2.0.5"
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
    contextual_matches = [
        str(term).casefold()
        for term in matched_terms
        if str(term).casefold() not in must_tokens
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
        musts, events = normalize_visual_musts(
            scene.get("must_have") or [],
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

        verified_relaxed = []
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
            return record
        except Exception as exc:
            failures.append(f"{candidate.get('fonte','?')}:{type(exc).__name__}")

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
