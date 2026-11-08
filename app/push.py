"""Web Push notifications for the home-screen app (iOS 16.4+, Android, desktop).

One-time setup — generate a VAPID key pair and store both values as secrets:
    python -m app.push --gen-keys
"""
from __future__ import annotations

import argparse
import base64
import json
import logging

from .config import Settings
from .store import Store

log = logging.getLogger("push")


def enabled(s: Settings) -> bool:
    return bool(s.vapid_private_key and s.vapid_public_key)


def notify_all(s: Settings, store: Store, title: str, body: str, url: str) -> int:
    """Send to every subscribed device. Returns how many succeeded; drops expired subscriptions."""
    if not enabled(s):
        return 0
    from pywebpush import WebPushException, webpush

    payload = json.dumps({"title": title, "body": body, "url": url}, ensure_ascii=False)
    sent = 0
    for endpoint, sub in store.push_subscriptions():
        try:
            webpush(
                subscription_info=sub,
                data=payload,
                vapid_private_key=s.vapid_private_key,
                vapid_claims={"sub": s.vapid_subject},
                ttl=24 * 3600,
            )
            sent += 1
        except WebPushException as e:
            status = getattr(e.response, "status_code", None)
            if status in (404, 410):  # device unsubscribed / app removed
                store.remove_push_subscription(endpoint)
                log.info("removed expired push subscription")
            else:
                log.warning("push failed (%s): %s", status, e)
    return sent


def generate_keys() -> tuple[str, str]:
    """Return (private_key, public_key), both base64url, ready for env vars."""
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec

    key = ec.generate_private_key(ec.SECP256R1())
    priv = key.private_numbers().private_value.to_bytes(32, "big")
    pub = key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    b64 = lambda b: base64.urlsafe_b64encode(b).rstrip(b"=").decode()
    return b64(priv), b64(pub)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen-keys", action="store_true")
    if ap.parse_args().gen_keys:
        priv, pub = generate_keys()
        print(f"VAPID_PRIVATE_KEY={priv}\nVAPID_PUBLIC_KEY={pub}")


if __name__ == "__main__":
    main()
