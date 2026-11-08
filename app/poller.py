"""Gmail -> parse -> extract -> store -> WhatsApp.

Usage:
  python -m app.poller --eml samples/order.eml --dry-run   # offline test with a file
  python -m app.poller --once                                # one Gmail pass
  python -m app.poller                                       # loop forever
"""
from __future__ import annotations

import argparse
import logging
import re
import time

from . import push, whatsapp
from .config import Settings
from .eml_parser import parse_bytes, parse_file, ParsedEmail
from .extractor import extract_items
from .store import Store

log = logging.getLogger("poller")


def process(email: ParsedEmail, msg_id: str, store: Store, s: Settings, dry_run: bool) -> str | None:
    if store.exists(msg_id):
        log.info("skip (already stored): %s", email.subject)
        return None
    items = extract_items(email)
    if not items:
        log.warning("no items found in %r — check extractor rules", email.subject)
        return None
    title = re.sub(r"^\s*((fwd?|fw|re|הועבר)\s*:\s*)+", "", email.subject, flags=re.I).strip() or email.subject
    token = store.create(msg_id, title, email.sender, items)
    link = f"{s.base_url}/l/{token}"
    log.info("created %d-item list %r -> %s", len(items), title, link)
    if dry_run or not (s.wa_token and s.wa_phone_id and s.wa_to):
        print("[WhatsApp preview]", whatsapp.preview(title, len(items), link, s.wa_lang))
    else:
        try:
            whatsapp.send(s, title, len(items), link)
        except Exception:
            log.exception("WhatsApp send failed (checklist was still created)")
    if not dry_run:
        n = push.notify_all(s, store, title, f"{len(items)} עבודות חדשות", f"/l/{token}")
        log.info("push notifications sent: %d", n)
    return token


def run_gmail_once(store: Store, s: Settings, dry_run: bool) -> None:
    from .gmail_source import Gmail

    gm = Gmail(s)
    for gid, raw in gm.fetch_new():
        email = parse_bytes(raw)
        process(email, email.message_id or gid, store, s, dry_run)
        if not dry_run:
            gm.mark_processed(gid)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("--eml", nargs="*", help="process local .eml files instead of Gmail")
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="don't send WhatsApp or label mail")
    a = ap.parse_args()

    s = Settings()
    store = Store(s.db_path)

    if a.eml:
        for path in a.eml:
            email = parse_file(path)
            process(email, email.message_id or path, store, s, a.dry_run)
        return

    while True:
        try:
            run_gmail_once(store, s, a.dry_run)
        except Exception:
            log.exception("poll failed")
        if a.once:
            return
        time.sleep(s.poll_seconds)


if __name__ == "__main__":
    main()
