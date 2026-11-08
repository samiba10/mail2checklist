"""Turn a fixed-layout email into checklist items.

Default rules (adjust to your real layout once you have sample .eml files):
  1. HTML: the first <table> whose header row contains a column named like ITEM_HEADERS.
     Optional QTY_HEADERS / NOTE_HEADERS columns are picked up too.
  2. HTML fallback: <li> elements.
  3. Plain-text fallback: lines starting with "-", "*", "•" or "1." etc.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from bs4 import BeautifulSoup

from .eml_parser import ParsedEmail

ITEM_HEADERS = {"item", "items", "product", "description", "name", "task"}
QTY_HEADERS = {"qty", "quantity", "amount", "count"}
NOTE_HEADERS = {"note", "notes", "comment", "remarks"}

_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+(.+?)\s*$")


@dataclass
class Item:
    name: str
    qty: str = ""
    note: str = ""

    def label(self) -> str:
        s = f"{self.qty} × {self.name}" if self.qty else self.name
        return f"{s} ({self.note})" if self.note else s


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _from_table(soup: BeautifulSoup) -> list[Item]:
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [_clean(c.get_text()).lower() for c in rows[0].find_all(["th", "td"])]

        def col(names: set[str]) -> int | None:
            return next((i for i, h in enumerate(headers) if h in names), None)

        i_item, i_qty, i_note = col(ITEM_HEADERS), col(QTY_HEADERS), col(NOTE_HEADERS)
        if i_item is None:
            continue

        items = []
        for row in rows[1:]:
            cells = [_clean(c.get_text()) for c in row.find_all(["td", "th"])]
            if i_item >= len(cells) or not cells[i_item]:
                continue
            get = lambda i: cells[i] if i is not None and i < len(cells) else ""
            items.append(Item(cells[i_item], get(i_qty), get(i_note)))
        if items:
            return items
    return []


def extract_items(email: ParsedEmail) -> list[Item]:
    if email.html:
        soup = BeautifulSoup(email.html, "html.parser")
        items = _from_table(soup)
        if items:
            return items
        lis = [_clean(li.get_text()) for li in soup.find_all("li")]
        if lis := [x for x in lis if x]:
            return [Item(x) for x in lis]

    return [Item(m.group(1)) for line in email.text.splitlines() if (m := _BULLET.match(line))]
