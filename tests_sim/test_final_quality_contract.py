import unittest

from final_quality import MANIFEST_REQUIRED_FLAGS, avaliar


SCRIPT = " ".join(["palavra"] * 110)
HOOK = "Como esse mistério nunca deixou uma resposta definitiva?"
PUBLISH = {"publish_score": 90}


def valid_manifest():
    quality = {flag: True for flag in MANIFEST_REQUIRED_FLAGS}
    return {
        "status": "QUALITY_PASS",
        "quality": quality,
        "video": {"duration_seconds": 43.0},
        "scenes": {"count": 12, "physical_count": 12},
    }


class FinalQualityContractTests(unittest.TestCase):
    def test_valid_manifest_contract_passes(self):
        result = avaliar(valid_manifest(), PUBLISH, SCRIPT, HOOK)
        self.assertTrue(result["approved"], result["critical"])
        self.assertEqual(result["critical"], [])

    def test_codec_failure_blocks_even_if_status_is_quality_pass(self):
        manifest = valid_manifest()
        manifest["quality"]["video_codec_ok"] = False
        result = avaliar(manifest, PUBLISH, SCRIPT, HOOK)
        self.assertFalse(result["approved"])
        self.assertIn(
            "manifest_quality_failed=video_codec_ok",
            result["critical"],
        )

    def test_publish_integrity_failure_blocks_even_if_status_is_quality_pass(self):
        manifest = valid_manifest()
        manifest["quality"]["publish_integrity_pass"] = False
        result = avaliar(manifest, PUBLISH, SCRIPT, HOOK)
        self.assertFalse(result["approved"])
        self.assertIn(
            "manifest_quality_failed=publish_integrity_pass",
            result["critical"],
        )

    def test_source_ledger_failure_blocks_even_if_score_is_high(self):
        manifest = valid_manifest()
        manifest["quality"]["source_ledger_exists"] = False
        result = avaliar(manifest, PUBLISH, SCRIPT, HOOK)
        self.assertFalse(result["approved"])
        self.assertGreaterEqual(result["total_score"], 65)
        self.assertIn(
            "manifest_quality_failed=source_ledger_exists",
            result["critical"],
        )


if __name__ == "__main__":
    unittest.main()
