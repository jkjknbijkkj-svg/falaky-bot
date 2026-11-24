"""
رفع الفيديو إلى يوتيوب عبر YouTube Data API v3 — مع دعم تعدّد اللغات.

ما يرفعه هذا الملف:
  ١) الفيديو نفسه + العنوان والوصف العربيَّين (دائمًا).
  ٢) **عناوين وأوصاف موطّنة** بلغات أخرى (snippet.localizations): نفس
     الفيديو يظهر بعنوان الزائر بلغته في البحث والمقترحات.
  ٣) **ملفّات ترجمة (captions)** بكل لغة متاحة: ترجمة دقيقة من توقيت
     edge-tts، لا من التسميات التلقائية الضعيفة للعربية.

المسارات الصوتية المتعدّدة (multi-audio) لا تُرفع عبر Data API — يوتيوب
يمنحها فقط من واجهة Creator Studio (ميزة "إضافة لغة إلى الفيديو"). لذا
ندخل طريقين: ملفّات صوت MP3 منفصلة لكل لغة تُحفظ أثرًا على GitHub Actions
لترفعها يدويًا من Studio مرّة واحدة، وتبقى لاحقًا.

يحتاج ثلاثة أسرار بيئية (GitHub Secrets):
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
"""

import os

ALLOWED_PRIVACY = ("private", "unlisted", "public")


# نطاقات OAuth: upload للفيديو + force-ssl للتسميات والترجمات
_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def _client():
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials(
        token=None,
        refresh_token=os.environ["YT_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["YT_CLIENT_ID"],
        client_secret=os.environ["YT_CLIENT_SECRET"],
        scopes=_SCOPES,
    )
    return build("youtube", "v3", credentials=creds)


def upload(video_path, title, description, tags, cfg=None,
           localizations=None, captions=None, default_language="ar"):
    """يرفع الفيديو ثم يُلحق به العناوين الموطّنة وملفّات الترجمة.

    localizations: {"en": {"title": "...", "description": "..."}, ...}
    captions:      {"ar": "path/to/ar.srt", "en": "path/to/en.srt", ...}
    """
    from googleapiclient.http import MediaFileUpload

    yt = (cfg or {}).get("youtube", {})
    privacy = str(yt.get("privacy", "private")).lower().strip()
    if privacy not in ALLOWED_PRIVACY:
        print(f"[youtube] قيمة privacy غير معروفة ({privacy}) — سأستعمل private.")
        privacy = "private"

    youtube = _client()

    snippet = {
        "title": title[:95],
        "description": description[:4900],
        "tags": tags[:15],
        "categoryId": str(yt.get("category_id", "28")),
        "defaultLanguage": default_language,
        "defaultAudioLanguage": default_language,
    }

    # الترجمات داخل snippet تُقبل في نفس نداء الإنشاء — نفعل ذلك حتى
    # يظهر العنوان الموطّن منذ أوّل لحظة بدل انتظار تحديث لاحق
    if localizations:
        snippet["localizations"] = {
            code: {
                "title": str(loc.get("title", "") or "")[:95],
                "description": str(loc.get("description", "") or "")[:4900],
            }
            for code, loc in localizations.items()
            if loc and loc.get("title")
        }

    body = {"snippet": snippet,
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}}

    media = MediaFileUpload(video_path, chunksize=-1, resumable=True,
                            mimetype="video/mp4")
    parts = "snippet,status"
    if "localizations" in snippet:
        parts += ",localizations"

    req = youtube.videos().insert(part=parts, body=body, media_body=media)
    resp = req.execute()
    vid = resp["id"]

    # نُلحق ملفّات الترجمة بعد الرفع (حدّ الطلب الواحد يمنع رصّها كلّها)
    if captions:
        for code, path in captions.items():
            if path and os.path.exists(path):
                try:
                    _upload_caption(youtube, vid, code, path)
                except Exception as e:
                    print(f"[youtube] تعذّر رفع ترجمة {code}: {e}")

    note = {
        "private": "خاص — تجده في YouTube Studio ← المحتوى، ولا يظهر في القناة",
        "unlisted": "غير مُدرَج — يفتح بالرابط فقط",
        "public": "منشور للجميع",
    }[privacy]
    langs_note = ""
    if localizations:
        langs_note = f" + عناوين موطّنة: {', '.join(sorted(localizations))}"
    print(f"[youtube] رُفع: https://youtu.be/{vid} ({note}){langs_note}")

    return {"id": vid, "url": f"https://youtu.be/{vid}", "privacy": privacy,
            "note": note,
            "localizations": sorted(localizations.keys()) if localizations else [],
            "captions": sorted(captions.keys()) if captions else []}


def _upload_caption(youtube, video_id, language, path):
    """يرفع ملفّ ترجمة لمسار لغوي واحد."""
    from googleapiclient.http import MediaFileUpload

    body = {
        "snippet": {
            "videoId": video_id,
            "language": language,
            "name": f"{language} (auto)",
            "isDraft": False,
        }
    }
    media = MediaFileUpload(path, mimetype="application/octet-stream",
                            resumable=False)
    youtube.captions().insert(part="snippet", body=body, media_body=media).execute()
    print(f"[youtube] ترجمة {language} رُفعت.")
