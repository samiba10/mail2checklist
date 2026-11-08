from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


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
    wa_to: list[str] = field(default_factory=lambda: [x.strip() for x in os.getenv("WA_TO", "").split(",") if x.strip()])
    wa_template: str = field(default_factory=lambda: os.getenv("WA_TEMPLATE", "new_checklist"))
    wa_lang: str = field(default_factory=lambda: os.getenv("WA_LANG", "en"))
    poll_seconds: int = field(default_factory=lambda: int(os.getenv("POLL_SECONDS", "180")))
