#!/usr/bin/env python3
"""
One-time helper: obtain a YouTube refresh token for the sync workflow.

Run this ONCE on your own machine (not in CI). It opens a browser, you approve
access, and it prints the refresh token to paste into GitHub Secrets.

    pip install google-auth-oauthlib
    python get_refresh_token.py
"""
import json
import os
import sys
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube"]
SECRETS = "client_secret.json"

if not os.path.exists(SECRETS):
    sys.exit(
        f"Put your OAuth client file here as {SECRETS}.\n"
        "Google Cloud Console -> APIs & Services -> Credentials ->\n"
        "Create Credentials -> OAuth client ID -> Desktop app -> Download JSON."
    )

flow = InstalledAppFlow.from_client_secrets_file(SECRETS, SCOPES)
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

if not creds.refresh_token:
    sys.exit("No refresh token returned. Delete any prior grant at "
             "https://myaccount.google.com/permissions and run this again.")

with open(SECRETS) as fh:
    data = json.load(fh)
installed = data.get("installed") or data.get("web") or {}

print("\n" + "=" * 62)
print("Add these three as GitHub repository secrets:\n")
print("YT_CLIENT_ID      =", installed.get("client_id", "<from client_secret.json>"))
print("YT_CLIENT_SECRET  =", installed.get("client_secret", "<from client_secret.json>"))
print("YT_REFRESH_TOKEN  =", creds.refresh_token)
print("=" * 62)
print("\nAlso add YT_TARGET_PLAYLIST = the ID of the playlist to fill")
print("(the list= value from its URL).")
