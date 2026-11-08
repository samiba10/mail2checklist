# mail2checklist

Gmail email → checklist web page → WhatsApp alert with a link to it.

## Quick start (offline)
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/pytest -q
.venv/bin/python -m app.poller --eml samples/example_order.eml --dry-run
.venv/bin/uvicorn app.web:app --port 8000   # open the printed link
```

## Going live
1. `cp .env.example .env` and fill it in.
2. **Gmail**: Google Cloud Console → enable Gmail API → OAuth client (Desktop) → save as `credentials.json`.
   The first `python -m app.poller --once` opens a browser to sign in and saves `token.json`.
3. **WhatsApp**: Meta developer app → WhatsApp → copy the phone number ID and access token.
   Create a *Utility* template `new_checklist` with body `New list *{{1}}*: {{2}} items. Open: {{3}}`.
4. Deploy the web app somewhere public (set `BASE_URL`), and run `python -m app.poller` next to it.

## Adapting to your email layout
Put your real emails (Gmail → ⋮ → *Download message*) in `samples/`, then adjust
`app/extractor.py` (column names in `ITEM_HEADERS` / `QTY_HEADERS` / `NOTE_HEADERS`) and add a test.
