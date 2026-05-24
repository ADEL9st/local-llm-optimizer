from doctor.diagnosis.scoring import max_ratio, metric_values, summarize, to_float


def test_to_float_handles_missing_and_numeric_values():
    assert to_float(None) is None
    assert to_float("") is None
    assert to_float("not-a-number") is None
    assert to_float("42.5") == 42.5
    assert to_float(7) == 7.0


def test_metric_values_skips_bad_rows():
    rows = [
        {"gpu_util_percent": "5"},
        {"gpu_util_percent": None},
        {"gpu_util_percent": "bad"},
        {"gpu_util_percent": 10},
    ]

    assert metric_values(rows, "gpu_util_percent") == [5.0, 10.0]


def test_summarize_returns_avg_max_min():
    rows = [
        {"ram_percent": 80},
        {"ram_percent": 90},
        {"ram_percent": 100},
    ]

    assert summarize(rows, "ram_percent") == {
        "avg": 90,
        "max": 100,
        "min": 80,
    }


def test_max_ratio_uses_peak_values():
    assert max_ratio([100, 250], [1000]) == 25.0
    assert max_ratio([], [1000]) is None
    assert max_ratio([100], [0]) is None
