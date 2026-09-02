from src.profile import load_profile


def test_load_example_profile():
    profile = load_profile("profile.example.yaml")
    assert profile.location.residence == "서울특별시"
    assert "행복주택" in profile.interests.housing_types
    assert profile.income.monthly_gross_krw == 2900000
