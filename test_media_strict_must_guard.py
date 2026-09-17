#!/usr/bin/env python3
"""Regression tests for fail-closed explicit-MUST media commits."""
from __future__ import annotations

import unittest
from unittest import mock

import media_strict_must_guard as guard


class StrictMustGuardTests(unittest.TestCase):
    def namespace(self):
        return {
            "busca": "dummy head made of paper mache with real hair",
            "must_have": ["dummy head", "paper mache"],
            "ordenar_failover_5_2": lambda candidates, total, route, previous="": list(candidates),
            "fallback_preserva_5_2": lambda candidate, reference: True,
            "fallback_degradado_ok_5_2": lambda candidate, total: True,
            "baixar_candidato_5_2": lambda candidate, scene, label: (True, "/tmp/scene.jpg"),
            "buscar_local": lambda prefer_video: "/tmp/previous.jpg",
        }

    @staticmethod
    def partial():
        return {
            "fonte": "Pixabay",
            "tipo": "foto",
            "description": "a handmade dummy head with real hair",
            "must_hits": 2,  # provider claim must not be authoritative
            "avoid_hits": 0,
        }

    @staticmethod
    def complete():
        return {
            "fonte": "Wikimedia",
            "tipo": "foto",
            "description": "dummy head made of paper mache with real hair",
            "must_hits": 0,
            "avoid_hits": 0,
        }

    def test_partial_explicit_must_is_removed_from_failover(self):
        ns = self.namespace()
        guard.install(ns)
        result = ns["ordenar_failover_5_2"]([self.partial()], 2, "stock_first")
        self.assertEqual(result, [])

    def test_complete_explicit_must_survives_and_can_download(self):
        ns = self.namespace()
        guard.install(ns)
        candidate = self.complete()
        result = ns["ordenar_failover_5_2"]([candidate], 2, "documentary_first")
        self.assertEqual(result, [candidate])
        self.assertEqual(candidate["_sap_verified_must_hits"], 2)
        self.assertEqual(ns["baixar_candidato_5_2"](candidate, 2, "TEST"), (True, "/tmp/scene.jpg"))

    def test_partial_explicit_must_cannot_download_or_use_degraded_escape(self):
        ns = self.namespace()
        guard.install(ns)
        candidate = self.partial()
        self.assertEqual(ns["baixar_candidato_5_2"](candidate, 2, "TEST"), (False, None))
        self.assertFalse(ns["fallback_preserva_5_2"](candidate, None))
        self.assertFalse(ns["fallback_degradado_ok_5_2"](candidate, 2))

    def test_explicit_must_blocks_local_continuity_fallback(self):
        ns = self.namespace()
        guard.install(ns)
        self.assertIsNone(ns["buscar_local"](False))

    def test_no_must_preserves_existing_local_fallback(self):
        ns = self.namespace()
        ns["must_have"] = []
        guard.install(ns)
        self.assertEqual(ns["buscar_local"](False), "/tmp/previous.jpg")

    def test_verifier_failure_is_fail_closed(self):
        ns = self.namespace()
        candidate = self.complete()
        with mock.patch.object(guard.v1, "normalize_candidate", side_effect=RuntimeError("boom")):
            self.assertFalse(guard._strict_ok(ns, candidate))
            self.assertEqual(guard._verified_hits(ns, candidate), (0, 2))


if __name__ == "__main__":
    unittest.main(verbosity=2)
