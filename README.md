# mail2checklist

Gmail email → checklist web page → WhatsApp alert with a link to it.

One container runs both parts: the **web app** (checklist pages) and the **poller**
(checks Gmail every few minutes, creates the checklist, sends the WhatsApp message).

## Quick start (offline)
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest -q
.venv/bin/python -m app.poller --eml samples/example_installs.eml --dry-run
.venv/bin/uvicorn app.web:app --port 8000   # open the printed link
```

## 1. Gmail access (one time, on your computer)
1. [Google Cloud Console](https://console.cloud.google.com/) → new project → **APIs & Services → Enable APIs** → *Gmail API*.
2. **OAuth consent screen** → External → add the Gmail account that receives the lists as a test user.
   Then click **Publish app** (status *In production*). In *Testing* status Google expires the
   login after 7 days and the poller stops. Google will warn "unverified app" on sign-in; that is
   fine for your own account.
3. **Credentials → Create OAuth client ID → Desktop app** → download as `credentials.json` in this folder.
4. Sign in (opens a browser; use the Gmail account that receives the lists):
   ```bash
   .venv/bin/python -m app.gmail_auth
   ```
   This creates `token.json`. Never commit it (it is git-ignored).

## 2. WhatsApp (Meta)
1. [developers.facebook.com](https://developers.facebook.com/) → create app → add **WhatsApp**.
   Note the **Phone number ID**.
2. Create a **permanent** access token: Business Settings → System users → add → *Generate token*
   with `whatsapp_business_messaging`. (The token shown on the API setup page expires in 24 h.)
3. WhatsApp Manager → Message templates → new, category **Utility**, name `new_checklist`, language **Hebrew**:
   `רשימה חדשה *{{1}}*: {{2}} עבודות. לפתיחה: {{3}}`
4. While in test mode, add the recipient's number under *API setup → To*.

## 3. Deploy to Fly.io (recommended)
Fly keeps a small disk for the database and runs the poller around the clock (around $2–3/month for this size).

```bash
curl -L https://fly.io/install.sh | sh          # install flyctl
fly auth signup                                  # or: fly auth login
```
Edit `app = "..."` in `fly.toml` to a unique name, then:
```bash
fly launch --no-deploy --copy-config
fly volumes create m2c_data --size 1 --region fra
fly secrets set \
  BASE_URL="https://<your-app>.fly.dev" \
  GMAIL_QUERY='from:<sender-domain> subject:"רשימת לקוחות" -label:processed' \
  GMAIL_TOKEN_JSON="$(cat token.json)" \
  WA_TOKEN="<permanent token>" \
  WA_PHONE_ID="<phone number id>" \
  WA_TO="05X-XXXXXXX" \
  ADMIN_KEY="$(openssl rand -hex 16)"
fly deploy
fly logs                                         # watch the poller
```
Check: `https://<your-app>.fly.dev/healthz` → `{"ok": true}`.
Send a matching test email to the Gmail account; within `POLL_SECONDS` a WhatsApp message arrives.

## Alternative: any server with Docker
```bash
cp .env.example .env        # fill in, including GMAIL_TOKEN_JSON and BASE_URL
docker compose up -d --build
```
Put HTTPS in front of port 8000 (for example Caddy: `caddy reverse-proxy --from your.domain --to :8000`).

## Privacy
- Checklist links use random, unguessable tokens; pages send `noindex` so search engines skip them.
- The overview page `/` is disabled unless `ADMIN_KEY` is set, and then needs `/?key=<ADMIN_KEY>`.
- Real emails go in `samples/private/` (git-ignored and excluded from the Docker image).
  `.env`, `credentials.json`, `token.json` and the database are never committed.

## Configuration
All settings are environment variables. See `.env.example` for the full list.

## Adapting to another email layout
Put example emails (Gmail → ⋮ → *Download message*) in `samples/private/`, then adjust the rules in
`app/extractor.py` and add a test that checks counts/shapes only (no personal data in the repo).
