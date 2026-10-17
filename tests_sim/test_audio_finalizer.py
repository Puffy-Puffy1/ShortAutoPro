"""Regression tests for bounded audio-finalizer recovery."""
from __future__ import annotations

import audio_finalizer as finalizer


def test_retries_dynamic_mastering_when_first_pass_still_fails(monkeypatch, tmp_path):
    video = tmp_path / "short.mp4"
    video.write_bytes(b"x" * 600_000)
    report = tmp_path / "report.json"
    monkeypatch.setattr(finalizer, "VIDEO", video)
    monkeypatch.setattr(finalizer, "REPORT", report)

    measurements = iter([
        {"lufs": -18.28, "true_peak_db": -0.01, "lra": 4.0, "threshold": -28.0, "offset": 4.0},
        {"lufs": -18.10, "true_peak_db": -0.50, "lra": 4.0, "threshold": -28.0, "offset": 4.0},
        {"lufs": -14.20, "true_peak_db": -1.70, "lra": 4.0, "threshold": -24.0, "offset": 0.0},
    ])
    calls = []

    monkeypatch.setattr(finalizer, "measure", lambda _path: next(measurements))
    monkeypatch.setattr(
        finalizer,
        "remaster",
        lambda _path, measured, *, linear=True: calls.append((measured["lufs"], linear)),
    )

    assert finalizer.main() == 0
    assert calls == [(-18.28, True), (-18.1, False)]
    import json
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["status"] == "PASS"
    assert payload["measurement_source"] == "post_remaster_dynamic_retry"


def test_does_not_remaster_when_audio_is_already_within_policy(monkeypatch, tmp_path):
    video = tmp_path / "short.mp4"
    video.write_bytes(b"x" * 600_000)
    monkeypatch.setattr(finalizer, "VIDEO", video)
    monkeypatch.setattr(finalizer, "REPORT", tmp_path / "report.json")
    monkeypatch.setattr(
        finalizer,
        "measure",
        lambda _path: {"lufs": -14.1, "true_peak_db": -1.6, "lra": 4.0, "threshold": -24.0, "offset": 0.0},
    )
    monkeypatch.setattr(
        finalizer,
        "remaster",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("unexpected remaster")),
    )

    assert finalizer.main() == 0
