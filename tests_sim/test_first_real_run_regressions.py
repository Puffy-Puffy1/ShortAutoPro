import unittest

import midia_runtime as mr


class MediaRuntimeResolutionGuardTests(unittest.TestCase):
    def test_guard_rejects_subcritical_download_before_commit(self):
        source = '''\n        if largura <= 0 or altura <= 0:\n            raise RuntimeError(\n                "dimensões inválidas"\n            )\n\n        os.replace(\n            temporario,\n            destino\n        )\n'''
        patched, applied = mr.harden_download_resolution(source)
        self.assertTrue(applied)
        self.assertIn("largura * altura < 320 * 180", patched)
        self.assertIn("mídia abaixo do piso técnico", patched)

    def test_guard_is_idempotent(self):
        source = '''\n        if largura <= 0 or altura <= 0:\n            raise RuntimeError(\n                "dimensões inválidas"\n            )\n'''
        patched, applied = mr.harden_download_resolution(source)
        self.assertTrue(applied)
        patched_again, applied_again = mr.harden_download_resolution(patched)
        self.assertFalse(applied_again)
        self.assertEqual(patched_again, patched)

    def test_guard_fails_closed_when_upstream_layout_changes(self):
        with self.assertRaises(RuntimeError):
            mr.harden_download_resolution("def baixar():\n    pass\n")


if __name__ == "__main__":
    unittest.main()
