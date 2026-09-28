#!/usr/bin/env python3
"""Regression tests for bounded Wikimedia HTTP search budgets."""

import time
import unittest
from unittest.mock import patch


class _Response:
    ok = True
    status_code = 200

    def json(self):
        return {"query": {"pages": []}}


class WikimediaDeadlineTests(unittest.TestCase):
    def test_single_request_stays_inside_search_deadline(self):
        import wikimedia_source as source

        captured = {}

        def fake_get(*args, **kwargs):
            captured["timeout"] = kwargs["timeout"]
            return _Response()

        deadline = time.monotonic() + 2.0
        with patch.object(source, "_sap_provider_gate", return_value=(True, "OK", 2.0)),              patch.object(source, "requests") as requests_mock:
            requests_mock.get.side_effect = fake_get
            pages = source.consultar_commons(
                "test",
                1,
                deadline_at=deadline,
            )

        self.assertEqual(pages, [])
        connect_timeout, read_timeout = captured["timeout"]
        self.assertGreater(connect_timeout, 0)
        self.assertGreater(read_timeout, 0)
        self.assertLessEqual(read_timeout, 1.9)
        self.assertLessEqual(connect_timeout, read_timeout)

    def test_expired_deadline_skips_http_request(self):
        import wikimedia_source as source

        with patch.object(source, "_sap_provider_gate", return_value=(True, "OK", 2.0)),              patch.object(source, "requests") as requests_mock:
            pages = source.consultar_commons(
                "test",
                1,
                deadline_at=time.monotonic() - 1.0,
            )

        self.assertEqual(pages, [])
        requests_mock.get.assert_not_called()


if __name__ == "__main__":
    unittest.main()
