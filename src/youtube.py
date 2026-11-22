"""
رفع الفيديو إلى يوتيوب عبر YouTube Data API v3.

يحتاج ثلاثة أسرار بيئية (GitHub Secrets):
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
تُولَّد مرة واحدة محليًا (انظر README). الرفع بعدها بلا تدخّل.

درجة الظهور تُضبط من config.json ← youtube.privacy:
  private  = خاص، لا يظهر في القناة (الافتراضي: تراجعه بنفسك أولًا)
  unlisted = لا يظهر في القناة لكن يفتح بالرابط
  public   = منشور للجميع فورًا
"""

import os

ALLOWED_PRIVACY = ("private", "unlisted", "public")


def upload(video_path, title, description, tags, cfg=None):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    yt = (cfg or {}).get("youtube", {})
    privacy = str(yt.get("privacy", "private")).lower().strip()
    if privacy not in ALLOWED_PRIVACY:
        print(f"[youtube] قيمة privacy غير معروفة ({privacy}) — سأستعمل private.")
        privacy = "private"

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
            "categoryId": str(yt.get("category_id", "28")),
        },
        "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True,
                            mimetype="video/mp4")
    req = youtube.videos().insert(part="snippet,status", body=body,
                                  media_body=media)
    resp = req.execute()
    vid = resp["id"]

    note = {
        "private": "خاص — تجده في YouTube Studio ← المحتوى، ولا يظهر في القناة",
        "unlisted": "غير مُدرَج — يفتح بالرابط فقط",
        "public": "منشور للجميع",
    }[privacy]
    print(f"[youtube] رُفع: https://youtu.be/{vid} ({note})")
    return {"id": vid, "url": f"https://youtu.be/{vid}", "privacy": privacy,
            "note": note}
