"""
أداة تُشغَّل مرّة واحدة على جهازك لتوليد YT_REFRESH_TOKEN (رمز الرفع الدائم).

قبلها:
  1) من Google Cloud Console فعّل "YouTube Data API v3".
  2) أنشئ "OAuth client ID" نوع Desktop، وخذ client_id و client_secret.
  3) ثبّت: pip install google-auth-oauthlib

التشغيل:
  YT_CLIENT_ID=... YT_CLIENT_SECRET=... python src/get_youtube_token.py

انسخ refresh_token الظاهر وضعه في GitHub Secrets باسم YT_REFRESH_TOKEN
(مع YT_CLIENT_ID و YT_CLIENT_SECRET).
"""

import os

from google_auth_oauthlib.flow import InstalledAppFlow

CLIENT_ID = os.environ["YT_CLIENT_ID"]
CLIENT_SECRET = os.environ["YT_CLIENT_SECRET"]

config = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
}

flow = InstalledAppFlow.from_client_config(
    config, scopes=["https://www.googleapis.com/auth/youtube.upload"]
)
creds = flow.run_local_server(port=0)
print("\n==== انسخ هذا السطر إلى GitHub Secret باسم YT_REFRESH_TOKEN ====")
print(creds.refresh_token)
