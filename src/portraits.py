"""
جلب صور العلماء من ويكيميديا — **بترخيص حرّ فقط**.

لماذا هذا التشدّد؟ لأن صورة محمية الحقوق داخل فيديو على يوتيوب تعني ضربة
حقوق على القناة. فلا نقبل إلا ما ترخيصه صريح في الملك العام أو المشاع
الإبداعي، ونذكر المصدر في وصف الفيديو. وإن لم نجد صورة حرّة، نرجع إلى
الحرف الأول داخل الدائرة بدل أن نخاطر.

المسار:
  اسم العالِم → صفحة ويكيبيديا (عربية ثم إنجليزية) → صورة الصفحة
  → ترخيصها من ويكيميديا كومنز → قبول أو رفض → قصّ دائري → PNG شفّاف
"""

import os
import re
import urllib.parse

# ترخيص مقبول إن ورد أيٌّ من هذه في اسمه أو شروط استعماله
_OK = ("public domain", "pd-", "pd ", "cc0", "cc by", "cc-by",
       "creative commons", "attribution")

# وإن ورد أيٌّ من هذه فهو مرفوض مهما قال غيره
_BAD = ("fair use", "non-free", "nonfree", "copyright", "all rights reserved")

_HEADERS = {"User-Agent": "falaky-bot/1.0 (educational Arabic physics channel)"}
_TIMEOUT = 45


def _get(url, params=None):
    import requests
    r = requests.get(url, params=params, headers=_HEADERS, timeout=_TIMEOUT)
    r.raise_for_status()
    return r


def _page_image(name, lang):
    """عنوان الصفحة وصورتها الرئيسية من ويكيبيديا."""
    try:
        # البحث عن الصفحة أولًا: الاسم قد يختلف عن عنوان المقالة
        r = _get(f"https://{lang}.wikipedia.org/w/api.php", {
            "action": "query", "list": "search", "srsearch": name,
            "srlimit": 1, "format": "json",
        })
        hits = r.json().get("query", {}).get("search", [])
        if not hits:
            return None
        title = hits[0]["title"]

        quoted = urllib.parse.quote(title.replace(" ", "_"), safe="")
        r = _get(f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quoted}")
        data = r.json()
        src = (data.get("originalimage") or {}).get("source") \
            or (data.get("thumbnail") or {}).get("source")
        return (title, src) if src else None
    except Exception as e:
        print(f"[portraits] {lang}: تعذّر البحث عن «{name}» ({e}).")
        return None


def _commons_file(url):
    """اسم الملف في كومنز من رابط upload.wikimedia.org."""
    m = re.search(r"/commons/(?:thumb/)?[0-9a-f]/[0-9a-f]{2}/([^/]+)", url)
    if not m:
        return None
    return urllib.parse.unquote(m.group(1))


def _license_ok(filename):
    """يعيد (مقبول؟، اسم الترخيص، المؤلّف)."""
    try:
        r = _get("https://commons.wikimedia.org/w/api.php", {
            "action": "query", "titles": f"File:{filename}",
            "prop": "imageinfo", "iiprop": "extmetadata", "format": "json",
        })
        pages = r.json().get("query", {}).get("pages", {})
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata", {}) or {}
            lic = str(meta.get("LicenseShortName", {}).get("value", ""))
            terms = str(meta.get("UsageTerms", {}).get("value", ""))
            artist = re.sub(r"<[^>]+>", "", str(
                meta.get("Artist", {}).get("value", ""))).strip()

            blob = f"{lic} {terms}".lower()
            if any(b in blob for b in _BAD):
                return False, lic, artist
            if any(k in blob for k in _OK):
                return True, lic or "Public domain", artist
            return False, lic, artist
    except Exception as e:
        print(f"[portraits] تعذّر فحص ترخيص {filename} ({e}).")
    return False, "", ""


def _circle_crop(raw_path, out_path, size=512):
    """قصّ مربّع يميل إلى أعلى الصورة (مكان الوجه) ثم قناع دائري شفّاف."""
    from PIL import Image, ImageDraw

    img = Image.open(raw_path).convert("RGB")
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = int((h - side) * 0.25)          # الوجه عادةً أعلى من المنتصف
    img = img.crop((left, top, left + side, top + side)).resize(
        (size, size), Image.Resampling.LANCZOS)

    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, size * 4 - 1, size * 4 - 1], fill=255)
    mask = mask.resize((size, size), Image.Resampling.LANCZOS)  # حواف ناعمة

    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    out.save(out_path)
    return out_path


def fetch(name, out_dir, slug):
    """يعيد {'path': اسم الملف, 'credit': نصّ النسب} أو None."""
    import requests

    name = str(name).strip()
    if not name:
        return None

    for lang in ("ar", "en"):
        found = _page_image(name, lang)
        if not found:
            continue
        title, url = found

        filename = _commons_file(url)
        if not filename:
            print(f"[portraits] «{name}»: الصورة ليست من كومنز — تُرفض.")
            continue

        ok, lic, artist = _license_ok(filename)
        if not ok:
            print(f"[portraits] «{name}»: ترخيص غير حرّ ({lic or 'مجهول'}) — تُرفض.")
            continue

        try:
            raw = os.path.join(out_dir, f"{slug}_raw")
            with requests.get(url, headers=_HEADERS, timeout=_TIMEOUT,
                              stream=True) as r:
                r.raise_for_status()
                with open(raw, "wb") as fh:
                    for chunk in r.iter_content(1 << 16):
                        fh.write(chunk)

            png = os.path.join(out_dir, f"{slug}.png")
            _circle_crop(raw, png)
            os.remove(raw)
        except Exception as e:
            print(f"[portraits] «{name}»: فشل التنزيل أو القصّ ({e}).")
            continue

        credit = f"{title} — {lic}"
        if artist:
            credit += f" — {artist}"
        credit += " (ويكيميديا كومنز)"
        print(f"[portraits] «{name}»: صورة حرّة ({lic}).")
        return {"path": os.path.basename(png), "credit": credit}

    print(f"[portraits] «{name}»: لا صورة حرّة — سأكتفي بالحرف الأول.")
    return None


def attach(script, cfg, work_dir):
    """يضيف صورة لكل قسم من نوع profile، ويجمع نصوص النسب."""
    if not cfg.get("portraits", {}).get("enabled", True):
        return []

    credits = []
    for i, sec in enumerate(script.get("sections", [])):
        vis = sec.get("visual", {})
        if vis.get("type") != "profile":
            continue
        items = vis.get("items") or []
        if not items:
            continue
        res = fetch(items[0], work_dir, f"portrait_{i}")
        if res:
            vis["portrait"] = res["path"]
            sec["portrait_credit"] = res["credit"]
            credits.append(res["credit"])
    return credits
