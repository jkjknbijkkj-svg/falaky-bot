"""
محرّك التصميم الصوتي — المونتاج لا يُرى فقط، بل يُسمَع.

القطع بلا نأمة صوتية يبدو خللًا لا مونتاجًا. هنا نبني طبقة صوت كاملة
ترافق كل لقطة: whoosh مع الانتقال، نبضة على القطع، riser قبل القسم
الجديد، وسجادة هواء خفيفة تحت الكل.

كل صوت **مُولّد بالكود** بـnumpy: لا تنزيل، لا مفاتيح، لا تراخيص،
ونتيجة واحدة في كل تشغيل (البذور مشتقّة من رقم اللقطة).

وميزتنا التي لا يملكها محرِر بشري: نعرف لحظة نطق كل كلمة، فالصوت يقع
على الكلمة بدقّة العيّنة لا بدقّة العين.
"""

import os
import wave

import numpy as np

SR = 44100
PEAK = 0.72          # نُبقي سَقفًا للمزج لاحقًا تحت التعليق


# ----------------------------------------------------------- أدوات التوليد

def _t(n):
    return np.arange(n, dtype=np.float64) / SR


def _rng(seed):
    return np.random.default_rng(int(seed) & 0xFFFFFFFF)


def _noise(n, seed):
    return _rng(seed).standard_normal(n)


def _band(x, lo, hi):
    """مرشّح نطاق في مجال الترددات — حادّ بما يكفي وبلا رنين مزعج.

    نشكّل المقدار بمنحنى شبيه بباترورث فلا تظهر حوافّ صناعية كما يحدث
    مع القناع المستقيم.
    """
    n = len(x)
    if n < 8:
        return x
    X = np.fft.rfft(x)
    f = np.maximum(np.fft.rfftfreq(n, 1.0 / SR), 1e-6)
    m = 1.0 / (1.0 + (lo / f) ** 4)          # تمرير عالٍ
    m *= 1.0 / (1.0 + (f / hi) ** 4)         # تمرير منخفض
    return np.fft.irfft(X * m, n=n)


def _norm(x):
    """يُعيّر كل صوت إلى ذروة ١ حتى تصير أرقام الكسب أدناه معنى حقيقيًا.

    بدونه كان الضجيج المرشَّح أخفت من الجيب المنخفض بنيويًا، فتضيع
    هسهسة القطع تحت التعليق مهما رفعنا كسبها.
    """
    p = float(np.max(np.abs(x))) if len(x) else 0.0
    return x / p if p > 1e-9 else x


def _env(n, attack=0.02, curve=1.7):
    """غلاف هجوم/تلاشٍ: الهجوم نسبة من الطول، والتلاشي أسّي."""
    if n <= 1:
        return np.ones(max(n, 1))
    a = max(int(n * attack), 1)
    e = np.ones(n)
    e[:a] = np.linspace(0.0, 1.0, a) ** 1.4
    tail = np.linspace(0.0, 1.0, n - a)
    e[a:] = (1.0 - tail) ** curve
    return e


def _sweep_noise(n, f_start, f_end, seed, segments=12):
    """ضجيج يتحرّك نطاقه من ترددٍ إلى آخر — جوهر الـwhoosh والـriser."""
    x = _noise(n, seed)
    out = np.zeros(n)
    for k in range(segments):
        s, e = k * n // segments, (k + 1) * n // segments
        if e <= s:
            continue
        frac = k / max(segments - 1, 1)
        c = f_start * (1 - frac) + f_end * frac
        out[s:e] = _band(x[s:e], c * 0.55, c * 1.95)
    return out


# ------------------------------------------------------------- الأصوات

def whoosh(dur=0.40, up=True, seed=0):
    """هسهسة انتقال. صاعدة تفتح الفكرة، هابطة تُغلقها."""
    n = int(dur * SR)
    lo, hi = (320.0, 4200.0) if up else (4200.0, 320.0)
    x = _sweep_noise(n, lo, hi, seed)
    return _norm(x * _env(n, attack=0.22, curve=1.5))


