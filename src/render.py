"""
التركيب النهائي: يرصّ مقاطع المشاهد على الخط الزمني ويضع فوقها الصوت.

كل مقطع مشهد رُسم أصلًا بمدّة جزئه + الفاصل، فالتزامن مع التعليق مضمون
بالبناء لا بالتخمين. لا تكرار للّقطات ولا نصّ مرميّ على تدرّج.
"""

import os


def _fit(clip, w, h):
    clip = clip.resize(height=h)
    if clip.w < w:
        clip = clip.resize(width=w)
    return clip.crop(x_center=clip.w / 2, y_center=clip.h / 2, width=w, height=h)


def assemble(segment_paths, spans, total, cfg, out_path):
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

    track = audio_mod.build(spans, total, cfg)
    if track is not None:
        video = video.set_audio(track)

    video = CompositeVideoClip([video], size=(w, h)).set_duration(total)
    video.write_videofile(
        out_path, fps=fps, codec="libx264", audio_codec="aac",
        preset="medium", threads=4, logger=None,
    )
    print(f"[render] تم: {out_path} ({total:.1f}s)")
    return out_path
