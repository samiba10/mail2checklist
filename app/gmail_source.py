"""Read raw messages from Gmail and label them once processed."""
from __future__ import annotations

import base64
from pathlib import Path

from .config import Settings

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]  # read + add labels


def _service(s: Settings):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if Path(s.gmail_token).exists():
        creds = Credentials.from_authorized_user_file(s.gmail_token, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # First run: opens a browser for Google sign-in, then caches token.json
            creds = InstalledAppFlow.from_client_secrets_file(s.gmail_credentials, SCOPES).run_local_server(port=0)
        Path(s.gmail_token).write_text(creds.to_json())
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


class Gmail:
    def __init__(self, s: Settings):
        self.s = s
        self.svc = _service(s)
        self._label_id = None

    def fetch_new(self):
        """Yield (gmail_id, raw_bytes) for messages matching the query."""
        req = self.svc.users().messages().list(userId="me", q=self.s.gmail_query, maxResults=50)
        while req is not None:
            resp = req.execute()
            for m in resp.get("messages", []):
                full = self.svc.users().messages().get(userId="me", id=m["id"], format="raw").execute()
                yield m["id"], base64.urlsafe_b64decode(full["raw"])
            req = self.svc.users().messages().list_next(req, resp)

    def _processed_label(self) -> str:
        if self._label_id is None:
            labels = self.svc.users().labels().list(userId="me").execute().get("labels", [])
            match = next((l for l in labels if l["name"] == self.s.gmail_processed_label), None)
            if match is None:
                match = self.svc.users().labels().create(
                    userId="me", body={"name": self.s.gmail_processed_label}
                ).execute()
            self._label_id = match["id"]
        return self._label_id

    def mark_processed(self, gmail_id: str) -> None:
        self.svc.users().messages().modify(
            userId="me", id=gmail_id, body={"addLabelIds": [self._processed_label()]}
        ).execute()
