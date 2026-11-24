"""
بناء ملفّات ترجمة (SRT) من توقيت الكلمات الحقيقي الذي يُرجعه edge-tts.

لدى voice.py لكلّ جزءٍ قائمةَ كلمات مع لحظة نطق كلّ واحدة بدقّة جزء من
مئة. نجمعها عبر كل الأجزاء بحسب خطّها الزمني في spans.json، ونرصّها في
أسطر ترجمة بطول مناسب للقراءة (نحو ٤٢ حرفًا للسطر، ٣٬٥ ثوانٍ للعرض).

لماذا SRT وليس التسميات التلقائية ليوتيوب؟ لأن التسميات التلقائية للعربية
ضعيفة، ولأن الترجمة هنا مبنيّة من توقيت الكلمات الذي سمعه edge-tts فعلًا،
فهي أدقّ من أي استدلال صوتي.

تُستعمل لاحقًا من أي لغة: جلب التعليق الإنجليزي من voice.py بنفس الطريقة
يُنتج SRT إنجليزيًا بلا شيفرة جديدة.
"""

import os


# حدود مريحة للقراءة. السطر الأطول من هذا يُقسَم عند أقرب فراغ، والسطر
# الأقصر من الحدّ الأدنى يُدمج في الذي يليه. القيم محافظة بحيث تبقى
# الترجمة ظاهرة طوال نطق عبارتها دون أن تتأخّر عن الصوت.
MAX_LINE_CHARS = 42
MAX_LINE_SECONDS = 4.0
MIN_LINE_SECONDS = 1.1
MAX_GAP_SECONDS = 0.6          # فجوة أكبر من هذا تبدأ سطرًا جديدًا


def _fmt(t):
    """تنسيق SRT: HH:MM:SS,mmm."""
    t = max(0.0, float(t))
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    ms = int(round((s - int(s)) * 1000))
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{ms:03d}"


def _flush(buf, start, end, lines, max_chars):
    """ينشر سطر ترجمة من الكلمات المتراكمة مع ضمان ألّا يتجاوز الطول."""
    if not buf:
        return
    text = " ".join(buf).strip()
    if not text:
        return
    # قسّم السطر الطويل إلى سطرين عند أقرب فراغ من المنتصف
    if len(text) > max_chars:
        mid = len(text) // 2
        split = text.rfind(" ", 0, mid + 10)
        if split < 5:
            split = text.find(" ", mid)
        if split > 0:
            text = text[:split] + "\n" + text[split + 1:]
    lines.append((start, end, text))


def _group_words(words, max_chars, max_seconds, max_gap):
    """يرصّ كلمات الجزء الواحد في أسطر ترجمة مقروءة."""
    lines = []
    buf, start, last_end = [], None, None
    pending_chars = 0

    for w in words:
        token = str(w.get("w", "")).strip()
        if not token:
            continue
        at = float(w.get("at", 0.0))
        dur = float(w.get("dur", 0.0))
        end = at + dur

        # هل نبدأ سطرًا جديدًا؟ ثلاث حالات: فجوة طويلة، أو امتلاء الطول،
        # أو تجاوز مدّة العرض — أيّها جاء أوّلًا.
        new_line = (
            not buf
            or (last_end is not None and at - last_end > max_gap)
            or pending_chars + len(token) + 1 > max_chars
            or (start is not None and end - start > max_seconds)
        )
        if new_line and buf:
            _flush(buf, start, last_end, lines, max_chars)
            buf, start, pending_chars = [], None, 0

        if start is None:
            start = at
        buf.append(token)
        pending_chars += len(token) + 1
        last_end = end

    _flush(buf, start, last_end, lines, max_chars)
    return lines


def build(spans, parts, out_path,
          max_chars=MAX_LINE_CHARS, max_seconds=MAX_LINE_SECONDS,
          min_seconds=MIN_LINE_SECONDS, max_gap=MAX_GAP_SECONDS):
    """يبني ملفّ SRT كاملًا من الأجزاء مع إزاحة كل جزء إلى بدايته العالمية.

    spans: قائمة من {key, start, duration, ...}  من audio.layout
    parts: قائمة من {key, words, ...}            من voice.synth_script
    """
    by_key = {p["key"]: p for p in parts}
    all_lines = []

    for span in spans:
        part = by_key.get(span["key"])
        if not part or not part.get("words"):
            continue
        offset = float(span["start"])
        lines = _group_words(part["words"], max_chars, max_seconds, max_gap)
        for s, e, text in lines:
            all_lines.append((offset + s, offset + e, text))

    # ضمان الحدّ الأدنى من زمن العرض، وعدم التداخل
    all_lines.sort(key=lambda x: x[0])
    fixed = []
    for i, (s, e, text) in enumerate(all_lines):
        if e - s < min_seconds:
            e = s + min_seconds
        if fixed and s < fixed[-1][1]:                # تداخل: نكمل من آخر نهاية
            s = fixed[-1][1]
            if e <= s:
                e = s + min_seconds
        fixed.append((s, e, text))

    with open(out_path, "w", encoding="utf-8") as fh:
        for i, (s, e, text) in enumerate(fixed, 1):
            fh.write(f"{i}\n{_fmt(s)} --> {_fmt(e)}\n{text}\n\n")

    print(f"[subs] كُتب {len(fixed)} سطر ترجمة إلى {os.path.basename(out_path)}")
    return out_path