def impact(strength=1.0, seed=0):
    """نبضة القطع: جسم منخفض يهبط تردّده + طقّة عالية قصيرة."""
    dur = 0.46
    n = int(dur * SR)
    t = _t(n)
    f = 116.0 * np.exp(-t * 15.0) + 44.0
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 9.5)
    click = _band(_noise(n, seed + 7), 1900.0, 9500.0) * np.exp(-t * 58.0)
    return _norm(body * 0.85 + click * 0.22) * float(strength)


def riser(dur=1.15, seed=0):
    """تصاعد يسبق القسم الجديد — يشدّ الانتباه قبل أن يقع الشرح."""
    n = int(dur * SR)
    t = _t(n)
    air = _sweep_noise(n, 420.0, 6200.0, seed, segments=16) * 0.8
    tone = np.sin(2 * np.pi * np.cumsum(190.0 * np.exp(t * 1.25)) / SR) * 0.17
    return _norm((air + tone) * (t / max(dur, 1e-6)) ** 2.0)


def tick(seed=0):
    """طقّة ناعمة للأجزاء المكمّلة: تُشعِر بالقطع بلا أن تقطع المعنى."""
    n = int(0.09 * SR)
    t = _t(n)
    return _norm(_band(_noise(n, seed), 2600.0, 11000.0) * np.exp(-t * 85.0))


def _pad_loop(seconds, seed=0):
    """حلقة هواء قابلة للتكرار بلا خرزة: تردّداتها دورية في طول الحلقة."""
    n = int(seconds * SR)
    t = _t(n)
    base = 1.0 / seconds                       # أي عدد صحيح من هذا يُغلق الحلقة
    out = np.zeros(n)
    rng = _rng(seed)
    for mult, amp in ((55, 0.5), (82, 0.3), (110, 0.26), (165, 0.14)):
        f = round(mult / base) * base          # نُدوّر إلى أقرب تردّد دوري
        phase = rng.uniform(0, 2 * np.pi)
        lfo_m = max(round(0.07 / base), 1) * base
        lfo = 0.72 + 0.28 * np.sin(2 * np.pi * lfo_m * t + phase)
        out += np.sin(2 * np.pi * f * t + phase) * amp * lfo
    hiss = _band(_noise(n, seed + 31), 500.0, 5200.0) * 0.05
    return (out * 0.1 + hiss)


def ambience(total, seed=0):
    """سجادة هواء بطول الحلقة، مبنيّة بتكرار حلقة قصيرة حفظًا للذاكرة."""
    loop = _pad_loop(12.0, seed)
    reps = int(np.ceil(total * SR / len(loop)))
    return np.tile(loop, reps)[: int(total * SR)]


def _limit(bed, knee=0.52):
    """حدٌ ناعم: خطّي تحت الركبة، مضغوط فوقها.

    تطبيع الذروة كان يقسّم الطبقة كلّها على أعلى ضربة فيها، فتصير
    الهسهسات شبه معدومة. هنا نترك المستويات كما وُزِنت ونكتم القمم فقط.
    """
    t = PEAK * knee
    a = np.abs(bed)
    over = a > t
    if np.any(over):
        extra = (PEAK - t) * np.tanh((a[over] - t) / (PEAK - t))
        bed[over] = np.sign(bed[over]) * (t + extra)
    return bed


# --------------------------------------------------- رصف الأحداث على الخط

def _events(spec, spans):
    """يحوّل لقطات المواصفات إلى أحداث صوتية بتوقيت مطلق.

    spans[0] هو الخطّاف، فالقسم i يبدأ عند spans[i+1].
    """
    ev = []

    if spans:
        ev.append({"at": 0.25, "kind": "title"})

    for i, sec in enumerate(spec.get("sections", [])):
        j = i + 1
        if j >= len(spans):
            break
        base = float(spans[j]["start"])
        beats = sec.get("beats") or []
        for b_i, b in enumerate(beats):
            at = base + float(b.get("at", 0.0))
            if b_i == 0:
                ev.append({"at": at, "kind": "section"})
            elif b.get("split"):
                ev.append({"at": at, "kind": "tick", "i": b_i})
            else:
                ev.append({"at": at, "kind": "cut", "i": b_i})

    if len(spans) > 1:
        ev.append({"at": float(spans[-1]["start"]), "kind": "outro"})
    return ev


