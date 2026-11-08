"""Installation-list layout (forwarded job rows, no header row, shifting columns)."""
import re
from pathlib import Path

import pytest

from app.eml_parser import parse_file
from app.extractor import extract_items

SAMPLES = Path(__file__).parent.parent / "samples"


def test_demo_installs():
    items = extract_items(parse_file(SAMPLES / "example_installs.eml"))
    assert [i.name for i in items] == ["ישראל ישראלי – 17טורבו", "דנה כהן – 20ליטר", "יוסי לוי – 17 מאולץ"]
    assert items[0].phones == ["050-0000001"]                 # duplicate phone collapsed
    assert items[1].phones == ["052-0000002", "052-0000003"]
    assert items[0].note.startswith("הרצל 1 תל אביב")        # postal code dropped
    assert "#450000003" in items[2].note and "טכנאי" in items[2].note


# Real email kept out of git (samples/private/ is ignored). Only shapes are asserted here,
# so no personal data ends up in the repository.
PRIVATE = SAMPLES / "private" / "installs.eml"


@pytest.mark.skipif(not PRIVATE.exists(), reason="private sample not present")
def test_private_installs_shape():
    items = extract_items(parse_file(PRIVATE))
    assert len(items) == 7
    for it in items:
        assert " – " in it.name                                  # name – heater
        assert it.phones and all(re.fullmatch(r"0\d{1,2}-\d{7}", p) for p in it.phones)
        assert re.search(r"#\d{7,10}", it.note)
        assert not re.match(r"^\W", it.note)                     # no stray quote / postal code
