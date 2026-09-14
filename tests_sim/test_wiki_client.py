import tempfile
import unittest
from pathlib import Path

import wiki_client


class WikiCacheTests(unittest.TestCase):
    def test_atomic_cache_round_trip_and_no_fixed_tmp_collision(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = wiki_client.CACHE_DIR
            wiki_client.CACHE_DIR = Path(tmp)
            try:
                payload = [{"title": "Exemplo"}]
                wiki_client._salvar_cache("search", "chave", payload)
                self.assertEqual(wiki_client._ler_cache("search", "chave"), payload)
                leftovers = list(Path(tmp).glob("*.tmp"))
                self.assertEqual(leftovers, [])
            finally:
                wiki_client.CACHE_DIR = original

    def test_corrupt_cache_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            original = wiki_client.CACHE_DIR
            wiki_client.CACHE_DIR = Path(tmp)
            try:
                path = wiki_client._cache_path("extract", "abc")
                path.write_text("{bad", encoding="utf-8")
                self.assertIsNone(wiki_client._ler_cache("extract", "abc"))
            finally:
                wiki_client.CACHE_DIR = original


if __name__ == "__main__":
    unittest.main()
