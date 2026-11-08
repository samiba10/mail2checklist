"""Checklist web app.  Run:  uvicorn app.web:app --host 0.0.0.0 --port 8000"""
from __future__ import annotations

import re
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .config import Settings
from .store import Store

settings = Settings()
store = Store(settings.db_path)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app = FastAPI(title="mail2checklist")


@app.get("/healthz")
def healthz():
    store.db.execute("SELECT 1")
    return {"ok": True}


@app.middleware("http")
async def no_index(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"  # customer data: keep out of search engines
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


@app.get("/", response_class=HTMLResponse)
def index(request: Request, key: str = ""):
    # The overview lists every checklist, so it needs ADMIN_KEY (/?key=...). Unset = disabled.
    if not settings.admin_key or not secrets.compare_digest(key, settings.admin_key):
        raise HTTPException(404)
    return templates.TemplateResponse(request, "index.html", {"lists": store.recent()})


@app.get("/l/{token}", response_class=HTMLResponse)
def checklist(request: Request, token: str):
    lst, items = store.get(token)
    if lst is None:
        raise HTTPException(404, "Checklist not found")
    rtl = bool(re.search(r"[\u0590-\u06FF]", lst["title"]))  # Hebrew / Arabic
    return templates.TemplateResponse(request, "list.html", {"lst": lst, "items": items, "rtl": rtl})


@app.post("/l/{token}/items/{item_id}/toggle")
def toggle(token: str, item_id: int):
    done = store.toggle(token, item_id)
    if done is None:
        raise HTTPException(404, "Item not found")
    return {"id": item_id, "done": done}