def _place(bed, x, at, gain=1.0, pan=0.0):
    """يضيف صوتًا في موضعه. pan: ‎-1 يسار، +1 يمين."""
    start = int(at * SR)
    if start < 0:
        x = x[-start:]
        start = 0
    if start >= bed.shape[1] or len(x) == 0:
        return
    end = min(start + len(x), bed.shape[1])
    seg = x[: end - start] * gain
    l = np.sqrt(max(0.0, (1.0 - pan) / 2.0))
    r = np.sqrt(max(0.0, (1.0 + pan) / 2.0))
    bed[0, start:end] += seg * l * 1.4142
    bed[1, start:end] += seg * r * 1.4142


def build(spec, spans, total, cfg, out_path):
    """يبني طبقة التصميم الصوتي كاملة ويكتبها WAV. يعيد المسار أو None."""
    s = cfg.get("sfx", {})
    if not s.get("enabled", True):
        print("[sfx] التصميم الصوتي مُعطَّل.")
        return None

    total = float(total)
    n = int(total * SR)
    if n <= 0:
        return None

    ev = _events(spec, spans)
    bed = np.zeros((2, n), dtype=np.float32)

    amb_gain = float(s.get("ambience_gain", 0.16))
    if amb_gain > 0:
        amb = ambience(total).astype(np.float32)
        bed[0, :len(amb)] += amb * amb_gain
        bed[1, :len(amb)] += amb * amb_gain * 0.92   # فرق طفيف يفتح الصورة

    cuts = 0
    for k, e in enumerate(ev):
        at, kind = e["at"], e["kind"]

        if kind == "title":
            _place(bed, impact(1.0, seed=1), at, 0.90)
            _place(bed, riser(1.3, seed=2), max(at - 1.3, 0.0), 0.50)

        elif kind == "section":
            # التصاعد ينتهي عند اللقطة، والنبضة تقع عليها
            _place(bed, riser(1.05, seed=100 + k), max(at - 1.05, 0.0), 0.55)
            _place(bed, impact(0.9, seed=200 + k), at, 0.60)

        elif kind == "outro":
            _place(bed, impact(0.8, seed=3), at, 0.55)

        elif kind == "tick":
            _place(bed, tick(seed=300 + k), at, 0.35,
                   pan=0.5 if k % 2 else -0.5)

        else:   # cut
            cuts += 1
            up = (cuts % 3) != 0
            dur = (0.30, 0.38, 0.46)[cuts % 3]
            # الهسهسة تمرّ من اليمين إلى اليسار كاتجاه القراءة العربية
            _place(bed, whoosh(dur, up=up, seed=400 + k), max(at - dur * 0.62, 0.0),
                   0.50, pan=0.55)
            if cuts % 2 == 0:
                _place(bed, impact(1.0, seed=500 + k), at, 0.30, pan=-0.25)

    _limit(bed)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with wave.open(out_path, "wb") as fh:
        fh.setnchannels(2)
        fh.setsampwidth(2)
        fh.setframerate(SR)
        # نكتب على دفعات حتى لا نُنشئ نسخة int16 كاملة في الذاكرة
        step = 1 << 20
        for a in range(0, n, step):
            b = min(a + step, n)
            chunk = bed[:, a:b].T
            fh.writeframes((np.clip(chunk, -1.0, 1.0) * 32767.0)
                           .astype("<i2").tobytes())

    print(f"[sfx] {len(ev)} حدثًا صوتيًا ({cuts} قطعة) على {total/60:.1f} دقيقة")
    return out_path
