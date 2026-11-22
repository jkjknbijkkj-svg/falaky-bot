"""
توليد سكريبت الحلقة ببنية وثائقية حقيقية.

البنية المُخرجة (ثابتة دائمًا):
{
  "title": str,
  "hook": str,                      # أول 10-15 ثانية: سؤال يشدّ المشاهد
  "sections": [
      {
        "heading": str,             # عنوان القسم (قصير)
        "narration": str,           # نص التعليق لهذا القسم
        "visual": {                 # توجيه بصري لمشهد Manim
            "type": "flow|bullets|compare|wave|orbit|stat",
            "items": [...],
            "caption": str
        },
        "keywords": [str, ...]      # كلمات إنجليزية للقطات ستوك مساندة
      }, ...
  ],
  "outro": str,
  "tags": [str, ...]
}

إن لم يوجد GEMINI_API_KEY (أو فشل الطلب) نرجع لحلقة احتياطية كاملة
ومكتوبة بعناية — المشروع يعمل من أول تشغيل بلا أي مفتاح.
"""

import json
import os
import random

VISUAL_TYPES = ("flow", "bullets", "compare", "wave", "orbit", "stat")


# ---------------------------------------------------------------- الاحتياطي

FALLBACK_EPISODES = [
    {
        "title": "لماذا يسخن شاحن هاتفك؟",
        "hook": "ضع يدك على شاحن هاتفك بعد نصف ساعة. إنه دافئ. تلك الحرارة ليست عيبًا في الشاحن، بل هي قانون فيزيائي لا يمكن لأي مهندس أن يتجاوزه.",
        "sections": [
            {
                "heading": "رحلة الكهرباء",
                "narration": "الكهرباء التي تصل بيتك تأتي بجهد مرتفع ومتردّد، يتغيّر اتجاهه عشرات المرات في الثانية. لكن بطارية هاتفك لا تفهم هذه اللغة إطلاقًا؛ فهي تحتاج تيارًا ثابتًا بجهد منخفض. مهمة الشاحن كلها هي الترجمة بين هاتين اللغتين.",
                "visual": {
                    "type": "flow",
                    "items": ["الشبكة ٢٢٠ فولت", "محوّل خافض", "مقوّم", "مرشّح", "البطارية ٥ فولت"],
                    "caption": "الشاحن سلسلة ترجمة، لا مجرد سلك",
                },
                "keywords": ["power grid cables", "phone charging", "electricity pylon"],
            },
            {
                "heading": "أين تذهب الطاقة المفقودة؟",
                "narration": "في كل خطوة من هذه الخطوات تضيع نسبة من الطاقة. لا تختفي هذه الطاقة، لأن اختفاءها مستحيل؛ بل تتحوّل إلى الشكل الوحيد المتبقّي أمامها، وهو الحرارة. الشاحن الجيد يحوّل نحو تسعين بالمئة من الطاقة، والعشرة الباقية هي ما تشعر به تحت أصابعك.",
                "visual": {
                    "type": "stat",
                    "items": ["٩٠٪", "من الطاقة تصل للبطارية", "١٠٪ تتحوّل حرارة"],
                    "caption": "الطاقة لا تفنى، بل تغيّر شكلها",
                },
                "keywords": ["heat thermal", "circuit board closeup", "energy"],
            },
            {
                "heading": "لماذا الحرارة تحديدًا؟",
                "narration": "داخل أسلاك الشاحن تندفع الإلكترونات، فتصطدم بذرّات المعدن في طريقها. كل اصطدام يسرق جزءًا صغيرًا من طاقة حركتها ويحوّله إلى اهتزاز في الذرّة. واهتزاز الذرّات هو بالضبط ما نسمّيه حرارة. المقاومة الكهربائية ليست سوى اسم آخر لهذا الازدحام.",
                "visual": {
                    "type": "orbit",
                    "items": ["إلكترون", "ذرّة معدن", "اصطدام = حرارة"],
                    "caption": "المقاومة = ازدحام الإلكترونات",
                },
                "keywords": ["atoms molecules", "electron particles", "abstract energy"],
            },
            {
                "heading": "الشحن السريع والمقايضة",
                "narration": "الشحن السريع يدفع طاقة أكبر في الزمن نفسه، والحرارة المتولّدة تتناسب مع مربّع التيار. أي أن مضاعفة التيار لا تضاعف الحرارة، بل تجعلها أربعة أضعاف. لذلك تراقب الهواتف الحديثة حرارتها لحظة بلحظة، وتخفض سرعة الشحن عمدًا كي تحمي البطارية من التلف.",
                "visual": {
                    "type": "compare",
                    "items": ["شحن عادي|حرارة قليلة|عمر أطول", "شحن سريع|حرارة أربعة أضعاف|راحة أكبر"],
                    "caption": "لا توجد وجبة مجانية في الفيزياء",
                },
                "keywords": ["fast charging phone", "smartphone battery", "temperature"],
            },
        ],
        "outro": "في المرة القادمة حين تلمس شاحنًا دافئًا، تذكّر أنك تلمس أثرًا مباشرًا لقانون حفظ الطاقة. الحرارة ليست خطأ في التصميم، بل هي الثمن الذي تدفعه الفيزياء مقابل كل تحويل.",
        "tags": ["فيزياء", "إلكترونيات", "شاحن", "بطارية", "تعليم", "علوم"],
    },
    {
        "title": "كيف يفكّر المعالج؟",
        "hook": "داخل هاتفك قطعة سيليكون أصغر من ظفرك، تتخذ مليارات القرارات في الثانية الواحدة. لكنها في الحقيقة لا تعرف سوى شيء واحد: هل يمرّ التيار أم لا؟",
        "sections": [
            {
                "heading": "المفتاح الذي بدّل العالم",
                "narration": "اللبنة الأساسية للمعالج هي الترانزستور، وهو ببساطة مفتاح كهربائي بلا أجزاء متحرّكة. تضع جهدًا على بوّابته فيسمح للتيار بالمرور، وترفع الجهد فيقطعه. لا شيء أكثر من ذلك. لكن حين تضع عشرات المليارات منها معًا، يولد شيء يشبه التفكير.",
                "visual": {
                    "type": "flow",
                    "items": ["جهد على البوّابة", "قناة موصّلة", "تيار يمرّ", "١", "٠"],
                    "caption": "الترانزستور: مفتاح بلا حركة",
                },
                "keywords": ["microchip closeup", "semiconductor wafer", "circuit board"],
            },
            {
                "heading": "من مفتاح إلى منطق",
                "narration": "عند ربط عدّة ترانزستورات بترتيب معيّن نحصل على بوّابة منطقية. بوّابة تعطي واحدًا فقط إذا كان المدخلان واحدًا، وأخرى تعطي واحدًا إذا كان أحدهما كذلك. من هذه القواعد البسيطة وحدها يُبنى الجمع، ثم الضرب، ثم كل برنامج استخدمته في حياتك.",
                "visual": {
                    "type": "bullets",
                    "items": ["بوّابة AND: الاثنان معًا", "بوّابة OR: أحدهما يكفي", "بوّابة NOT: اقلب القيمة", "منها يُبنى الحساب كلّه"],
                    "caption": "المنطق يولد من المفاتيح",
                },
                "keywords": ["logic gates", "binary code", "computer chip macro"],
            },
            {
                "heading": "لماذا السرعة لها سقف؟",
                "narration": "كل مرّة يبدّل الترانزستور حالته يستهلك قليلًا من الطاقة ويطلق قليلًا من الحرارة. وبما أن هذا يحدث مليارات المرّات في الثانية، تصبح الحرارة هي العائق الحقيقي أمام السرعة. ليست الفكرة أن نصنع معالجًا أسرع، بل أن نصنع معالجًا نستطيع تبريده.",
                "visual": {
                    "type": "stat",
                    "items": ["٣ مليار", "عملية تبديل في الثانية", "لكل ترانزستور"],
                    "caption": "الحرارة هي سقف السرعة",
                },
                "keywords": ["cpu cooling fan", "heatsink computer", "thermal paste"],
            },
            {
                "heading": "الحلّ: التوازي",
                "narration": "حين عجز المهندسون عن رفع السرعة أكثر، غيّروا السؤال. بدل معالج واحد سريع جدًا، لماذا لا نضع عدّة أنوية تعمل معًا؟ هذا سبب وجود ثمانية أنوية في هاتفك اليوم. لم نكسر حدود الفيزياء، بل التففنا حولها.",
                "visual": {
                    "type": "compare",
                    "items": ["نواة واحدة|سرعة عالية|حرارة خانقة", "عدّة أنوية|سرعة معتدلة|عمل متوازٍ"],
                    "caption": "لا نكسر الحدود، بل نلتفّ حولها",
                },
                "keywords": ["multi core processor", "server datacenter", "silicon chip"],
            },
        ],
        "outro": "المعالج لا يفكّر في الحقيقة. إنه يفتح ويغلق مفاتيح بسرعة تفوق خيالنا. والذكاء الذي نراه ليس في المفاتيح، بل في الترتيب الذي وضعناها به.",
        "tags": ["فيزياء", "معالج", "إلكترونيات", "حاسوب", "تعليم", "علوم"],
    },
]


