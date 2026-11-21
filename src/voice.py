"""
توليد الصوت العربي عبر edge-tts (مجاني، أصوات Microsoft Neural، بلا مفتاح).
يُرجع مدة المقطع بالثواني، أو None إن فشل (فيُكمل المشروع بفيديو صامت بمدة افتراضية).
"""

import asyncio
import os


async def _synth(text, out_path, voice, rate):
    import edge_tts

    communicate = edge_tts.Communicate(text, voice=voice, rate=rate)
    await communicate.save(out_path)


def _duration(path):
    # نقرأ المدة عبر moviepy (يعتمد على ffmpeg)
    try:
        from moviepy.editor import AudioFileClip

        clip = AudioFileClip(path)
        d = clip.duration
        clip.close()
        return d
    except Exception:
        return None


def synth(text, out_path, cfg):
    voice = cfg["voice"]["edge_voice"]
    rate = cfg["voice"]["rate"]
    try:
        asyncio.run(_synth(text, out_path, voice, rate))
    except Exception as e:
        print(f"[voice] تعذّر توليد الصوت ({e})؛ سيكون الفيديو صامتًا.")
        return None
    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        return None
    return _duration(out_path)
