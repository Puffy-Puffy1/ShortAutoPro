import unittest

from midia_runtime import EXPECTED_BROKEN_COUNTS, fix_source, harden_cleanup


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

CLEANUP = '''# LIMPAR MÍDIA ANTIGA
for nome in os.listdir(SAIDA_DIR):
    if nome.lower().endswith(
        (
            ".jpg",
            ".jpeg",
            ".png",
            ".mp4"
        )
    ):
        os.remove(nome)

# TEXTO
print("next")
'''


class MediaRuntimeFixTests(unittest.TestCase):
    def test_known_seven_premature_breaks_are_removed(self):
        fixed, counters = fix_source(BROKEN)
        self.assertEqual(counters, EXPECTED_BROKEN_COUNTS)
        self.assertIn("destino = destino_teste", fixed)
        self.assertIn("total += 1", fixed)
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

    def test_cleanup_adds_webp_exactly_once(self):
        fixed, applied = harden_cleanup(CLEANUP)
        self.assertTrue(applied)
        self.assertEqual(fixed.count('".webp"'), 1)

        fixed_again, applied_again = harden_cleanup(fixed)
        self.assertFalse(applied_again)
        self.assertEqual(fixed_again, fixed)

    def test_unknown_cleanup_layout_fails_closed(self):
        source = '''# LIMPAR MÍDIA ANTIGA
extensions = [".jpg", ".mp4"]
# TEXTO
'''
        with self.assertRaises(RuntimeError):
            harden_cleanup(source)


if __name__ == "__main__":
    unittest.main()
