"""
نظام التصميم: الخطوط، الألوان، تشكيل العربية، وبطاقة ساكنة مصمَّمة.

يُستعمل في بديل Manim وفي أي طبقة نصّ فوق اللقطات. الهدف أن يكون لكل
إطار في القناة النسب والألوان والخط نفسه — الثبات هو نصف الاحترافية.
"""

import glob
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import arabic_reshaper
try:
    from bidi.algorithm import get_display
except ImportError:  # python-bidi >= 0.5
    from bidi import get_display


# ------------------------------------------------------------------ أدوات

def hex_rgb(value, default=(255, 255, 255)):
    if isinstance(value, (list, tuple)):
        return tuple(int(c) for c in value[:3])
    s = str(value).lstrip("#")
    if len(s) == 3:
        s = "".join(ch * 2 for ch in s)
    try:
        return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        return default


def shape(text):
    """تشكيل + ترتيب ثنائي الاتجاه — ضروري لـPillow (وليس لـManim)."""
    return get_display(arabic_reshaper.reshape(str(text)))


def find_font(candidates):
    for p in candidates:
        if os.path.exists(p):
            return p
    roots = ["/usr/share/fonts", os.path.expanduser("~/.fonts"),
             os.path.expanduser("~/.local/share/fonts")]
    for kw in ("Amiri", "amiri", "Naskh", "naskh", "Kacst", "kacst",
               "Arabic", "arabic", "Scheherazade"):
        for root in roots:
            if not os.path.isdir(root):
                continue
            for ext in ("ttf", "otf"):
                hits = glob.glob(os.path.join(root, "**", f"*{kw}*.{ext}"),
                                 recursive=True)
                if hits:
                    return sorted(hits)[0]
    raise FileNotFoundError(
        "لم أجد خطًا عربيًا. ثبّت fonts-hosny-amiri أو ضع assets/arabic.ttf"
    )


def font_family_name(design_cfg):
    """اسم العائلة الذي يمرَّر إلى Manim (Pango يبحث بالاسم لا بالمسار)."""
    return design_cfg.get("font_family") or "Amiri"


# ------------------------------------------------------------- بطاقة ساكنة

def _glow(w, h, accent):
    """توهّج ناعم يكسر جمود الخلفية المسطّحة."""
    layer = Image.new("RGB", (w // 6, h // 6), (0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = layer.width // 2, int(layer.height * 0.42)
    for r, a in ((layer.width // 2, 26), (layer.width // 3, 22), (layer.width // 5, 20)):
        d.ellipse([cx - r, cy - r, cx + r, cy + r],
                  fill=tuple(int(c * a / 100) for c in accent))
    layer = layer.filter(ImageFilter.GaussianBlur(14))
    return layer.resize((w, h), Image.Resampling.BILINEAR)


def card(w, h, heading, items, caption, design_cfg):
    bg = hex_rgb(design_cfg["bg"], (11, 16, 32))
    surface = hex_rgb(design_cfg["surface"], (22, 31, 60))
    accent = hex_rgb(design_cfg["accent"], (76, 201, 240))
    accent_w = hex_rgb(design_cfg["accent_warm"], (247, 184, 1))
    text_c = hex_rgb(design_cfg["text"], (234, 242, 255))
    muted = hex_rgb(design_cfg["muted"], (147, 166, 200))

    font_path = find_font(design_cfg["font_path_candidates"])
    f_head = ImageFont.truetype(font_path, int(h * 0.052))
    f_item = ImageFont.truetype(font_path, int(h * 0.044))
    f_cap = ImageFont.truetype(font_path, int(h * 0.030))

    base = np.asarray(Image.new("RGB", (w, h), bg), dtype=np.int16)
    glow = np.asarray(_glow(w, h, accent), dtype=np.int16)
    img = Image.fromarray(np.clip(base + glow, 0, 255).astype("uint8"))
    d = ImageDraw.Draw(img)

    margin = int(w * 0.075)
    right = w - margin

    # العنوان أعلى اليمين + خط تحته
    y = int(h * 0.13)
    if heading:
        d.text((right, y), shape(heading), font=f_head, fill=accent, anchor="ra")
        d.rectangle([right - int(w * 0.11), y + int(h * 0.075),
                     right, y + int(h * 0.078)], fill=accent_w)

    # النقاط بمحاذاة يمين
    top = int(h * 0.30)
    gap = int(h * 0.105)
    for i, it in enumerate(list(items)[:5]):
        ty = top + i * gap
        txt = str(it).replace("|", " — ")
        d.text((right - int(w * 0.028), ty), shape(txt), font=f_item,
               fill=text_c, anchor="ra")
        r = int(h * 0.010)
        cy = ty + int(h * 0.022)
        d.ellipse([right - r * 2, cy - r, right, cy + r], fill=accent_w)

    # شريط سفلي للسطر التوضيحي
    if caption:
        bar_h = int(h * 0.088)
        d.rectangle([0, h - bar_h, w, h], fill=surface)
        d.text((w // 2, h - bar_h // 2), shape(caption), font=f_cap,
               fill=muted, anchor="mm")

    return img
