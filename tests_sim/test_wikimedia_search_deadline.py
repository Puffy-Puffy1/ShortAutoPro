"""Historical compatibility test retained but disabled after canonical V3 retirement."""
import unittest


class LegacyWikimediaSearchDeadlineCompatibilityTests(unittest.TestCase):
    @unittest.skip("legacy compatibility test disabled: canonical V3 owns provider health/source routing")
    def test_legacy_wikimedia_search_deadline(self):
        pass
