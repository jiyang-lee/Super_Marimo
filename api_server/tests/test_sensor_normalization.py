from datetime import datetime, timedelta, timezone

from services.sensor_analytics import build_distance_summary, build_sensor_payload, build_sensor_summary, compute_sensor_metrics, empty_sensor_metrics


class _Cursor:
    def __init__(self, recent_rows, daylight_rows):
        self.recent_rows = recent_rows
        self.daylight_rows = daylight_rows
        self.call_count = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.call_count += 1

    def fetchall(self):
        if self.call_count == 1:
            return self.recent_rows
        return self.daylight_rows


class _Conn:
    def __init__(self, recent_rows, daylight_rows):
        self.recent_rows = recent_rows
        self.daylight_rows = daylight_rows

    def cursor(self):
        return _Cursor(self.recent_rows, self.daylight_rows)


def test_build_sensor_payload_adds_0_to_100_normalized_values() -> None:
    merged = build_sensor_payload(
        {"light": 200.0, "water_level": 25.0, "distance": 40.0},
        None,
        metrics={
            "water_level_recent_avg_2h": 50.0,
            "water_level_sample_count": 4,
            "light_daytime_avg_13_18": 400.0,
            "light_daytime_sample_count": 8,
            "light_daytime_window_label": "13:00~18:00 KST",
        },
    )

    assert merged["light"] == 200.0
    assert merged["water_level"] == 25.0
    assert "light_raw" not in merged
    assert "water_level_raw" not in merged
    assert merged["light_normalized_0_100"] == 28
    assert merged["water_level_normalized_0_100"] == 50


def test_build_sensor_payload_clamps_values_and_allows_missing_reference() -> None:
    clamped = build_sensor_payload(
        {"light": 700.0, "water_level": 0.0, "distance": 40.0},
        None,
        metrics={
            "water_level_recent_avg_2h": 50.0,
            "water_level_sample_count": 4,
            "light_daytime_avg_13_18": 400.0,
            "light_daytime_sample_count": 8,
            "light_daytime_window_label": "13:00~18:00 KST",
        },
    )
    low = build_sensor_payload(
        {"light": 2.0, "water_level": 25.0, "distance": 40.0},
        None,
        metrics=empty_sensor_metrics(),
    )

    assert clamped["light_normalized_0_100"] == 100
    assert clamped["water_level_normalized_0_100"] == 0
    assert low["light_normalized_0_100"] == 0
    assert low["water_level_normalized_0_100"] is None


def test_compute_sensor_metrics_uses_recent_20_day_daylight_average() -> None:
    current = datetime(2026, 5, 21, 4, 0, tzinfo=timezone(timedelta(hours=9)))
    recent_rows = [
        {"created_at": current - timedelta(minutes=10), "payload": {"water_level": 20.0, "light": 14.0}, "sensor_type": "realtime"},
    ]
    daylight_rows = [
        {"created_at": datetime(2026, 5, 20, 14, 0, tzinfo=timezone(timedelta(hours=9))), "payload": {"light": 390.0}, "sensor_type": "realtime"},
        {"created_at": datetime(2026, 5, 19, 15, 0, tzinfo=timezone(timedelta(hours=9))), "payload": {"light": 410.0}, "sensor_type": "realtime"},
        {"created_at": datetime(2026, 4, 20, 10, 0, tzinfo=timezone(timedelta(hours=9))), "payload": {"light": 999.0}, "sensor_type": "realtime"},
    ]

    metrics = compute_sensor_metrics(_Conn(recent_rows, daylight_rows), current_time=current)

    assert metrics["water_level_recent_avg_2h"] == 20.0
    assert metrics["light_daytime_avg_13_18"] == 400.0
    assert metrics["light_daytime_sample_count"] == 2


def test_sensor_summary_excludes_distance_and_distance_summary_separates_it() -> None:
    summary = build_sensor_summary(
        {"temperature": 28.0, "humidity": 57.0, "light": 14.0, "water_level": 100.0, "distance": 42.0},
        {"level": "normal"},
        {"water_level_recent_avg_2h": 100.0, "light_daytime_avg_13_18": 400.0},
    )
    distance_summary = build_distance_summary(
        {"distance": 42.0},
        {"distance_detection_enabled": True, "wake_enabled": True, "distance_threshold_cm": 50.0, "distance_inside_threshold": False},
    )

    assert "거리" not in summary
    assert "42.0" not in summary
    assert "거리 센서는 환경 대화 모드" in distance_summary
    assert "42.0센티미터" in distance_summary



def test_sensor_summary_prefers_normalized_values_when_present() -> None:
    summary = build_sensor_summary(
        {
            "temperature": 27.0,
            "humidity": 57.0,
            "water_level": 199.0,
            "water_level_normalized_0_100": 73.0,
            "light": 765.0,
            "light_normalized_0_100": 28.0,
        },
        {"level": "normal"},
        {"water_level_recent_avg_2h": 80.0, "light_daytime_avg_13_18": 400.0},
    )

    assert "199.0" not in summary
    assert "765.0" not in summary
    assert "73.0%" in summary
    assert "28.0%" in summary
