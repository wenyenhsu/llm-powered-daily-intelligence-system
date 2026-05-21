from src.ranking import extract_links

def test_extract_links():
    text = "[[insights/topic1]] some text [[insights/topic2|alias]]"
    assert extract_links(text) == ["topic1", "topic2"]