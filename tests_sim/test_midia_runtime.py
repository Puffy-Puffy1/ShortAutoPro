import unittest

from midia_runtime import EXPECTED_BROKEN_COUNTS, fix_source


BROKEN = '''for scene in scenes:
    if chosen:
        for candidate in pool:
            if ok:
                success = True
                # Primeiro download válido vence.
                break
                destino = destino_teste
                print("commit")
                break

                # SHORTAUTOPRO VSE42 SUCCESS COMMIT
                print("success commit")
                _vse42_cleanup_scene_sibling(destino)
                break
        _vse42_cleanup_scene_sibling(destino)
        break

    if not success:
        for alt in alternatives:
            if success:
                break
        _vse42_cleanup_scene_sibling(destino)
        break

    if not success and degraded:
        for candidate in degraded:
            if ok:
                break
        _vse42_cleanup_scene_sibling(destino)
        break

    if not success:
        if origin:
            _vse42_cleanup_scene_sibling(destino)
            _vse42_commit_safe(escolhido)
            break
        _vse42_cleanup_scene_sibling(destino)
        _vse42_commit_safe(escolhido)
        break

    if success:
        total += 1
'''


class MediaRuntimeFixTests(unittest.TestCase):
    def test_known_seven_premature_breaks_are_removed(self):
        fixed, counters = fix_source(BROKEN)
        self.assertEqual(counters, EXPECTED_BROKEN_COUNTS)
        self.assertIn("destino = destino_teste", fixed)
        self.assertIn("total += 1", fixed)
        # The legitimate inner-loop breaks stay in place.
        self.assertGreaterEqual(fixed.count("break"), 3)
        self.assertNotIn("        _vse42_cleanup_scene_sibling(destino)\n        break", fixed)

    def test_already_fixed_source_is_transparent(self):
        source = "for scene in scenes:\n    total += 1\n"
        fixed, counters = fix_source(source)
        self.assertEqual(fixed, source)
        self.assertEqual(sum(counters.values()), 0)

    def test_partial_unknown_layout_fails_closed(self):
        partial = '''for scene in scenes:
    if chosen:
        for candidate in pool:
            if ok:
                break
                destino = destino_teste
'''
        with self.assertRaises(RuntimeError):
            fix_source(partial)


if __name__ == "__main__":
    unittest.main()
