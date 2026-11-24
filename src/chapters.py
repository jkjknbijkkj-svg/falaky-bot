"""
فصول يوتيوب (chapters) من توقيت الأقسام.

يوتيوب يتعرّف على الفصول حين يبدأ الوصف بقائمة توقيتات: الأوّل عند
«0:00» وكل سطر «mm:ss عنوان». ثلاث فصول فأكثر تُفعِّل شريط الفصول في
مشغّل الفيديو، فتزيد اكتشافية الأقسام في البحث وتحسّن الاحتفاظ لأن
المشاهد يقفز إلى ما يهمّه بدل أن يغلق.

هذه بيانات نملكها مجّانًا من spans.json — لا حاجة لنموذج ولا لرفع ثانٍ.
"""


def _fmt_time(seconds):
    """تنسيق توقيت فصل. أقل من ساعة: m:ss، وإلّا h:mm:ss."""
    seconds = max(0, int(seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def build(spans, script):
    """يعيد نصّ الفصول جاهزًا للإلصاق في وصف الفيديو.

    الفصل الأوّل يُسمّى «المقدّمة» ويبدأ من 0:00 (شرط يوتيوب). ثم فصل لكل
    قسم بعنوانه. الخاتمة فصل أخير لتسهيل القفز إليها.
    """
    if not spans or not script:
        return ""

    chapters = []
    by_key = {s["key"]: s for s in spans}

    # المقدّمة (الخطّاف) تبدأ 0:00 حتمًا
    intro = by_key.get("intro")
    if intro:
        chapters.append((0, "المقدّمة"))

    # كل قسم فصل بعنوانه من السكريبت
    for i, sec in enumerate(script.get("sections", [])):
        span = by_key.get(str(i))
        if not span:
            continue
        heading = str(sec.get("heading", "")).strip()
        if not heading:
            heading = f"القسم {i + 1}"
        chapters.append((span["start"], heading))

    # الخاتمة
    outro = by_key.get("outro")
    if outro:
        chapters.append((outro["start"], "الخاتمة"))

    # يوتيوب يشترط 3 فصول على الأقل والأول عند 0:00
    if len(chapters) < 3:
        return ""
    if chapters[0][0] > 0:
        return ""

    return "\n".join(f"{_fmt_time(t)} {title}" for t, title in chapters)


def inject(description, chapters_text):
    """يضع كتلة الفصول بعد الخطّاف مباشرة — موضعها الأمثل للخوارزمية."""
    if not chapters_text:
        return description
    header = "— فصول الفيديو —"
    block = f"\n\n{header}\n{chapters_text}\n"

    # إن كان الوصف يحتوي كتلة فصول قديمة نستبدلها، وإلّا نُلحق
    if header in description:
        before, _, rest = description.partition(header)
        _, _, after = rest.partition("\n\n")
        return (before.rstrip() + block + after).strip()
    return (description.rstrip() + block).strip()
