"""
رفع الفيديو إلى يوتيوب عبر YouTube Data API v3 (الخطوة الثانية — بعد أن تتأكد من جودة الفيديو).

يحتاج ثلاثة أسرار بيئية (GitHub Secrets):
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
تُولَّد مرة واحدة محليًا (انظر README). الرفع بعدها بلا تدخّل.
"""

import os


def upload(video_path, title, description, tags):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        scopes=["https://www.googleapis.com/auth/youtube.upload"],
    )
    youtube = build("youtube", "v3", credentials=creds)

    body = {
        "snippet": {
            "title": title[:95],
            "description": description[:4900],
            "tags": tags[:15],
            "categoryId": "28",  # العلوم والتقنية
        },
        "status": {"privacyStatus": "private", "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
    req = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = req.execute()
    print(f"[youtube] رُفع الفيديو: https://youtu.be/{resp['id']} (خاص — راجعه ثم انشره)")
    return resp["id"]
