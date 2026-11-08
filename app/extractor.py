"""Turn a fixed-layout email into checklist items.

Rules, tried in order:
  1. Job rows (installation-list emails): table rows with a cell starting with JOB_PREFIX.
     Columns shift between rows, so each field is recognised by its pattern, not position.
  2. HTML table whose header row has a column named like ITEM_HEADERS (+ optional qty/note).
  3. HTML <li> elements.
  4. Plain-text lines starting with "-", "*", "•" or "1." etc.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup, Tag

from .eml_parser import ParsedEmail

ITEM_HEADERS = {"item", "items", "product", "description", "name", "task"}
QTY_HEADERS = {"qty", "quantity", "amount", "count"}
NOTE_HEADERS = {"note", "notes", "comment", "remarks"}

JOB_PREFIX = "התקנת"  # "installation of ..."
_DATE = re.compile(r"^\d{1,2}/\d{1,2}/\d{4}$")
_ORDER = re.compile(r"^\d{7,10}$")
_PHONE = re.compile(r"^0\d{1,2}-?\d{7}$")
_ADDRESS = re.compile(r"^\d{1,7}\s+\S")           # starts with a postal code (or 0)
_HEATER = re.compile(r"\d{2}\s*\D+|\D+\s*\d{2}")    # "17 טורבו", "ליטר 20", "20ליטר"
_YELLOW = re.compile(r"yellow|#?ffff00", re.I)
_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+(.+?)\s*$")


@dataclass
class Item:
    name: str
    qty: str = ""
    note: str = ""
    phones: list[str] = field(default_factory=list)

    def label(self) -> str:
        s = f"{self.qty} × {self.name}" if self.qty else self.name
        return f"{s} ({self.note})" if self.note else s


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _is_yellow(cell: Tag) -> bool:
    styles = [cell.get("style") or "", str(cell.get("bgcolor") or "")]
    styles += [t.get("style") or "" for t in cell.find_all(style=True)]
    return any(_YELLOW.search(s) for s in styles)


def _from_job_rows(soup: BeautifulSoup) -> list[Item]:
    items = []
    for row in soup.find_all("tr"):
        cells = row.find_all(["td", "th"], recursive=False) or row.find_all(["td", "th"])
        texts = [_clean(c.get_text()) for c in cells]
        if not any(t.startswith(JOB_PREFIX) for t in texts):
            continue

        job = name = address = order = heater = ""
        dates, phones, rest = [], [], []
        for cell, t in zip(cells, texts):
            if not t:
                continue
            if t.startswith(JOB_PREFIX) and not job:
                job = t
            elif _DATE.match(t):
                dates.append(t)
            elif _PHONE.match(t):
                if t not in phones:
                    phones.append(t)
            elif _ORDER.match(t) and not order:
                order = t
            elif _ADDRESS.match(t) and not address:
                address = re.sub(r"^\d+\s+['\"\s]*", "", t)  # drop postal code + stray quotes
            elif not heater and (_is_yellow(cell) or _HEATER.fullmatch(t)):
                heater = t
            elif order and not name:
                name = t  # first free-text cell after the order number
            else:
                rest.append(t)

        if not (name or order):
            continue
        title = " – ".join(x for x in (name or f"#{order}", heater) if x)
        details = [address, job, f"#{order}" if order and name else "", dates[-1] if dates else "", *rest]
        items.append(Item(title, note=" · ".join(x for x in details if x), phones=phones))
    return items


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
        for rule in (_from_job_rows, _from_table):
            if items := rule(soup):
                return items
        lis = [_clean(li.get_text()) for li in soup.find_all("li")]
        if lis := [x for x in lis if x]:
            return [Item(x) for x in lis]

    return [Item(m.group(1)) for line in email.text.splitlines() if (m := _BULLET.match(line))]
