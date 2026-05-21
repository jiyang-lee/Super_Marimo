from bridge.main import Bridge


class _FakeApiBridge:
    def __init__(self, status):
        self.status = status

    def sensor_runtime_status(self):
        return self.status


def test_should_accept_wakeword_requires_distance_threshold() -> None:
    bridge = Bridge.__new__(Bridge)
    bridge.api_bridge = _FakeApiBridge(
        {
            "settings": {"wake_enabled": True},
            "wake_eligible": True,
        }
    )

    assert bridge.should_accept_wakeword() is True

    bridge.api_bridge = _FakeApiBridge(
        {
            "settings": {"wake_enabled": True},
            "wake_eligible": False,
        }
    )

    assert bridge.should_accept_wakeword() is False


def test_should_accept_wakeword_blocks_when_status_unavailable() -> None:
    class _BrokenApiBridge:
        def sensor_runtime_status(self):
            raise RuntimeError("unavailable")

    bridge = Bridge.__new__(Bridge)
    bridge.api_bridge = _BrokenApiBridge()

    assert bridge.should_accept_wakeword() is False
