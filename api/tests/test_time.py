from datetime import date

from app.core.time import IST, day_bounds_utc, day_counter, month_bounds_utc, prev_ym, ym_of


def test_day_bounds_ist_offset():
    s, e = day_bounds_utc(date(2026, 7, 15))
    assert s.isoformat() == "2026-07-14T18:30:00+00:00"  # IST = UTC+5:30
    assert (e - s).total_seconds() == 86400


def test_month_bounds():
    s, e = month_bounds_utc("2026-07")
    assert s.astimezone(IST).day == 1
    assert e.astimezone(IST).month == 8
    sd, ed = month_bounds_utc("2026-12")
    assert ed.astimezone(IST).year == 2027


def test_prev_ym_and_ym():
    assert prev_ym(date(2026, 7, 1)) == "2026-06"
    assert prev_ym(date(2026, 1, 3)) == "2025-12"
    assert ym_of(date(2026, 7, 15)) == "2026-07"


def test_day_counter_anchor_is_day_one():
    assert day_counter(date(2026, 7, 15), date(2026, 7, 15)) == 1
    assert day_counter(date(2026, 7, 15), date(2026, 10, 6)) == 84
