"""One-time Gmail sign-in. Run on your own computer (it opens a browser):

    python -m app.gmail_auth

Sign in with the Gmail account that receives the lists. This writes token.json;
for a server, copy its content into the GMAIL_TOKEN_JSON secret.
"""
from __future__ import annotations

from pathlib import Path

from .config import Settings
from .gmail_source import _service


def main() -> None:
    s = Settings()
    svc = _service(s, allow_browser=True)
    email = svc.users().getProfile(userId="me").execute()["emailAddress"]
    print(f"Signed in as {email}. Token saved to {Path(s.gmail_token).resolve()}")
    print("Server secret:  fly secrets set GMAIL_TOKEN_JSON=\"$(cat token.json)\"")


if __name__ == "__main__":
    main()
