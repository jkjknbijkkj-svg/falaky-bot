"""
جلب لقطات فيديو من مصادر مجانية **مرخّصة للاستخدام التجاري** بحسب كلمات مفتاحية.
المصادر النظيفة ذات الـ API الموثوق:
  - Pexels Videos  (مفتاح مجاني: PEXELS_API_KEY)
  - Pixabay Videos (مفتاح مجاني: PIXABAY_API_KEY)
كلاهما يسمح بالاستخدام التجاري بلا نسب إجباري. نتجنّب المصادر غير الواضحة الرخصة عمدًا.
يعيد قائمة مسارات ملفات mp4 محلية. إن لم توجد مفاتيح، يعيد قائمة فارغة
(فيتحوّل المحرّك تلقائيًا إلى خلفية متدرّجة).
"""

import os
import tempfile

import requests

HEADERS = {"User-Agent": "falaky-bot/1.0"}
_TMP = tempfile.mkdtemp(prefix="clips_")


def _download(url, idx):
    dest = os.path.join(_TMP, f"clip_{idx:03d}.mp4")
    with requests.get(url, stream=True, timeout=180, headers=HEADERS) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)
    if os.path.getsize(dest) < 10000:
        os.remove(dest)
        raise ValueError("ملف صغير جدًا")
    return dest


def _pexels(keyword, n):
    key = os.environ.get("PEXELS_API_KEY")
    if not key:
        return []
    try:
        r = requests.get(
            "https://api.pexels.com/videos/search",
            headers={"Authorization": key},
            params={"query": keyword, "per_page": n, "orientation": "landscape", "size": "medium"},
            timeout=60,
        )
        r.raise_for_status()
        urls = []
        for v in r.json().get("videos", []):
            mp4 = [f for f in v.get("video_files", [])
                   if f.get("file_type") == "video/mp4" and (f.get("height") or 0) <= 1080]
            if mp4:
                urls.append(sorted(mp4, key=lambda f: f.get("height") or 0)[-1]["link"])
        return urls
    except Exception as e:
        print(f"[footage] Pexels '{keyword}': {e}")
        return []


def _pixabay(keyword, n):
    key = os.environ.get("PIXABAY_API_KEY")
    if not key:
        return []
    try:
        r = requests.get(
            "https://pixabay.com/api/videos/",
            params={"key": key, "q": keyword, "per_page": max(3, n)},
            timeout=60,
        )
        r.raise_for_status()
        urls = []
        for v in r.json().get("hits", []):
            vids = v.get("videos", {})
            link = (vids.get("large") or vids.get("medium") or vids.get("small") or {}).get("url")
            if link:
                urls.append(link)
        return urls
    except Exception as e:
        print(f"[footage] Pixabay '{keyword}': {e}")
        return []


def fetch(keywords, count):
    """يجمع روابط من المصدرين عبر الكلمات، ثم ينزّل حتى count مقطعًا."""
    if not keywords:
        return []
    urls = []
    per_kw = max(2, count // max(len(keywords), 1) + 1)
    for kw in keywords:
        urls += _pexels(kw, per_kw)
        urls += _pixabay(kw, per_kw)
    seen, uniq = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            uniq.append(u)

    paths = []
    for i, u in enumerate(uniq):
        if len(paths) >= count:
            break
        try:
            paths.append(_download(u, i))
        except Exception as e:
            print(f"[footage] تنزيل فشل: {e}")
    print(f"[footage] نزّلت {len(paths)} مقطعًا من {len(uniq)} رابطًا")
    return paths
