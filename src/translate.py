"""
ترجمة السكريبت والعنوان والوصف إلى الإنجليزية (وغيرها) عبر Gemini.

لماذا الإنجليزية تحديدًا؟ لأن RPM (الربح لكل ألف مشاهدة) على يوتيوب
في الأسواق الناطقة بالإنجليزية (الولايات المتّحدة، بريطانيا، أستراليا،
كندا) أعلى بكثير من العربية، أحيانًا بعشر مرّات. ومسار صوت إنجليزي على
نفس الفيديو العربي يفتح الباب لذلك الجمهور بلا إنتاج ثانٍ.

نترجم فقط: السكريبت (hook + sections.narration + outro) + العنوان + الوصف.
الرسوم بلا نصّ لغوي تقريبًا، فتعمل مع أي لغة.

الاستهلاك: لغة واحدة = نداء Gemini لكل قسم + نداء للعنوان/الوصف. نستعمل
نفس مفاتيح content.py وآلية التسليم بينها.
"""

import json

import content as _content


_PROMPT = """You are a documentary narrator translating from Arabic to {target}.

Translate the following Arabic documentary narration faithfully and
naturally, keeping the same tone (calm, scientific, direct address to
the viewer). Keep names of scientists, places and units in the target
language's conventional form. Keep sentence rhythm similar to the
original so the spoken pace matches. Do not add, remove or editorialize.

Arabic text:
---
{text}
---

Return JSON only: {{"text": "the translation"}}
"""

_META_PROMPT = """Translate this YouTube video metadata from Arabic to {target},
keeping it accurate, engaging and fit for the YouTube audience.

Title (Arabic): {title}
Description (Arabic, first 800 chars):
---
{description}
---

Return JSON only:
{{"title": "translated title, <= 90 chars",
  "description": "translated description",
  "tags": ["english", "tags", "7 to 12"]}}
"""


_TARGETS = {
    "en": "English",
    "fr": "French",
    "es": "Spanish",
    "de": "German",
}


def language_name(code):
    return _TARGETS.get(code, code)


def translate_text(text, target_code, cfg):
    """يترجم فقرة واحدة. يعيد None إن فشل الاستدعاء."""
    text = (text or "").strip()
    if not text:
        return ""
    data = _content._gemini(
        _PROMPT.format(target=language_name(target_code), text=text),
        cfg, max_tokens=4096, temperature=0.5,
    )
    if not data:
        return None
    out = str(data.get("text") or "").strip()
    return out or None


def translate_script(script, target_code, cfg):
    """يترجم السكريبت كاملًا إلى اللغة الهدف. يعيد نسخة بنفس البنية.

    الترجمة تلتزم الفقرات نفسها حتى تحافظ على أقسام الصوت والتوقيت.
    beats لا نترجمها: labels اختيارية والـsay لا يُستعمل بعد مرحلة
    السكريبت (توقيت الكلمات يخرج من TTS اللغة الهدف نفسها لاحقًا).
    """
    print(f"[translate] أترجم السكريبت إلى {language_name(target_code)}…")
    out = {
        "source": script.get("source"),
        "title": script.get("title"),
        "hook": "",
        "sections": [],
        "outro": "",
        "tags": script.get("tags", []),
    }

    hook = translate_text(script.get("hook"), target_code, cfg)
    if hook is None:
        print("[translate] تعذّرت ترجمة الخطّاف — أتوقّف.")
        return None
    out["hook"] = hook

    for i, sec in enumerate(script.get("sections", [])):
        narration = translate_text(sec.get("narration"), target_code, cfg)
        if narration is None:
            print(f"[translate] تعذّرت ترجمة القسم {i + 1} — أتوقّف.")
            return None
        out["sections"].append({
            **sec,
            "narration": narration,
        })
        print(f"[translate] القسم {i + 1}/{len(script['sections'])} جاهز.")

    outro = translate_text(script.get("outro"), target_code, cfg)
    if outro is None:
        print("[translate] تعذّرت ترجمة الخاتمة — أتوقّف.")
        return None
    out["outro"] = outro
    return out


def translate_meta(meta, target_code, cfg):
    """يترجم العنوان والوصف ويولّد وسومًا بلغة الهدف.

    الوسوم الإنجليزية مهمّة: بحث يوتيوب يربط بين فيديوهات نفس الموضوع
    عبر الوسوم، وفيديو بوسوم عربية فقط لا يصل إلى البحث الإنجليزي.
    """
    print(f"[translate] أترجم بيانات يوتيوب إلى {language_name(target_code)}…")
    data = _content._gemini(
        _META_PROMPT.format(
            target=language_name(target_code),
            title=meta.get("title", ""),
            description=(meta.get("description") or "")[:800],
        ),
        cfg, max_tokens=2048, temperature=0.6,
    )
    if not data:
        return None
    return {
        "title": str(data.get("title") or "").strip()[:95],
        "description": str(data.get("description") or "").strip(),
        "tags": [str(t) for t in (data.get("tags") or [])][:12],
    }
