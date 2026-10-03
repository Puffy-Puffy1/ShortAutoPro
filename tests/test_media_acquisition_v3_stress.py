import json, struct, tempfile, unittest, zlib
from pathlib import Path

import media_acquisition_v3
from media_v3.acquisition import MediaAcquisitionV3
from media_v3.providers import ProviderAdapter, ProviderRegistry, ProviderStatus


def make_png():
    w = h = 64
    rows = []
    for y in range(h):
        rows.append(b"\x00" + b"".join(bytes(((x * 4) % 256, (y * 4) % 256, 180)) for x in range(w)))
    raw = b"".join(rows)
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


class FixtureProvider(ProviderAdapter):
    name = "fixture"

    def __init__(self, fixture: Path, fail_token: str = ""):
        self.fixture = Path(fixture)
        self.fail_token = fail_token
        self.calls = []

    def status(self):
        return ProviderStatus(True)

    def search(self, query):
        self.calls.append(query)
        if self.fail_token and self.fail_token.casefold() in query.casefold():
            raise RuntimeError("TIMEOUT")
        return [{
            "provider": self.name,
            "kind": "image",
            "id": "fixture-" + query.replace(" ", "-"),
            "url": "file://fixture",
            "local_path": str(self.fixture),
            "description": query + " fixture visual scene",
            "tags": "fixture visual",
        }]


class AcquisitionV3StressTests(unittest.TestCase):
    def _scene(self, query="fixture"):
        return {"scene_id": "scene_01", "query": query}

    def _prepare(self, base: Path, sid: str, query="fixture"):
        (base / "roteiros").mkdir(parents=True, exist_ok=True)
        (base / "roteiros" / f"scene_map_{sid}.json").write_text(
            json.dumps({"scenes": [self._scene(query)]}), encoding="utf-8"
        )

    def test_sequential_1_2_5_10_jobs_are_isolated(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            fixture = base / "fixture.png"
            fixture.write_bytes(make_png())
            media_acquisition_v3.BASE = base
            engine = MediaAcquisitionV3(base, ProviderRegistry([FixtureProvider(fixture)]))
            counts = (1, 2, 5, 10)
            total = 0
            seen_ids = []
            for count in counts:
                for _ in range(count):
                    total += 1
                    sid = f"JOB_{total:02d}"
                    self._prepare(base, sid)
                    manifest = media_acquisition_v3.build_manifest(sid, engine)
                    seen_ids.append(sid)
                    self.assertEqual(manifest["short_id"], sid)
                    self.assertEqual(manifest["scene_count"], 1)
                    self.assertTrue((base / "manifests" / f"media_{sid}.json").is_file())
            self.assertEqual(len(seen_ids), 18)
            self.assertEqual(len(set(seen_ids)), 18)
            for sid in seen_ids:
                media_dir = base / "imagens" / f"short_{sid}"
                self.assertTrue((media_dir / "scene_01_fixture.png").is_file())
                sidecar = json.loads((media_dir / "scene_01.json").read_text(encoding="utf-8"))
                self.assertEqual(sidecar["short_id"], sid)
                manifest = json.loads((base / "manifests" / f"media_{sid}.json").read_text(encoding="utf-8"))
                self.assertEqual(manifest["short_id"], sid)
                self.assertEqual(manifest["scene_count"], 1)

    def test_resume_reuses_frozen_media_without_reacquisition(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            fixture = base / "fixture.png"
            fixture.write_bytes(make_png())
            media_acquisition_v3.BASE = base
            provider = FixtureProvider(fixture)
            engine = MediaAcquisitionV3(base, ProviderRegistry([provider]))
            sid = "RESUME_01"
            self._prepare(base, sid)
            first = media_acquisition_v3.build_manifest(sid, engine)
            calls_after_first = len(provider.calls)
            second = media_acquisition_v3.build_manifest(sid, engine)
            self.assertEqual(first["integrity_sha256"], second["integrity_sha256"])
            self.assertEqual(len(provider.calls), calls_after_first)

    def test_batch_failure_does_not_stop_other_jobs(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            fixture = base / "fixture.png"
            fixture.write_bytes(make_png())
            media_acquisition_v3.BASE = base
            engine = MediaAcquisitionV3(base, ProviderRegistry([FixtureProvider(fixture, fail_token="FAIL_JOB_02")]))
            results = {}
            for n in range(1, 6):
                sid = f"FAIL_JOB_{n:02d}"
                self._prepare(base, sid, query=sid)
                try:
                    media_acquisition_v3.build_manifest(sid, engine)
                    results[sid] = "COMPLETED"
                except RuntimeError:
                    results[sid] = "FAILED"
            self.assertEqual(results["FAIL_JOB_02"], "FAILED")
            self.assertEqual(
                [results[f"FAIL_JOB_{n:02d}"] for n in (1, 3, 4, 5)],
                ["COMPLETED"] * 4,
            )

    def test_failure_diagnostics_are_written_and_typed(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            fixture = base / "fixture.png"
            fixture.write_bytes(make_png())
            media_acquisition_v3.BASE = base
            engine = MediaAcquisitionV3(
                base,
                ProviderRegistry([FixtureProvider(fixture, fail_token="NOPE")]),
            )
            sid = "DIAG_01"
            self._prepare(base, sid, query="NOPE")
            with self.assertRaises(RuntimeError):
                media_acquisition_v3.build_manifest(sid, engine)
            report = json.loads(
                (base / "reports" / "media" / f"acquisition_{sid}.json").read_text(encoding="utf-8")
            )
            scene = report["scenes"][0]
            self.assertEqual(report["final_status"], "FAILED")
            self.assertIn("TIMEOUT", {item["reason"] for item in scene["rejections"]} | {x.get("reason") for x in scene["fallbacks"]})
            self.assertTrue(scene["query_variants"])
            self.assertEqual(scene["candidates_downloaded"], 0)


if __name__ == "__main__":
    unittest.main()
