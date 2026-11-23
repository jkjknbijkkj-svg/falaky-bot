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

    # الفاصل بين الأقسام (٠٫٥s) أقصر من زمن التحلّل (٠٫٦٥s)، فنقطة ارتفاع
    # القسم السابق كانت تقع **داخل** كلام القسم التالي: تُرتّب القائمة
    # فتُدرَج (end+0.65, hi) بعد (start, lo)، فترتفع الموسيقى فوق أوّل
    # جملة من كل قسم. القياس أظهر ٠٫١٦٥ أثناء الكلام بدل ٠٫٠٧.
    #
    # الصواب أن تُدمَج المكابس بأخذ **الأدنى** من أغلفتها، لا بوصل نقاطها:
    # ما دام أحدها يكبس، فالموسيقى مكبوسة.
    bounds = {0.0, float(total)}
    for s in spans:
        for x in (s["start"] - atk, s["start"], s["end"], s["end"] + rel):
            bounds.add(min(max(float(x), 0.0), float(total)))
    xs = np.array(sorted(bounds))

    def one(span, t):
        a, b = span["start"], span["end"]
        if t <= a - atk or t >= b + rel:
            return hi
        if a <= t <= b:
            return lo
        if t < a:                                   # هبوط قبل الكلام
            return hi + (lo - hi) * (t - (a - atk)) / max(atk, 1e-6)
        return lo + (hi - lo) * (t - b) / max(rel, 1e-6)   # ارتفاع بعده

    ys = np.array([min([one(s, t) for s in spans], default=hi) for t in xs])
    return xs, ys


def build(spans, total, cfg, sfx_path=None):
    """يعيد مقطعًا صوتيًا كاملًا للفيديو (أو None).

    ثلاث طبقات: التعليق، وطبقة التصميم الصوتي المرصوفة على اللقطات،
    والموسيقى التي تنخفض تحت الكلام.
    """
    from moviepy.editor import AudioFileClip, CompositeAudioClip

    a = cfg.get("audio", {})
    tracks = []

    for s in spans:
        if s["path"] and os.path.exists(s["path"]):
            try:
                tracks.append(AudioFileClip(s["path"]).set_start(s["start"]))
            except Exception as e:
                print(f"[audio] تعذّر تحميل {s['key']}: {e}")

    if sfx_path and os.path.exists(sfx_path):
        try:
            g = float(a.get("sfx_gain", 0.5))
            clip = AudioFileClip(sfx_path).volumex(g).set_start(0)
            tracks.append(clip)
            print(f"[audio] طبقة التصميم الصوتي مُضافة (كسب {g})")
        except Exception as e:
            print(f"[audio] تجاهل طبقة المؤثّرات: {e}")

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
