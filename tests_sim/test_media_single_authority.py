import os
import unittest
from unittest import mock

import media_runtime_adapter_v1 as adapter


class MediaSingleAuthorityTests(unittest.TestCase):
    def test_vi6_is_shadow_and_legacy_decision_bridges_are_disabled(self):
        namespace = {"VI6_MODE": "ACTIVE"}
        with mock.patch.dict(os.environ, {}, clear=False):
            result = adapter.install(namespace)
            self.assertEqual(namespace["VI6_MODE"], "SHADOW")
            self.assertEqual(os.environ["VISUAL_INTELLIGENCE_MODE"], "SHADOW")
            self.assertEqual(os.environ["SAP_VISUAL_UNIFIED"], "1")
            self.assertEqual(os.environ["SAP_VSE42_BRIDGE"], "0")
            self.assertEqual(os.environ["SAP_VG4X"], "0")
            self.assertEqual(os.environ["SAP_VSE42_RESCUE"], "0")
            self.assertEqual(os.environ["SAP_VSE4_QUERY_EXPANSION"], "1")
            self.assertEqual(result["vi6_mode"], "SHADOW")


if __name__ == "__main__":
    unittest.main()
