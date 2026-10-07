from recovery_controller import RecoveryAction, RecoveryController


def test_controller_limits_actions():
    calls = []
    actions = [
        RecoveryAction(f"a{i}", lambda i=i: calls.append(i) or {"status": "PASS"})
        for i in range(10)
    ]
    result = RecoveryController(max_actions=99).run(actions)
    assert result.status == "RECOVERED"
    assert result.attempts == 4
    assert calls == [0, 1, 2, 3]


def test_controller_stops_on_failure():
    calls = []

    def fail():
        calls.append("fail")
        return {"status": "FAIL", "reason": "provider_timeout"}

    def should_not_run():
        calls.append("after")
        return {"status": "PASS"}

    result = RecoveryController().run([
        RecoveryAction("fail", fail),
        RecoveryAction("after", should_not_run),
    ])

    assert result.status == "BLOCKED"
    assert result.reason == "recovery_action_failed"
    assert calls == ["fail"]


def test_controller_catches_action_exception():
    result = RecoveryController().run([
        RecoveryAction("boom", lambda: 1 / 0),
    ])
    assert result.status == "BLOCKED"
    assert result.actions[0]["reason"] == "recovery_action_exception"


def test_controller_has_no_retry_loop():
    calls = []

    def fail():
        calls.append(1)
        return {"status": "FAIL"}

    result = RecoveryController(max_actions=4).run([RecoveryAction("one", fail)])
    assert result.attempts == 1
    assert len(calls) == 1
