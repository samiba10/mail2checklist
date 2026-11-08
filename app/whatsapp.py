"""Send a WhatsApp alert via the Meta WhatsApp Cloud API.

The bot normally starts the conversation, so Meta requires a pre-approved *template*.
Create one in WhatsApp Manager (category: Utility), e.g. named `new_checklist`, body:
    English (WA_LANG=en):  New list *{{1}}*: {{2}} items. Open: {{3}}
    Hebrew  (WA_LANG=he):  רשימה חדשה *{{1}}*: {{2}} עבודות. לפתיחה: {{3}}
"""
from __future__ import annotations

import httpx

from .config import Settings

GRAPH = "https://graph.facebook.com/v21.0"


def build_payload(s: Settings, to: str, title: str, count: int, link: str) -> dict:
    return {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": s.wa_template,
            "language": {"code": s.wa_lang},
            "components": [{
                "type": "body",
                "parameters": [
                    {"type": "text", "text": title[:60]},
                    {"type": "text", "text": str(count)},
                    {"type": "text", "text": link},
                ],
            }],
        },
    }


PREVIEW = {
    "en": "New list *{t}*: {n} items. Open: {l}",
    "he": "רשימה חדשה *{t}*: {n} עבודות. לפתיחה: {l}",
}


def preview(title: str, count: int, link: str, lang: str = "en") -> str:
    """What the template message will look like (used for --dry-run)."""
    return PREVIEW.get(lang, PREVIEW["en"]).format(t=title, n=count, l=link)


def send(s: Settings, title: str, count: int, link: str) -> None:
    for to in s.wa_to:
        r = httpx.post(
            f"{GRAPH}/{s.wa_phone_id}/messages",
            headers={"Authorization": f"Bearer {s.wa_token}"},
            json=build_payload(s, to, title, count, link),
            timeout=20,
        )
        r.raise_for_status()
