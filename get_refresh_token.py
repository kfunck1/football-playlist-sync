import json, sys
from google_auth_oauthlib.flow import InstalledAppFlow
SCOPES = ["https://www.googleapis.com/auth/youtube"]
flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
if not creds.refresh_token:
    sys.exit("No refresh token. Revoke at https://myaccount.google.com/permissions and retry.")
d = json.load(open("client_secret.json"))
i = d.get("installed") or d.get("web") or {}
print("\n" + "=" * 62)
print("YT_CLIENT_ID      =", i.get("client_id"))
print("YT_CLIENT_SECRET  =", i.get("client_secret"))
print("YT_REFRESH_TOKEN  =", creds.refresh_token)
print("=" * 62)
