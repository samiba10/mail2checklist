"""Home-screen app (PWA): routes, key protection, push subscription and real Web Push encryption."""
import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from fastapi.testclient import TestClient

import app.web as web
from app import push
from app.config import Settings
from app.store import Store

SUB = {"endpoint": "https://push.example.com/abc", "keys": {"p256dh": "x", "auth": "y"}}


@pytest.fixture
def client(tmp_path):
    web.store = Store(str(tmp_path / "w.db"))
    web.settings.app_key = "k3y"
    web.settings.vapid_public_key = "PUB"
    return TestClient(web.app)


def test_health_and_no_public_index(client):
    assert client.get("/healthz").json() == {"ok": True}
    assert client.get("/").status_code == 404


def test_app_requires_key(client):
    assert client.get("/app/wrong").status_code == 404
    assert client.get("/app/wrong/manifest.webmanifest").status_code == 404
    assert client.post("/app/wrong/subscribe", json=SUB).status_code == 404
    web.settings.app_key = ""
    assert client.get("/app/").status_code == 404  # disabled when APP_KEY unset


def test_app_page_and_manifest(client):
    r = client.get("/app/k3y")
    assert r.status_code == 200 and 'rel="manifest"' in r.text and "apple-touch-icon" in r.text
    assert r.headers["x-robots-tag"].startswith("noindex")
    m = client.get("/app/k3y/manifest.webmanifest").json()
    assert m["start_url"] == "/app/k3y" and m["display"] == "standalone" and m["dir"] == "rtl"
    for icon in m["icons"]:
        assert client.get(icon["src"]).status_code == 200


def test_service_worker_served_from_root(client):
    r = client.get("/sw.js")
    assert r.status_code == 200 and "javascript" in r.headers["content-type"]
    assert r.headers["service-worker-allowed"] == "/"


def test_subscribe_validates_and_stores(client):
    assert client.post("/app/k3y/subscribe", json={"endpoint": "http://insecure"}).status_code == 400
    assert client.post("/app/k3y/subscribe", json=SUB).json() == {"ok": True}
    client.post("/app/k3y/subscribe", json=SUB)  # same device again: no duplicate
    assert [e for e, _ in web.store.push_subscriptions()] == [SUB["endpoint"]]
    client.post("/app/k3y/unsubscribe", json={"endpoint": SUB["endpoint"]})
    assert web.store.push_subscriptions() == []


class _FakePushService(BaseHTTPRequestHandler):
    received: list = []
    status = 201

    def do_POST(self):
        body = self.rfile.read(int(self.headers["Content-Length"]))
        _FakePushService.received.append(({k.lower(): v for k, v in self.headers.items()}, body))
        self.send_response(_FakePushService.status)
        self.end_headers()

    def log_message(self, *a):
        pass


def test_web_push_is_encrypted_and_decryptable(tmp_path):
    """Send through pywebpush to a local push service, then decrypt like a browser would."""
    import http_ece
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    import os

    srv = HTTPServer(("127.0.0.1", 0), _FakePushService)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    endpoint = f"http://127.0.0.1:{srv.server_port}/push/device1"

    # the "browser": its own key pair + auth secret
    device_key = ec.generate_private_key(ec.SECP256R1())
    p256dh = device_key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    auth = os.urandom(16)
    b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()

    store = Store(str(tmp_path / "p.db"))
    store.add_push_subscription({"endpoint": endpoint, "keys": {"p256dh": b64(p256dh), "auth": b64(auth)}})
    priv, pub = push.generate_keys()
    s = Settings(vapid_private_key=priv, vapid_public_key=pub, vapid_subject="mailto:test@example.com")

    _FakePushService.received.clear(); _FakePushService.status = 201
    assert push.notify_all(s, store, "רשימה חדשה", "7 עבודות חדשות", "/l/abc") == 1
    headers, body = _FakePushService.received[0]
    assert headers["content-encoding"] == "aes128gcm"
    assert headers["authorization"].startswith("vapid t=") and f"k={pub}" in headers["authorization"]
    plain = http_ece.decrypt(body, private_key=device_key, auth_secret=auth, version="aes128gcm")
    assert json.loads(plain) == {"title": "רשימה חדשה", "body": "7 עבודות חדשות", "url": "/l/abc"}

    # device removed the app -> push service answers 410 -> subscription is dropped
    _FakePushService.status = 410
    assert push.notify_all(s, store, "t", "b", "/l/x") == 0
    assert store.push_subscriptions() == []
    srv.shutdown()


def test_push_disabled_without_keys(tmp_path):
    store = Store(str(tmp_path / "n.db"))
    store.add_push_subscription(SUB)
    assert push.notify_all(Settings(vapid_private_key="", vapid_public_key=""), store, "t", "b", "/") == 0
