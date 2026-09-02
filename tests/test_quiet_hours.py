from datetime import time

from src.quiet_hours import is_quiet_now


def test_normal_range():
    assert is_quiet_now("09:00-18:00", now=time(12, 0)) is True
    assert is_quiet_now("09:00-18:00", now=time(20, 0)) is False


def test_overnight_range():
    assert is_quiet_now("23:00-08:00", now=time(23, 30)) is True
    assert is_quiet_now("23:00-08:00", now=time(3, 0)) is True
    assert is_quiet_now("23:00-08:00", now=time(12, 0)) is False


def test_none_means_never_quiet():
    assert is_quiet_now(None, now=time(3, 0)) is False
