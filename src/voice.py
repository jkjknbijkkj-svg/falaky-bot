"""
التعليق الصوتي عبر edge-tts (مجاني، بلا مفتاح).

الفرق عن النسخة القديمة: نولّد مقطعًا منفصلًا لكل جزء من الحلقة
(الخطّاف، كل قسم، الخاتمة). هذا يعطينا مدّة كل جزء قبل الرسم،
فتتزامن المشاهد مع الكلام بدقّة بدل أن نقسّم الزمن تخمينًا.
"""

import asyncio
import os


async def _save(text, out_path, voice, rate, pitch):
    import edge_tts

    kw = {"voice": voice}
    if rate:
        kw["rate"] = rate
    if pitch:
        kw["pitch"] = pitch
    await edge_tts.Communicate(text, **kw).save(out_path)


def _duration(path):
    try:
        from moviepy.editor import AudioFileClip
        clip = AudioFileClip(path)
        d = clip.duration
        clip.close()
        return d
    except Exception:
        return None


def _synth_one(text, out_path, cfg):
    v = cfg["voice"]
    voices = [v["edge_voice"]] + list(v.get("fallback_voices") or [])
    for voice in voices:
        try:
            asyncio.run(_save(text, out_path, voice, v.get("rate"), v.get("pitch")))
            if os.path.exists(out_path) and os.path.getsize(out_path) > 1024:
                return _duration(out_path)
        except Exception as e:
            print(f"[voice] تعذّر الصوت {voice}: {e}")
    return None


def synth_script(script, cfg, out_dir):
    """يعيد قائمة أجزاء: [{'key','text','path','duration'}, ...]"""
    os.makedirs(out_dir, exist_ok=True)
    blocks = [("intro", script["hook"])]
    blocks += [(str(i), s["narration"]) for i, s in enumerate(script["sections"])]
    blocks.append(("outro", script["outro"]))

    parts = []
    for key, text in blocks:
        text = (text or "").strip()
        path = os.path.join(out_dir, f"vo_{key}.mp3")
        dur = _synth_one(text, path, cfg) if text else None
        if dur is None:
            # لا صوت: نعطي مدّة تقديرية من عدد الكلمات حتى لا ينهار الإيقاع
            dur = max(3.0, len(text.split()) / 2.35)
            path = None
            print(f"[voice] الجزء {key} بلا صوت — مدّة تقديرية {dur:.1f}s")
        parts.append({"key": key, "text": text, "path": path,
                      "duration": round(float(dur), 2)})
        print(f"[voice] {key}: {parts[-1]['duration']}s")
    return parts
