"""
طبقة الصوت: تعليق مرصوف زمنيًا + موسيقى تنخفض تلقائيًا تحت الكلام.

الـducking هنا ليس تقديريًا: نحن نعرف بالضبط متى يتكلّم الراوي لأننا
ولّدنا مقطعًا لكل جزء، فنبني منحنى كسب دقيق من تلك الفترات.
هذه أرخص قفزة جودة في المشروع كلّه.
"""

import os

import numpy as np


def layout(parts, gap):
    """يحسب بداية ونهاية كل جزء على الخط الزمني."""
    t = 0.0
    spans = []
    for p in parts:
        start = t
        end = start + p["duration"]
        spans.append({"key": p["key"], "path": p["path"],
                      "start": round(start, 3), "end": round(end, 3),
                      "duration": p["duration"]})
        t = end + gap
    total = max(t - gap, 1.0)
    return spans, round(total, 3)


def _gain_curve(spans, total, cfg_audio):
    """منحنى كسب الموسيقى: منخفض أثناء الكلام، مرتفع في الفراغات."""
    lo = float(cfg_audio.get("music_gain_speech", 0.07))
    hi = float(cfg_audio.get("music_gain_gap", 0.26))
    atk = float(cfg_audio.get("duck_attack", 0.25))
    rel = float(cfg_audio.get("duck_release", 0.65))

    pts = [(0.0, hi)]
    for s in spans:
        pts.append((max(s["start"] - atk, 0.0), hi))
        pts.append((s["start"], lo))
        pts.append((s["end"], lo))
        pts.append((min(s["end"] + rel, total), hi))
    pts.append((total, hi))

    pts.sort(key=lambda p: p[0])
    xs, ys = [], []
    for x, y in pts:
        if xs and abs(x - xs[-1]) < 1e-4:
            ys[-1] = min(ys[-1], y)
            continue
        xs.append(x)
        ys.append(y)
    return np.array(xs), np.array(ys)


def build(spans, total, cfg):
    """يعيد مقطعًا صوتيًا كاملًا للفيديو (أو None)."""
    from moviepy.editor import AudioFileClip, CompositeAudioClip

    a = cfg.get("audio", {})
    tracks = []

    for s in spans:
        if s["path"] and os.path.exists(s["path"]):
            try:
                tracks.append(AudioFileClip(s["path"]).set_start(s["start"]))
            except Exception as e:
                print(f"[audio] تعذّر تحميل {s['key']}: {e}")

    music_path = a.get("music_path")
    if music_path and os.path.exists(music_path):
        try:
            from moviepy.audio.fx.all import audio_loop
            music = audio_loop(AudioFileClip(music_path), duration=total)
            xs, ys = _gain_curve(spans, total, a)

            def duck(get_frame, t):
                frame = np.asarray(get_frame(t), dtype="float64")
                g = np.interp(t, xs, ys)
                if frame.ndim == 2:
                    g = np.asarray(g).reshape(-1, 1)
                return frame * g

            tracks.append(music.fl(duck, keep_duration=True).set_start(0))
            print("[audio] موسيقى مع ducking مفعّلة")
        except Exception as e:
            print(f"[audio] تجاهل الموسيقى: {e}")
    else:
        print("[audio] لا توجد موسيقى (assets/music.mp3) — الفيديو بالتعليق فقط.")

    if not tracks:
        return None
    return CompositeAudioClip(tracks).set_duration(total)
