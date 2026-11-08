"""Parse raw RFC 822 / .eml bytes into the parts we care about."""
from __future__ import annotations

from dataclasses import dataclass
from email import policy
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from pathlib import Path


@dataclass
class ParsedEmail:
    message_id: str
    subject: str
    sender: str
    date: str
    html: str
    text: str


def parse_bytes(raw: bytes) -> ParsedEmail:
    msg = BytesParser(policy=policy.default).parsebytes(raw)

    html_part = msg.get_body(preferencelist=("html",))
    text_part = msg.get_body(preferencelist=("plain",))

    date = ""
    if msg["Date"]:
        try:
            date = parsedate_to_datetime(msg["Date"]).isoformat()
        except (TypeError, ValueError):
            date = str(msg["Date"])

    return ParsedEmail(
        message_id=str(msg["Message-ID"] or "").strip("<> "),
        subject=str(msg["Subject"] or "(no subject)"),
        sender=str(msg["From"] or ""),
        date=date,
        html=html_part.get_content() if html_part else "",
        text=text_part.get_content() if text_part else "",
    )


def parse_file(path: str | Path) -> ParsedEmail:
    return parse_bytes(Path(path).read_bytes())
