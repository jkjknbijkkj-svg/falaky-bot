"""
التعليق الصوتي عبر edge-tts (مجاني، بلا مفتاح) — **مع توقيت كل كلمة**.

هذا هو ما يجعل «المونتاج يتبع الكلام كلمة بكلمة» ممكنًا فعلًا لا تقديرًا:
edge-tts يرسل مع الصوت أحداث WordBoundary تحمل لحظة نطق كل كلمة بدقّة
جزء من عشرة ملايين من الثانية. نلتقطها ونحفظها، فيقطع المونتاج على
الكلمة نفسها بدل أن نقسّم الزمن بالتساوي ونأمل أن يتصادف.

إن تعذّرت الأحداث (نسخة قديمة أو شبكة متقطّعة) نوزّع الكلمات بالتناسب
مع أطوالها — تقدير معقول يبقي النظام عاملًا.
"""

import asyncio
import os

_TICKS = 10_000_000          # وحدة edge-tts: 100 نانوثانية


async def _stream(text, out_path, voice, rate, pitch):
    """يكتب الصوت ويعيد قائمة حدود الكلمات."""
    import edge_tts

    kw = {"voice": voice}
    if rate:
        kw["rate"] = rate
    if pitch:
        kw["pitch"] = pitch

    words = []
    with open(out_path, "wb") as fh:
        async for chunk in edge_tts.Communicate(text, **kw).stream():
            if chunk["type"] == "audio":
                fh.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                words.append({
                    "w": chunk.get("text", ""),
                    "at": round(chunk["offset"] / _TICKS, 3),
                    "dur": round(chunk.get("duration", 0) / _TICKS, 3),
                })
    return words


def _duration(path):
    try:
        from moviepy.editor import AudioFileClip
        clip = AudioFileClip(path)
        d = clip.duration
        clip.close()
        return d
    except Exception:
        return None


def estimate_words(text, total):
    """توزيع تقديري بالتناسب مع طول كل كلمة — شبكة أمان لا أكثر."""
    toks = [w for w in str(text).split() if w]
    if not toks or total <= 0:
        return []
    weights = [len(w) + 1 for w in toks]
    span = sum(weights)
    out, t = [], 0.0
    last = len(toks) - 1
    for i, (w, wt) in enumerate(zip(toks, weights)):
        # آخر كلمة تنتهي عند total بالضبط فلا يتراكم خطأ التقريب
        end = total if i == last else t + total * wt / span
        out.append({"w": w, "at": round(t, 3), "dur": round(end - t, 3)})
        t = end
    return out


def _synth_one(text, out_path, cfg):
    v = cfg["voice"]
    voices = [v["edge_voice"]] + list(v.get("fallback_voices") or [])
    for voice in voices:
        try:
            words = asyncio.run(_stream(text, out_path, voice,
                                        v.get("rate"), v.get("pitch")))
            if os.path.exists(out_path) and os.path.getsize(out_path) > 1024:
                return _duration(out_path), words
        except Exception as e:
            print(f"[voice] تعذّر الصوت {voice}: {e}")
    return None, []


def synth_script(script, cfg, out_dir):
    """يعيد قائمة أجزاء: [{'key','text','path','duration','words'}, ...]"""
    os.makedirs(out_dir, exist_ok=True)
    blocks = [("intro", script["hook"])]
    blocks += [(str(i), s["narration"]) for i, s in enumerate(script["sections"])]
    blocks.append(("outro", script["outro"]))

    parts = []
    for key, text in blocks:
        text = (text or "").strip()
        path = os.path.join(out_dir, f"vo_{key}.mp3")

        dur, words = (None, [])
        if text:
            dur, words = _synth_one(text, path, cfg)

        if dur is None:
            # لا صوت: مدّة تقديرية من عدد الكلمات حتى لا ينهار الإيقاع
            dur = max(3.0, len(text.split()) / 2.35)
            path = None
            print(f"[voice] الجزء {key} بلا صوت — مدّة تقديرية {dur:.1f}s")

        if not words:
            words = estimate_words(text, dur)
            if text:
                print(f"[voice] {key}: لا حدود كلمات — توزيع تقديري.")

        parts.append({"key": key, "text": text, "path": path,
                      "duration": round(float(dur), 2), "words": words})
        print(f"[voice] {key}: {parts[-1]['duration']}s، {len(words)} كلمة")
    return parts
