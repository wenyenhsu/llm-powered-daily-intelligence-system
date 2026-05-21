from src.clean_up import *


def test_normalize_target():
    assert normalize_target("folder/Name|alias") == "name"

def test_clean_text_removes_bad_links():
    text = "hello [[badnode]] world"
    result = clean_text(text)
    assert isinstance(result, str)