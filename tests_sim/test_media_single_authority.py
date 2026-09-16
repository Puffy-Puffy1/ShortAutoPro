import os
import unittest
from unittest import mock

import media_runtime_adapter_v1 as adapter


class MediaSingleAuthorityTests(unittest.TestCase):
    def test_vi6_is_shadow_and_all_legacy_decision_bridges_are_disabled(self):
        namespace = {"VI6_MODE": "ACTIVE"}
        with mock.patch.dict(os.environ, {}, clear=False):
            result = adapter.install(namespace)
            self.assertEqual(namespace["VI6_MODE"], "SHADOW")
            expected = {
                "VISUAL_INTELLIGENCE_MODE": "SHADOW",
                "SAP_VISUAL_UNIFIED": "1",
                "SAP_VSE4": "0",
                "SAP_VSE4_RESCUE": "0",
                "SAP_VSE_V42": "0",
                "SAP_VSE42": "0",
                "SAP_VSE42_RUNTIME": "0",
                "SAP_VSE42_BRIDGE": "0",
                "SAP_VSE42_RESCUE": "0",
                "SAP_VSE4_QUERY_EXPANSION": "1",
                "SAP_VG4X": "0",
            }
            for key, value in expected.items():
                self.assertEqual(os.environ[key], value, key)
            self.assertEqual(result["vi6_mode"], "SHADOW")
            self.assertFalse(result["legacy_vse4"])
            self.assertFalse(result["legacy_vse42"])
            self.assertFalse(result["legacy_vg4x"])


if __name__ == "__main__":
    unittest.main()