# ---------------------------------------------------------------- Gemini

_PROMPT = """أنت كاتب سيناريو وثائقي علمي بالعربية الفصحى، بنبرة رصينة تشبه الأفلام الوثائقية الكبرى.

اكتب حلقة واحدة عن موضوع من هذا المجال:
{niche}

قواعد الكتابة الإلزامية:
- العربية الفصحى فقط، بلا عامية وبلا مزاح.
- جُمل قصيرة وواضحة. تجنّب الحشو والمبالغات مثل "مذهل" و"لا يُصدّق".
- ابدأ بخطّاف يطرح سؤالًا أو مفارقة محسوسة من حياة المشاهد اليومية.
- كل قسم يبني على الذي قبله، وينتهي بفهم جديد لا بمعلومة معزولة.
- الدقة العلمية مطلقة. لا تذكر رقمًا إلا إن كنت واثقًا منه.
- اجعل مجموع التعليق مناسبًا لفيديو مدّته نحو {minutes} دقائق.
- عدد الأقسام بين {min_sections} و {max_sections}.

لكل قسم اختر نوع مشهد بصري من هذه الأنواع فقط:
- "flow": سلسلة مراحل متتابعة. items = قائمة مراحل مرتّبة (٣ إلى ٥).
- "bullets": نقاط تُكشف تباعًا. items = قائمة نقاط قصيرة (٣ إلى ٤).
- "compare": مقارنة بين خيارين. items = عنصران فقط، كل عنصر نص يفصل بين أجزائه رمز | هكذا: "الخيار|الميزة|الثمن".
- "wave": شرح موجة أو تردد أو إشارة. items = ٢ إلى ٣ تسميات قصيرة.
- "orbit": ذرّات أو إلكترونات أو جسيمات. items = ٢ إلى ٣ تسميات قصيرة.
- "stat": رقم واحد كبير. items = ثلاثة عناصر بالترتيب: [الرقم, سطر توضيح, سطر ثانوي].

أعد JSON فقط، بلا أي نص قبله أو بعده، بهذا الشكل بالضبط:
{{"title":"عنوان الحلقة",
"hook":"فقرة الخطّاف",
"sections":[{{"heading":"عنوان القسم","narration":"نص التعليق","visual":{{"type":"flow","items":["..."],"caption":"سطر قصير"}},"keywords":["english term","english term"]}}],
"outro":"خاتمة من جملتين",
"tags":["وسم","وسم"]}}
"""


