"""
التركيب النهائي: يرصّ مقاطع المشاهد على الخط الزمني ويضع فوقها الصوت.

كل مقطع مشهد رُسم أصلًا بمدّة جزئه + الفاصل، فالتزامن مع التعليق مضمون
بالبناء لا بالتخمين. لا تكرار للّقطات ولا نصّ مرميّ على تدرّج.
"""

import os
import shutil
import subprocess

import compat  # noqa: F401  — يجب أن يسبق أي استيراد لـmoviepy


def grade_chain(h, cfg):
    """سلسلة اللمسة النهائية. القيم مقيسة لا مُخمَّنة.

    مخرَج Manim الخام مسطّح: حدود حادّة، ولا توهّج، ولا عمق. أربع خطوات
    تكفي ليبدو الإطار منتَجًا لا مُصدَّرًا:

      eq        تشبّع أعلى قليلًا ورفع طفيف للأسود (شبه مجاني)
      bloom     يُسرّب ضوء الأشكال المتوهّجة إلى ما حولها — هذه أهمّ خطوة
      vignette  يُعتم الأطراف فيصير للصورة مركز ثقل
      noise     حبيبة زمنية خفيفة: تكسر التشريط الذي يُحدثه ضغط يوتيوب
                في التدرّجات الداكنة، وتزيل برودة الصورة الحاسوبية

    قيست على 1080p30: نحو ١٫٣× الزمن الحقيقي. إسقاط الحبيبة يُنزلها إلى
    ٠٫٨× إن أردت تشغيلًا أسرع (finish.grain = 0).
    """
    f = cfg.get("finish", {})
    sat = f.get("saturation", 1.10)
    con = f.get("contrast", 1.03)
    lift = f.get("black_lift", 0.012)
    bloom = f.get("bloom", 0.22)
    # نصف قطر التوهّج يتبع الارتفاع حتى لا يتغيّر مظهره بتغيّر الدقّة
    sigma = f.get("bloom_sigma") or max(round(h / 18.0), 6)
    vig = f.get("vignette", 0.85)        # ٠٫٨٥ تُبقي الزاوية عند ٧٠٪ من سطوعها
    grain = f.get("grain", 4)

    parts = [f"eq=contrast={con}:saturation={sat}:brightness={lift}"]
    if bloom > 0:
        parts.append(f"split[a][b];[b]gblur=sigma={sigma}[c];"
                     f"[a][c]blend=all_mode=screen:all_opacity={bloom}")
    if 0 < vig < 1:
        parts.append(f"split[d][e];[e]vignette=PI/4[f];"
                     f"[d][f]blend=all_mode=normal:all_opacity={vig}")
    if grain:
        parts.append(f"noise=alls={int(grain)}:allf=t+u")
    return ",".join(parts)


def finish(src, dst, cfg):
    """يطبّق التدريج بتمريرة FFmpeg مستقلّة.

    مستقلّة عن moviepy عن قصد: لو فشل المرشّح لأي سبب نُرجِع الفيديو غير
    المدرَّج بدل أن تسقط الحلقة كلّها بعد ساعة من الرسم.
    """
    if not cfg.get("finish", {}).get("enabled", True):
        return src
    v = cfg["video"]
    chain = grade_chain(v["height"], cfg)
    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-i", src, "-vf", chain,
           "-c:v", "libx264", "-preset", cfg.get("finish", {}).get("preset", "medium"),
           "-crf", str(cfg.get("finish", {}).get("crf", 20)),
           "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", dst]
    print("[render] اللمسة النهائية: تدريج + توهّج + vignette + حبيبة…")
    try:
        subprocess.run(cmd, check=True, timeout=int(
            cfg.get("finish", {}).get("timeout_seconds", 5400)))
    except Exception as e:
        print(f"[render] تعذّر التدريج ({type(e).__name__}: {e}) — "
              f"سأسلّم الفيديو بلا تدريج.")
        return src
    if not (os.path.exists(dst) and os.path.getsize(dst) > 10000):
        print("[render] مخرَج التدريج فارغ — سأسلّم الفيديو بلا تدريج.")
        return src
    return dst


def _fit(clip, w, h):
    clip = clip.resize(height=h)
    if clip.w < w:
        clip = clip.resize(width=w)
    return clip.crop(x_center=clip.w / 2, y_center=clip.h / 2, width=w, height=h)


def assemble(segment_paths, spans, total, cfg, out_path, sfx_path=None):
    from moviepy.editor import (
        VideoFileClip, ColorClip, concatenate_videoclips, CompositeVideoClip,
    )
    import audio as audio_mod

    v = cfg["video"]
    w, h, fps = v["width"], v["height"], v["fps"]

    clips = []
    for p in segment_paths:
        try:
            c = VideoFileClip(p).without_audio()
            clips.append(_fit(c, w, h))
        except Exception as e:
            print(f"[render] تجاهل مقطعًا تالفًا ({p}): {e}")

    if not clips:
        raise RuntimeError("لا توجد مشاهد صالحة للتركيب.")

    video = concatenate_videoclips(clips, method="compose").set_fps(fps)

    # نضبط الطول على الخط الزمني الصوتي بالضبط
    if video.duration < total:
        pad = ColorClip((w, h), color=(0, 0, 0)).set_duration(total - video.duration)
        video = concatenate_videoclips([video, pad], method="compose")
    video = video.subclip(0, total)

    track = audio_mod.build(spans, total, cfg, sfx_path)
    if track is not None:
        video = video.set_audio(track)

    video = CompositeVideoClip([video], size=(w, h)).set_duration(total)

    # نكتب نسخة خامًا أوّلًا ثم نُدرّجها، فلو فشل التدريج بقي الفيديو
    raw_path = os.path.join(os.path.dirname(out_path), "video_raw.mp4")
    video.write_videofile(
        raw_path, fps=fps, codec="libx264", audio_codec="aac",
        preset="medium", threads=4, logger=None,
    )

    final = finish(raw_path, out_path, cfg)
    if final != out_path:
        shutil.move(raw_path, out_path)
    elif os.path.exists(raw_path):
        os.remove(raw_path)

    print(f"[render] تم: {out_path} ({total:.1f}s)")
    return out_path
