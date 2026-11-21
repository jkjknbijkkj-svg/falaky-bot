"""
محرّك الرسوم: يبني فيديو موشن-غرافيكس مسطّح من (العنوان + النقاط + الصوت).
بايثون خالص: Pillow للرسم، numpy للخلفية، moviepy للتجميع مع ffmpeg.
"""

import os
import shutil
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

import arabic_reshaper
from bidi.algorithm import get_display


def _shape(text):
    """تشكيل العربية + ترتيب ثنائي الاتجاه حتى تُرسم موصولة وصحيحة الاتجاه."""
    return get_display(arabic_reshaper.reshape(text))


def _find_font(candidates):
    for p in candidates:
        if os.path.exists(p):
            return p
    raise FileNotFoundError(
        "لم أجد خطًا عربيًا. ثبّت خطًا (مثلًا: sudo apt-get install fonts-amiri) "
        "أو ضع ملف .ttf في assets/arabic.ttf، ثم حدّث المسار في config.json."
    )


def _smoothstep(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def _gradient_bg(w, h, top, bottom):
    ramp = np.linspace(0, 1, h).reshape(h, 1, 1)
    arr = np.array(top).reshape(1, 1, 3) * (1 - ramp) + np.array(bottom).reshape(1, 1, 3) * ramp
    arr = np.repeat(arr.astype("uint8"), w, axis=1)
    return Image.fromarray(arr, "RGB").convert("RGBA")


def _glow(w, h, accent):
    """هالة ناعمة مركزية (تُحسب مرة واحدة)."""
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx, cy = w // 2, int(h * 0.42)
    r = int(h * 0.42)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(accent[0], accent[1], accent[2], 70))
    return layer.filter(ImageFilter.GaussianBlur(r // 3))


def _text_layer(size, text, font, fill, alpha, center, dy=0):
    """طبقة شفافة فيها نص بدرجة شفافية alpha (0..1)."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = int(max(0, min(1, alpha)) * 255)
    d.text((center[0], center[1] + dy), _shape(text), font=font,
           fill=(fill[0], fill[1], fill[2], a), anchor="mm")
    return layer


def build_video(fact, voice_path, voice_duration, cfg, out_path):
    from moviepy.editor import ImageSequenceClip, AudioFileClip

    v = cfg["video"]
    s = cfg["style"]
    w, h, fps = v["width"], v["height"], v["fps"]
    duration = max(voice_duration or 0, v["min_duration_seconds"])
    n_frames = int(duration * fps)

    font_path = _find_font(s["font_path_candidates"])
    f_title = ImageFont.truetype(font_path, int(h * 0.075))
    f_point = ImageFont.truetype(font_path, int(h * 0.045))

    bg = _gradient_bg(w, h, s["bg_top"], s["bg_bottom"])
    glow = _glow(w, h, s["accent"])
    base = Image.alpha_composite(bg, glow)

    points = fact["points"]
    # توقيت ظهور العناصر
    title_in = 0.7
    points_start = 1.1
    points_span = max(duration - points_start - 0.6, 0.1)
    slot = points_span / max(len(points), 1)

    title_y = int(h * 0.30)
    first_point_y = int(h * 0.50)
    point_gap = int(h * 0.11)

    tmp = tempfile.mkdtemp(prefix="frames_")
    try:
        for i in range(n_frames):
            t = i / fps
            frame = base.copy()

            # العنوان: ظهور تدريجي + ارتفاع بسيط
            ta = _smoothstep(t / title_in)
            frame = Image.alpha_composite(
                frame,
                _text_layer((w, h), fact["title"], f_title, s["title_color"], ta,
                            (w // 2, title_y), dy=int((1 - ta) * 25)),
            )

            # النقاط: تظهر واحدة تلو الأخرى
            for idx, pt in enumerate(points):
                start = points_start + idx * slot
                pa = _smoothstep((t - start) / 0.45)
                if pa <= 0:
                    continue
                y = first_point_y + idx * point_gap
                frame = Image.alpha_composite(
                    frame,
                    _text_layer((w, h), pt, f_point, s["text_color"], pa,
                                (w // 2, y), dy=int((1 - pa) * 18)),
                )

            frame.convert("RGB").save(os.path.join(tmp, f"f{i:05d}.png"))

        files = [os.path.join(tmp, f"f{i:05d}.png") for i in range(n_frames)]
        clip = ImageSequenceClip(files, fps=fps)
        if voice_path and os.path.exists(voice_path) and voice_duration:
            clip = clip.set_audio(AudioFileClip(voice_path))
        clip.write_videofile(
            out_path, fps=fps, codec="libx264", audio_codec="aac",
            preset="medium", threads=4, logger=None,
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
