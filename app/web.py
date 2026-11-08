"""Checklist web app + installable home-screen app (PWA).

Run:  uvicorn app.web:app --host 0.0.0.0 --port 8000

Routes
  /l/{token}                 one checklist (link sent on WhatsApp / push)
  /app/{APP_KEY}             the app: all lists, notification switch, install help
  /app/{APP_KEY}/manifest.webmanifest, /subscribe, /unsubscribe
  /sw.js                     service worker (offline + push)
"""
from __future__ import annotations

import re
import secrets
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .config import Settings
from .store import Store

HERE = Path(__file__).parent
settings = Settings()
store = Store(settings.db_path)
templates = Jinja2Templates(directory=str(HERE / "templates"))
app = FastAPI(title="mail2checklist", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=HERE / "static"), name="static")

_RTL = re.compile(r"[֐-ۿ]")  # Hebrew / Arabic


@app.middleware("http")
async def headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"  # customer data: keep out of search engines
    resp.headers["Referrer-Policy"] = "no-referrer"
    return resp


@app.get("/healthz")
def healthz():
    store.db.execute("SELECT 1")
    return {"ok": True}


@app.get("/sw.js")
def service_worker():
    # Served from the root so it can control /l/... and /app/... pages.
    return FileResponse(HERE / "static" / "sw.js", media_type="text/javascript",
                        headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})


# ---------- single checklist ----------

@app.get("/l/{token}", response_class=HTMLResponse)
def checklist(request: Request, token: str):
    lst, items = store.get(token)
    if lst is None:
        raise HTTPException(404, "Checklist not found")
    rtl = bool(_RTL.search(lst["title"]))
    return templates.TemplateResponse(request, "list.html", {"lst": lst, "items": items, "rtl": rtl})


@app.post("/l/{token}/items/{item_id}/toggle")
def toggle(token: str, item_id: int):
    done = store.toggle(token, item_id)
    if done is None:
        raise HTTPException(404, "Item not found")
    return {"id": item_id, "done": done}


# ---------- the app (needs APP_KEY) ----------

def _check_key(key: str) -> None:
    if not settings.app_key or not secrets.compare_digest(key, settings.app_key):
        raise HTTPException(404)


@app.get("/app/{key}", response_class=HTMLResponse)
def app_home(request: Request, key: str):
    _check_key(key)
    return templates.TemplateResponse(request, "app.html", {
        "lists": store.recent(),
        "key": key,
        "vapid_public_key": settings.vapid_public_key,
    })


@app.get("/app/{key}/manifest.webmanifest")
def manifest(key: str):
    _check_key(key)
    return JSONResponse({
        "name": "רשימות עבודה",
        "short_name": "רשימות",
        "lang": "he",
        "dir": "rtl",
        "start_url": f"/app/{key}",
        "scope": "/",
        "display": "standalone",
        "background_color": "#f6f7f9",
        "theme_color": "#128c7e",
        "icons": [
            {"src": "/static/icon-192.png", "sizes": "192x192", "type": "image/png"},
            {"src": "/static/icon-512.png", "sizes": "512x512", "type": "image/png"},
            {"src": "/static/icon-512-maskable.png", "sizes": "512x512", "type": "image/png", "purpose": "maskable"},
        ],
    }, media_type="application/manifest+json")


@app.post("/app/{key}/subscribe")
async def subscribe(key: str, request: Request):
    _check_key(key)
    sub = await request.json()
    if not isinstance(sub, dict) or not str(sub.get("endpoint", "")).startswith("https://") \
            or not isinstance(sub.get("keys"), dict):
        raise HTTPException(400, "invalid subscription")
    store.add_push_subscription({"endpoint": sub["endpoint"], "keys": sub["keys"]})
    return {"ok": True}


@app.post("/app/{key}/unsubscribe")
async def unsubscribe(key: str, request: Request):
    _check_key(key)
    body = await request.json()
    store.remove_push_subscription(str(body.get("endpoint", "")))
    return {"ok": True}
