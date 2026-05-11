from pathlib import Path
import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def fixture():
    def _load(name: str) -> str:
        return (FIXTURE_DIR / name).read_text()
    return _load
