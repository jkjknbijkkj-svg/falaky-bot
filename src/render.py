"""
محرّك المنتاج: يركّب لقطات الفيديو الخارجية + سرد + عناوين عربية + موسيقى.
أسلوب مقيّد (احترافي): نسبة 16:9، طبقة تعتيم للنصّ، شريط سفلي للعناوين،
تلاشٍ ناعم، لون موحّد. إن لم توجد لقطات، يرجع إلى خلفية متدرّجة.
بايثون خالص: Pillow للنصوص، moviepy/ffmpeg للتركيب.
"""

import glob
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# توافق moviepy 1.0.3 مع Pillow 10+ (أُزيل Image.ANTIALIAS)
if not hasattr(Image, "ANTIALIAS"):
    Image.ANTIALIAS = Image.Resampling.LANCZOS

import arabic_reshaper
try:
    from bidi.algorithm import get_display
except ImportError:
    from bidi import get_display


def _shape(text):
    return get_display(arabic_reshaper.reshape(str(text)))


def _find_font(candidates):
    for p in candidates:
        if os.path.exists(p):
            return p
    roots = ["/usr/share/fonts", os.path.expanduser("~/.fonts"),
             os.path.expanduser("~/.local/share/fonts")]
    for kw in ["Amiri", "amiri", "Naskh", "naskh", "Kacst", "kacst",
               "Arabic", "arabic", "Scheherazade"]:
        for root in roots:
            if not os.path.isdir(root):
                continue
            for ext in ("ttf", "otf"):
                hits = glob.glob(os.path.join(root, "**", f"*{kw}*.{ext}"), recursive=True)
                if hits:
                    return sorted(hits)[0]
    raise FileNotFoundError(
        "لم أجد خطًا عربيًا. ثبّت fonts-amiri أو ضع assets/arabic.ttf."
    )


def _gradient(w, h, top, bottom):
    ramp = np.linspace(0, 1, h).reshape(h, 1, 1)
    arr = np.array(top).reshape(1, 1, 3) * (1 - ramp) + np.array(bottom).reshape(1, 1, 3) * ramp
    return np.repeat(arr.astype("uint8"), w, axis=1)


def _caption_png(w, h, text, font, fill, band=True):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if band:
        d.rectangle([0, int(h * 0.70), w, h], fill=(0, 0, 0, 150))
    d.text((w // 2, int(h * 0.82)), _shape(text), font=font,
           fill=(fill[0], fill[1], fill[2], 255), anchor="mm")
    return np.array(img)


def _title_png(w, h, text, font, fill):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.text((w // 2, int(h * 0.44)), _shape(text), font=font,
           fill=(fill[0], fill[1], fill[2], 255), anchor="mm",
           stroke_width=3, stroke_fill=(0, 0, 0, 220))
    return np.array(img)


def _fit(clip, w, h):
    clip = clip.resize(height=h)
    if clip.w < w:
        clip = clip.resize(width=w)
    return clip.crop(x_center=clip.w / 2, y_center=clip.h / 2, width=w, height=h)


def build_video(fact, voice_path, voice_duration, clip_paths, cfg, out_path):
    from moviepy.editor import (
        VideoFileClip, ImageClip, ColorClip, CompositeVideoClip,
        concatenate_videoclips, AudioFileClip, CompositeAudioClip,
    )

    v, s = cfg["video"], cfg["style"]
    w, h, fps = v["width"], v["height"], v["fps"]
    duration = max(voice_duration or 0, v["min_duration_seconds"])

    font_path = _find_font(s["font_path_candidates"])
    f_title = ImageFont.truetype(font_path, int(h * 0.075))
    f_point = ImageFont.truetype(font_path, int(h * 0.045))

    segments = []
    for c in clip_paths:
        try:
            vc = VideoFileClip(c).without_audio()
            vc = _fit(vc, w, h).subclip(0, min(4.0, max(vc.duration, 0.5)))
            segments.append(vc)
        except Exception as e:
            print(f"[render] تجاهل لقطة: {e}")
    if segments:
        base = concatenate_videoclips(segments, method="compose")
        reps = int(duration // max(base.duration, 0.1)) + 1
        base = concatenate_videoclips([base] * reps, method="compose").subclip(0, duration)
    else:
        bg = _gradient(w, h, s["bg_top"], s["bg_bottom"])
        base = ImageClip(bg).set_duration(duration)

    base = base.set_fps(fps)

    dim = ColorClip((w, h), color=(0, 0, 0)).set_opacity(0.30).set_duration(duration)

    overlays = [dim]
    title_clip = (ImageClip(_title_png(w, h, fact["title"], f_title, s["title_color"]))
                  .set_start(0).set_duration(min(3.5, duration)).crossfadein(0.4))
    overlays.append(title_clip)

    points = fact["points"]
    pstart = min(3.0, duration * 0.25)
    pspan = max(duration - pstart - 0.3, 0.1)
    slot = pspan / max(len(points), 1)
    for idx, pt in enumerate(points):
        png = _caption_png(w, h, pt, f_point, s["text_color"])
        oc = (ImageClip(png).set_start(pstart + idx * slot)
              .set_duration(slot + 0.05).crossfadein(0.3))
        overlays.append(oc)

    video = CompositeVideoClip([base] + overlays, size=(w, h)).set_duration(duration)

    audios = []
    if voice_path and os.path.exists(voice_path) and voice_duration:
        audios.append(AudioFileClip(voice_path))
    music = cfg.get("music_path", "assets/music.mp3")
    if music and os.path.exists(music):
        try:
            from moviepy.audio.fx.all import audio_loop, volumex
            m = AudioFileClip(music)
            m = audio_loop(m, duration=duration)
            audios.append(volumex(m, 0.12))
        except Exception as e:
            print(f"[render] تجاهل الموسيقى: {e}")
    if audios:
        video = video.set_audio(CompositeAudioClip(audios))

    video.write_videofile(
        out_path, fps=fps, codec="libx264", audio_codec="aac",
        preset="medium", threads=4, logger=None,
    )
