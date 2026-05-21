import pytest
from pathlib import Path

@pytest.fixture
def sample_text():
    return "hello world"

@pytest.fixture
def temp_output(tmp_path):
    return tmp_path / "output.md"
