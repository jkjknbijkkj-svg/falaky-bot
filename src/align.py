"""
محاذاة اللقطات على الكلام — قلب قاعدة «المونتاج يتبع الكلام كلمة بكلمة».

النموذج يعطي لكل لقطة العبارة التي تُقال أثناءها ("say"). هنا نبحث عن تلك
العبارة داخل مجرى الكلمات الذي أعطانا إيّاه edge-tts بتوقيتها الحقيقي،
فنعرف الثانية التي تبدأ عندها اللقطة بالضبط.

البحث يتقدّم للأمام فقط: اللقطة الثانية لا تُطابَق قبل الأولى، وإلا انقلب
ترتيب المونتاج. وما تعذّرت مطابقته يُوزّع بالتناسب بين أقرب مرساتين.
"""

import re
import unicodedata

_DIACRITICS = re.compile(r"[ً-ْٰـ]")

# نُبقي الحروف فقط. الكتلة العربية تضمّ علامات ترقيم (، ؛ ؟) فلا يصحّ
# استثناؤها كاملة، وإلا بقيت الفاصلة ملتصقة بالكلمة فتفشل المطابقة.
_PUNCT = re.compile(r"[^0-9A-Za-zء-غف-ي٠-٩]+")


def norm(token):
    """تطبيع عربي: بلا تشكيل ولا تطويل، وتوحيد الألف والياء والتاء."""
    t = unicodedata.normalize("NFKC", str(token))
    t = _DIACRITICS.sub("", t)
    t = _PUNCT.sub("", t)
    t = (t.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
          .replace("ى", "ي").replace("ة", "ه"))
    return t.strip().lower()


def _run_at(toks, phrase, i):
    """عدد الكلمات المتطابقة بدءًا من الموضع i."""
    n = 0
    while n < len(phrase) and i + n < len(toks) and toks[i + n] == phrase[n]:
        n += 1
    return n


def find_phrase(toks, phrase, start=0):
    """موضع أفضل تطابق للعبارة عند/بعد start، أو None."""
    if not phrase:
        return None

    best_i, best_n = None, 0
    for i in range(start, len(toks)):
        n = _run_at(toks, phrase, i)
        if n > best_n:
            best_i, best_n = i, n
            if n == len(phrase):
                break
    # تطابق كلمتين فأكثر يكفي، أو كلمة واحدة إن كانت العبارة كلمة
    if best_n >= min(2, len(phrase)):
        return best_i

    # وإلا نرسو على أطول كلمة مميّزة في العبارة
    for w in sorted(set(phrase), key=len, reverse=True):
        if len(w) < 3:
            continue
        for i in range(start, len(toks)):
            if toks[i] == w:
                return i
    return None


def map_beats(beats, words, total):
    """يحوّل 'say' في كل لقطة إلى 'at' بالثواني، بترتيب تصاعدي مضمون."""
    beats = list(beats or [])
    if not beats:
        return []
    if not words:
        step = total / len(beats)
        return [{**b, "at": round(i * step, 3)} for i, b in enumerate(beats)]

    toks = [norm(w.get("w", "")) for w in words]
    cursor, anchored = 0, []

    for b in beats:
        phrase = [p for p in (norm(t) for t in str(b.get("say", "")).split()) if p]
        idx = find_phrase(toks, phrase, cursor) if phrase else None
        if idx is None:
            anchored.append({**b, "at": None})
        else:
            anchored.append({**b, "at": float(words[idx].get("at", 0.0))})
            cursor = idx + 1

    # أول لقطة تبدأ مع القسم مهما كان
    anchored[0]["at"] = 0.0

    # ما لم يُطابَق يُوزّع بالتناسب بين أقرب مرساتين معروفتين
    i = 0
    while i < len(anchored):
        if anchored[i]["at"] is not None:
            i += 1
            continue
        j = i
        while j < len(anchored) and anchored[j]["at"] is None:
            j += 1
        left = anchored[i - 1]["at"]
        right = anchored[j]["at"] if j < len(anchored) else total
        gap = (right - left) / (j - i + 1)
        for k in range(i, j):
            anchored[k]["at"] = round(left + gap * (k - i + 1), 3)
        i = j

    # نضمن التصاعد: أي تراجع يُدفع للأمام قليلًا
    for i in range(1, len(anchored)):
        if anchored[i]["at"] <= anchored[i - 1]["at"]:
            anchored[i]["at"] = round(anchored[i - 1]["at"] + 0.05, 3)

    return [b for b in anchored if b["at"] < total]
