from src.generate_reports import parse_date, build_custom_window

def test_parse_date():
    assert parse_date("2026-05-20").isoformat() == "2026-05-20"