# Setup requirements: Gmail → WhatsApp

Everything needed to run **Gmail → WhatsApp** with the current code. The home-screen app and push
notifications are optional and not covered here (see the README).

## Where each part runs

| Part | Runs on | When |
|---|---|---|
| **The app** (checks Gmail, builds the list, sends WhatsApp, serves the list page) | **Fly.io server**, Frankfurt | 24/7 |
| **Database** (lists and ticks) | Fly.io storage disk (1 GB) | 24/7 |
| **Gmail** | Google, the technician's account | Already exists |
| **WhatsApp sending** | Meta's servers (WhatsApp Cloud API) | When a list arrives |
| **One-time setup** (Gmail sign-in, deploy commands) | **Your computer** (Windows, Mac or Linux) | Once, about 1 hour |
| **Reading the list** | **Technician's phone**: WhatsApp, then tap the link to open it in the browser | Daily use |

```
 Gmail ──► Fly.io server (24/7) ──► WhatsApp message with link
            • checks Gmail every 3 min
            • reads the table, builds the checklist
            • stores ticks (database)
            • serves the list page ◄──── technician taps the link
```

## Accounts to create

| # | Account | Sign up at | Cost |
|---|---|---|---|
| 1 | **Fly.io** | <https://fly.io> (credit card required) | about $2–3 a month |
| 2 | **Google Cloud** project, using **the Gmail account that receives the lists** | <https://console.cloud.google.com> | Free |
| 3 | **Meta for Developers** and a **Meta Business** account | <https://developers.facebook.com> | Free to set up; a few cents per message |
| 4 | **Phone number for sending** WhatsApp (can't be in use on WhatsApp already) | Meta gives a free test number, or use a spare number | Free, or the cost of a SIM |
| 5 | **GitHub** (code) | <https://github.com/samiba10/mail2checklist> | Free |

## Software for your computer (one time)

| Tool | Why |
|---|---|
| **Git** | Download the code |
| **Python 3.12+** | Run the Gmail sign-in (`python -m app.gmail_auth`) |
| **flyctl** | Deploy to Fly.io: `curl -L https://fly.io/install.sh \| sh` |
| **A browser** | Google sign-in and the Meta dashboard |

## Values to collect, in order

| # | Value | From | Becomes |
|---|---|---|---|
| 1 | `credentials.json` | Google Cloud → Credentials → OAuth client (Desktop) | Used once on your computer |
| 2 | `token.json` | Created by `python -m app.gmail_auth` after signing in to the receiving Gmail account | `GMAIL_TOKEN_JSON` |
| 3 | Phone number ID | Meta → WhatsApp → API setup | `WA_PHONE_ID` |
| 4 | **Permanent** access token | Meta Business Settings → System users → Generate token (`whatsapp_business_messaging`) | `WA_TOKEN` |
| 5 | Approved template `new_checklist` (Hebrew, Utility) | WhatsApp Manager → Message templates | `WA_TEMPLATE` (already set in `fly.toml`) |
| 6 | Technician's mobile number (`05X-XXXXXXX` is fine) | You | `WA_TO` |
| 7 | App address `https://<name>.fly.dev` | Fly.io, after `fly launch` | `BASE_URL` |
| 8 | Gmail filter | Sender domain and subject of the list emails | `GMAIL_QUERY`, e.g. `from:<sender-domain> subject:"רשימת לקוחות" -label:processed` |

Template body (Hebrew):

```
רשימה חדשה *{{1}}*: {{2}} עבודות. לפתיחה: {{3}}
```

## Easy to miss

- [ ] **Google: click "Publish app"** on the OAuth consent screen. Without it, the Gmail login stops working after 7 days.
- [ ] **Meta: use a *permanent* token** from System users. The one on the API setup page expires in 24 hours.
- [ ] **Meta test mode:** add the technician's number as an allowed recipient, or the messages won't arrive.
- [ ] **Template approval** takes from minutes up to a day. Submit it first, then do the rest while you wait.
- [ ] **Technician's phone** only needs WhatsApp; no app to install.

## Deploy

```bash
git clone https://github.com/samiba10/mail2checklist && cd mail2checklist
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m app.gmail_auth          # browser opens: sign in to the receiving Gmail account
```

Set a unique `app = "..."` name in `fly.toml`, then:

```bash
fly auth login
fly launch --no-deploy --copy-config
fly volumes create m2c_data --size 1 --region fra
fly secrets set \
  BASE_URL="https://<your-app>.fly.dev" \
  GMAIL_QUERY='from:<sender-domain> subject:"רשימת לקוחות" -label:processed' \
  GMAIL_TOKEN_JSON="$(cat token.json)" \
  WA_TOKEN="<permanent token>" \
  WA_PHONE_ID="<phone number id>" \
  WA_TO="<technician's number>"
fly deploy
```

Check that it works:

- `https://<your-app>.fly.dev/healthz` shows `{"ok": true}`
- `fly logs` shows the poller running every 3 minutes
- Forward a list email to the Gmail account: a WhatsApp message arrives within about 3 minutes

## Not needed for this setup

`APP_KEY`, the `VAPID_*` keys, the home-screen app, an Apple Developer account and a Mac.

## Monthly cost

About **$2–3** for Fly.io, plus **a few cents** for each WhatsApp message.
