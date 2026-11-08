from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.eml_parser import ParsedEmail, parse_file
from app.extractor import extract_items
from app.poller import process
from app.store import Store

SAMPLE = Path(__file__).parent.parent / "samples" / "example_order.eml"


def test_parse_eml():
    e = parse_file(SAMPLE)
    assert e.subject == "Order #1042 - items to pick"
    assert e.message_id == "order-1042@example.com"
    assert "<table>" in e.html and "Milk" in e.text


def test_extract_table():
    items = extract_items(parse_file(SAMPLE))
    assert [i.label() for i in items] == [
        "2 × Milk 2L (low fat)",
        "1 × Eggs (12)",
        "1 × Bread (whole wheat)",
    ]


def test_extract_text_fallback():
    e = ParsedEmail("x", "s", "f", "", "", "Intro\n- one\n* two\n3. three\nbye")
    assert [i.name for i in extract_items(e)] == ["one", "two", "three"]


def test_process_dedupes_and_toggles(tmp_path, capsys):
    s = Settings(db_path=str(tmp_path / "t.db"), wa_token="", wa_lang="en")
    store = Store(s.db_path)
    e = parse_file(SAMPLE)
    token = process(e, e.message_id, store, s, dry_run=True)
    assert token and "3 items" in capsys.readouterr().out
    assert process(e, e.message_id, store, s, dry_run=True) is None  # duplicate

    import app.web as web
    web.store = store
    client = TestClient(web.app)
    page = client.get(f"/l/{token}")
    assert page.status_code == 200 and "Milk 2L" in page.text
    _, items = store.get(token)
    r = client.post(f"/l/{token}/items/{items[0]['id']}/toggle")
    assert r.json()["done"] is True
    assert store.get(token)[1][0]["done"] == 1
    assert client.post(f"/l/wrong/items/{items[0]['id']}/toggle").status_code == 404


def test_admin_index_and_health(tmp_path):
    import app.web as web
    web.store = Store(str(tmp_path / "a.db"))
    c = TestClient(web.app)
    assert c.get("/healthz").json() == {"ok": True}
    web.settings.admin_key = ""
    assert c.get("/").status_code == 404                 # disabled without ADMIN_KEY
    web.settings.admin_key = "s3cret"
    assert c.get("/?key=wrong").status_code == 404
    r = c.get("/?key=s3cret")
    assert r.status_code == 200 and r.headers["x-robots-tag"].startswith("noindex")
