from src.profile import load_profile


def test_load_example_profile():
    profile = load_profile("profile.example.yaml")
    assert profile.interests.regions == ["서울특별시"]
    assert "행복주택" in profile.interests.housing_types
    assert profile.personal.birth_date.isoformat() == "1995-01-01"
    assert profile.notify.quiet_hours == "23:00-08:00"
