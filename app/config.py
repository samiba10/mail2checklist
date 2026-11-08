from __future__ import annotations

import os
import re
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


def normalize_phone(raw: str, country_code: str = "") -> str:
    """'052-123 4567' + '972' -> '972521234567'; '+972 52...' -> '97252...' (WhatsApp wants digits only)."""
    digits = re.sub(r"\D", "", raw)
    if country_code and digits.startswith("0") and not digits.startswith("00"):
        digits = country_code + digits[1:]
    return digits.removeprefix("00")


def _wa_to() -> list[str]:
    cc = os.getenv("WA_COUNTRY_CODE", "")
    return [normalize_phone(x, cc) for x in os.getenv("WA_TO", "").split(",") if x.strip()]


@dataclass
class Settings:
    db_path: str = field(default_factory=lambda: os.getenv("DB_PATH", "checklists.db"))
    base_url: str = field(default_factory=lambda: os.getenv("BASE_URL", "http://localhost:8000").rstrip("/"))
    gmail_query: str = field(default_factory=lambda: os.getenv("GMAIL_QUERY", "label:to-checklist -label:processed"))
    gmail_processed_label: str = field(default_factory=lambda: os.getenv("GMAIL_PROCESSED_LABEL", "processed"))
    gmail_credentials: str = field(default_factory=lambda: os.getenv("GMAIL_CREDENTIALS", "credentials.json"))
    gmail_token: str = field(default_factory=lambda: os.getenv("GMAIL_TOKEN", "token.json"))
    wa_token: str = field(default_factory=lambda: os.getenv("WA_TOKEN", ""))
    wa_phone_id: str = field(default_factory=lambda: os.getenv("WA_PHONE_ID", ""))
    wa_to: list[str] = field(default_factory=_wa_to)
    wa_template: str = field(default_factory=lambda: os.getenv("WA_TEMPLATE", "new_checklist"))
    wa_lang: str = field(default_factory=lambda: os.getenv("WA_LANG", "en"))
    # Secret part of the app URL /app/<APP_KEY> (Mahran's home-screen app). Unset = app disabled.
    app_key: str = field(default_factory=lambda: os.getenv("APP_KEY", ""))
    vapid_private_key: str = field(default_factory=lambda: os.getenv("VAPID_PRIVATE_KEY", ""))
    vapid_public_key: str = field(default_factory=lambda: os.getenv("VAPID_PUBLIC_KEY", ""))
    vapid_subject: str = field(default_factory=lambda: os.getenv("VAPID_SUBJECT", "mailto:admin@example.com"))
    poll_seconds: int = field(default_factory=lambda: int(os.getenv("POLL_SECONDS", "180")))