def _call_gemini(cfg):
    import requests

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        print("[content] لا يوجد GEMINI_API_KEY — سأستعمل حلقة احتياطية.")
        return None

    ep = cfg["episode"]
    prompt = _PROMPT.format(
        niche=cfg["niche"],
        minutes=ep["target_minutes"],
        min_sections=ep["min_sections"],
        max_sections=ep["max_sections"],
    )
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.85, "maxOutputTokens": 4096},
    }

    for model in cfg["gemini"]["models"]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            r = requests.post(url, params={"key": key}, json=body, timeout=120)
            if r.status_code != 200:
                print(f"[content] {model} رفض الطلب ({r.status_code})؛ أجرّب التالي.")
                continue
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
            text = text.strip()
            for mark in ("```json", "```"):
                if text.startswith(mark):
                    text = text[len(mark):]
            text = text.removesuffix("```").strip()
            data = json.loads(text)
            print(f"[content] تم توليد السكريبت عبر {model}")
            return data
        except Exception as e:
            print(f"[content] فشل {model}: {e}")
    return None


# ---------------------------------------------------------------- التحقّق

def _clean(data, cfg):
    """يضمن أن السكريبت صالح بنيويًا مهما كان مصدره."""
    ep = cfg["episode"]
    out = {
        "title": str(data.get("title") or "حلقة جديدة").strip(),
        "hook": str(data.get("hook") or "").strip(),
        "outro": str(data.get("outro") or "").strip(),
        "tags": [str(t) for t in (data.get("tags") or [])][:12],
    }

    sections = []
    for raw in (data.get("sections") or [])[: ep["max_sections"]]:
        if not isinstance(raw, dict):
            continue
        narration = str(raw.get("narration") or "").strip()
        if not narration:
            continue
        vis = raw.get("visual") or {}
        vtype = str(vis.get("type") or "bullets").lower().strip()
        if vtype not in VISUAL_TYPES:
            vtype = "bullets"
        items = [str(i).strip() for i in (vis.get("items") or []) if str(i).strip()][:5]
        if not items:
            items = [str(raw.get("heading") or "")] or ["…"]
        sections.append({
            "heading": str(raw.get("heading") or "").strip(),
            "narration": narration,
            "visual": {
                "type": vtype,
                "items": items,
                "caption": str(vis.get("caption") or "").strip(),
            },
            "keywords": [str(k) for k in (raw.get("keywords") or [])][:4],
        })

    if len(sections) < 2:
        return None
    out["sections"] = sections
    if not out["tags"]:
        out["tags"] = ["فيزياء", "علوم", "تعليم"]
    return out


def build_script(cfg):
    data = _call_gemini(cfg)
    script = _clean(data, cfg) if data else None
    if script is None:
        script = _clean(random.choice(FALLBACK_EPISODES), cfg)
        print("[content] استُعملت حلقة احتياطية.")
    return script


def build_meta(script, cfg):
    """وصف ووسوم يوتيوب."""
    body = [script["hook"], ""]
    for s in script["sections"]:
        if s["heading"]:
            body.append(f"• {s['heading']}")
    body += ["", script["outro"], "", "#فيزياء #علوم #إلكترونيات #تعليم"]
    return {
        "title": f"{script['title']} | {cfg['channel_name']}",
        "description": "\n".join(body).strip(),
        "tags": script["tags"],
    }
