"""
توليد سكريبت حلقة وثائقية طويلة (٢٠ دقيقة فأكثر) على مرحلتين.

لماذا مرحلتان؟ لأن طلب سكريبت ٣٠٠٠ كلمة في نداء واحد يصطدم بحدّ التوكنز
ويُخرج نصًّا سطحيًا. فنطلب أولًا **المخطّط**، ثم نوسّع كل قسم في نداء مستقل.
النتيجة: عمق حقيقي في كل قسم بدل تلخيص متسرّع للكل.

المتطلّبات المفروضة على كل حلقة:
  • شرح دقيق خطوة بخطوة، لا إشارات عامّة
  • مثال ملموس من حياة المشاهد في كل قسم
  • مخاطبة المشاهد مباشرةً (تخيّل، لاحظ معي، جرّب)
  • أصل الفكرة: الاكتشاف ثم الاختراع
  • العلماء بأسمائهم وتواريخ حياتهم وما فعلوه بالضبط

البنية المُخرجة:
{
  "title", "hook",
  "sections": [{"heading", "narration", "visual": {...}, "keywords"}],
  "outro", "tags"
}
"""

import json
import os
import random

VISUAL_TYPES = ("flow", "bullets", "compare", "wave", "orbit", "stat",
                "timeline", "profile", "quote")

# أنواع يجب أن تظهر مرّة على الأقل في كل حلقة
REQUIRED_TYPES = ("timeline", "profile")


# ---------------------------------------------------------------- Gemini

_RULES = """قواعد الكتابة الإلزامية:
- العربية الفصحى فقط، بنبرة وثائقية رصينة. بلا عامية وبلا مزاح.
- جُمل قصيرة وواضحة. تجنّب الحشو ومبالغات مثل "مذهل" و"لا يُصدّق".
- **الدقّة مطلقة**: لا تذكر اسمًا ولا تاريخًا ولا رقمًا إلا إن كنت واثقًا منه تمامًا.
  إن لم تكن واثقًا من تاريخ، اذكر الحقبة بدل السنة.
- **خاطب المشاهد مباشرةً** في كل قسم: "تخيّل أنك…"، "لاحظ معي…"، "جرّب أن…".
  اجعله يشعر أنك تشرح له هو، لا أنك تلقي محاضرة.
- **مثال ملموس في كل قسم** من أدوات يستعملها المشاهد يوميًا.
- احكِ **أصل الفكرة**: من لاحظها أول مرّة، وكيف تحوّلت من اكتشاف إلى اختراع.
- عند ذكر عالِم: اسمه كاملًا، سنتا ميلاده ووفاته، وماذا فعل بالضبط ومتى."""

_OUTLINE_PROMPT = """أنت كاتب سيناريو وثائقي علمي بالعربية الفصحى.

صمّم مخطّط حلقة وثائقية مدّتها نحو {minutes} دقيقة عن موضوع واحد من هذا المجال:
{niche}

{rules}

بنية الحلقة المطلوبة ({min_sections} إلى {max_sections} قسمًا):
1. أقسام تشرح المبدأ الفيزيائي خطوة بخطوة.
2. قسم أو أكثر عن **الاكتشاف الأصلي**: من لاحظ الظاهرة ومتى وكيف.
3. قسم أو أكثر عن **العلماء**: حياتهم وتواريخها وإسهامهم (نوع المشهد profile).
4. قسم **خط زمني** يربط المحطّات بالسنوات (نوع المشهد timeline).
5. أقسام عن التطبيق اليومي والمقايضات الهندسية.

أنواع المشاهد المتاحة: flow, bullets, compare, wave, orbit, stat, timeline, profile, quote
يجب أن يظهر timeline مرّة على الأقل، و profile مرّة على الأقل.

أعد JSON فقط بهذا الشكل:
{{"title":"عنوان الحلقة",
"hook":"فقرة الخطّاف: مفارقة محسوسة من حياة المشاهد، ٣ إلى ٥ جمل",
"outro":"خاتمة من ثلاث جمل",
"tags":["وسم","وسم","وسم"],
"sections":[{{"heading":"عنوان القسم","angle":"ماذا يغطّي هذا القسم بالضبط وما المثال المستعمل فيه","visual_type":"flow"}}]}}
"""

_SECTION_PROMPT = """أنت تكتب قسمًا واحدًا من حلقة وثائقية عربية بعنوان: {title}

القسم: {heading}
زاويته: {angle}

سياق الحلقة (عناوين الأقسام بالترتيب):
{outline}

{rules}

اكتب نصّ التعليق لهذا القسم فقط، نحو {words} كلمة، متّصلًا بما قبله ومنتهيًا بما يمهّد لما بعده.
لا تُعِد عنوان القسم داخل النص، ولا تكتب مقدّمة عن نفسك.

نوع المشهد البصري لهذا القسم: {visual_type}
املأ items بحسب النوع:
- flow: ٣ إلى ٥ مراحل مرتّبة.
- bullets: ٣ إلى ٤ نقاط قصيرة.
- compare: عنصران فقط بالشكل "الخيار|الميزة|الثمن".
- wave: ٢ إلى ٣ تسميات قصيرة.
- orbit: ٢ إلى ٣ تسميات قصيرة.
- stat: ثلاثة عناصر: [الرقم, سطر توضيح, سطر ثانوي].
- timeline: ٣ إلى ٥ عناصر بالشكل "السنة|الحدث" مرتّبة زمنيًا.
- profile: ثلاثة عناصر: [اسم العالِم, "سنة الميلاد — سنة الوفاة", إسهامه في سطر].
- quote: عنصران: [نصّ الاقتباس القصير, اسم قائله].

أعد JSON فقط:
{{"narration":"نص التعليق",
"visual":{{"type":"{visual_type}","items":["..."],"caption":"سطر قصير يلخّص المشهد"}},
"keywords":["english term","english term"]}}
"""


def _gemini(prompt, cfg, max_tokens=4096, temperature=0.8):
    import requests

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None

    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature,
                             "maxOutputTokens": max_tokens},
    }
    for model in cfg["gemini"]["models"]:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        try:
            r = requests.post(url, params={"key": key}, json=body, timeout=180)
            if r.status_code != 200:
                print(f"[content] {model} رفض ({r.status_code})؛ أجرّب التالي.")
                continue
            text = r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
            for mark in ("```json", "```"):
                if text.startswith(mark):
                    text = text[len(mark):]
            text = text.removesuffix("```").strip()
            return json.loads(text)
        except Exception as e:
            print(f"[content] فشل {model}: {e}")
    return None


def _build_outline(cfg):
    ep = cfg["episode"]
    prompt = _OUTLINE_PROMPT.format(
        minutes=ep["target_minutes"],
        niche=cfg["niche"],
        rules=_RULES,
        min_sections=ep["min_sections"],
        max_sections=ep["max_sections"],
    )
    data = _gemini(prompt, cfg, max_tokens=4096, temperature=0.9)
    if not data or not data.get("sections"):
        return None

    secs = []
    for raw in data["sections"][: ep["max_sections"]]:
        if not isinstance(raw, dict) or not raw.get("heading"):
            continue
        vt = str(raw.get("visual_type") or "bullets").lower().strip()
        secs.append({
            "heading": str(raw["heading"]).strip(),
            "angle": str(raw.get("angle") or "").strip(),
            "visual_type": vt if vt in VISUAL_TYPES else "bullets",
        })
    if len(secs) < 3:
        return None

    # نضمن وجود الأنواع الإلزامية حتى لو أغفلها المخطّط
    present = {s["visual_type"] for s in secs}
    for need in REQUIRED_TYPES:
        if need not in present:
            for s in secs:
                if s["visual_type"] in ("bullets", "flow"):
                    s["visual_type"] = need
                    break

    data["sections"] = secs
    return data


def _expand_section(outline, idx, cfg):
    ep = cfg["episode"]
    stub = outline["sections"][idx]
    headings = "\n".join(f"{i+1}. {s['heading']}"
                         for i, s in enumerate(outline["sections"]))
    prompt = _SECTION_PROMPT.format(
        title=outline.get("title", ""),
        heading=stub["heading"],
        angle=stub["angle"],
        outline=headings,
        rules=_RULES,
        words=ep.get("words_per_section", 260),
        visual_type=stub["visual_type"],
    )
    data = _gemini(prompt, cfg, max_tokens=3072, temperature=0.75)
    if not data or not str(data.get("narration") or "").strip():
        return None

    vis = data.get("visual") or {}
    vtype = str(vis.get("type") or stub["visual_type"]).lower().strip()
    if vtype not in VISUAL_TYPES:
        vtype = stub["visual_type"]
    items = [str(i).strip() for i in (vis.get("items") or []) if str(i).strip()][:5]
    if not items:
        items = [stub["heading"]]

    return {
        "heading": stub["heading"],
        "narration": str(data["narration"]).strip(),
        "visual": {"type": vtype, "items": items,
                   "caption": str(vis.get("caption") or "").strip()},
        "keywords": [str(k) for k in (data.get("keywords") or [])][:4],
    }


# ---------------------------------------------------------------- الاحتياطي

FALLBACK_EPISODES = [
    {
        "title": "البطارية: قصّة قرنين من مطاردة الكهرباء",
        "hook": "في جيبك الآن جهاز يختزن طاقة تكفي لتشغيل مصباح ساعات طويلة، في حجم قطعة بسكويت. لم يسقط هذا من السماء. وراءه سلسلة من المصادفات والخلافات العلمية امتدّت أكثر من قرنين. وأغربها أن كل شيء بدأ بساقَي ضفدع ميّت.",
        "sections": [
            {
                "heading": "ساقا الضفدع",
                "narration": "في ثمانينيات القرن الثامن عشر كان الطبيب الإيطالي لويجي غالفاني يشرّح ضفدعًا في مختبره في بولونيا. لامس مشرطه المعدني ساق الضفدع، فانتفضت الساق فجأة كأنها حيّة. تخيّل المشهد: حيوان ميّت منذ ساعات، وعضلته تتحرّك أمام عينيك. استنتج غالفاني أن في أنسجة الحيوان كهرباء خاصّة سمّاها الكهرباء الحيوانية. كان مخطئًا في التفسير، لكن ملاحظته كانت صحيحة تمامًا، وهذا وحده يكفي لتغيير التاريخ. لاحظ معي القاعدة التي تتكرّر في كل اكتشاف: الملاحظة الدقيقة أثمن من التفسير السريع.",
                "visual": {
                    "type": "profile",
                    "items": ["لويجي غالفاني", "١٧٣٧ — ١٧٩٨", "لاحظ انقباض عضلة الضفدع بتأثير المعدن"],
                    "caption": "ملاحظة صحيحة، وتفسير خاطئ",
                },
                "keywords": ["old laboratory", "science history", "anatomy"],
            },
            {
                "heading": "الخلاف الذي أنتج البطارية",
                "narration": "لم يقتنع زميله أليساندرو فولتا بتفسير الكهرباء الحيوانية. كان يرى أن مصدر الكهرباء ليس الضفدع، بل المعدنان المختلفان اللذان لامساه، وأن النسيج الرطب مجرّد وسيط. ولكي يثبت ذلك، فعل شيئًا بسيطًا وحاسمًا: أزال الحيوان من المعادلة تمامًا. رصّ أقراصًا من الزنك وأقراصًا من النحاس بالتناوب، وفصل بينها بورق مبلّل بماء مالح. وفي عام ألف وثمانمئة حصل على تيار كهربائي مستمرّ لأول مرّة في التاريخ. هذا هو العمود الفولتي. الخلاف العلمي هنا لم يكن عائقًا، بل كان هو المحرّك.",
                "visual": {
                    "type": "flow",
                    "items": ["قرص زنك", "ورق مبلّل بمحلول ملحي", "قرص نحاس", "تكرار الترتيب", "تيار مستمرّ"],
                    "caption": "العمود الفولتي، ١٨٠٠",
                },
                "keywords": ["voltaic pile", "zinc copper discs", "science museum"],
            },
            {
                "heading": "فولتا: الرجل والتاريخ",
                "narration": "وُلد أليساندرو فولتا في مدينة كومو الإيطالية عام ألف وسبعمئة وخمسة وأربعين، وعاش حتى عام ألف وثمانمئة وسبعة وعشرين. لم يكن مخترعًا منعزلًا، بل أستاذ فيزياء عرض اختراعه على الجمعية الملكية في لندن، فانتشر الخبر في أوروبا خلال أشهر. وتكريمًا له سُمّيت وحدة فرق الجهد باسمه: الفولت. في كل مرّة تقرأ على شاحنك عبارة خمسة فولت، أنت تقرأ اسم رجل مات قبل مئتي عام.",
                "visual": {
                    "type": "profile",
                    "items": ["أليساندرو فولتا", "١٧٤٥ — ١٨٢٧", "بنى أول بطارية حقيقية عام ١٨٠٠"],
                    "caption": "الفولت: وحدة تحمل اسمه",
                },
                "keywords": ["Como Italy", "historical portrait frame", "physics history"],
            },
            {
                "heading": "من الفضول إلى الاستعمال",
                "narration": "بقي العمود الفولتي لعقود أداة مختبر لا أكثر. المشكلة أنه ينفد ولا يُشحن. وفي عام ألف وثمانمئة وتسعة وخمسين قدّم الفرنسي غاستون بلانتيه حلًّا مختلفًا: خليّة من الرصاص وحمض الكبريتيك يمكن إعادة شحنها مرّات ومرّات. هذه هي البطارية القابلة للشحن الأولى، وهي نفسها التي تدير سيارتك اليوم بعد أكثر من قرن ونصف. تخيّل اختراعًا تستعمله يوميًا ولم يتغيّر مبدؤه منذ عهد نابليون الثالث.",
                "visual": {
                    "type": "compare",
                    "items": ["عمود فولتا|تيار مستمرّ أول مرّة|ينفد ولا يُشحن", "خليّة بلانتيه|قابلة للشحن|ثقيلة جدًا"],
                    "caption": "القفزة: من الاستهلاك إلى الشحن",
                },
                "keywords": ["lead acid battery", "car battery", "industrial history"],
            },
            {
                "heading": "خط زمني يختصر قرنين",
                "narration": "دعنا نرتّب المحطّات حتى تتضح الصورة. ملاحظة غالفاني في ثمانينيات القرن الثامن عشر، ثم عمود فولتا عام ألف وثمانمئة، ثم خليّة بلانتيه القابلة للشحن عام ألف وثمانمئة وتسعة وخمسين. وبعد قرن كامل من التحسينات الصغيرة جاءت القفزة الكبرى: ستانلي ويتينغهام يبني أول بطارية ليثيوم قابلة للشحن في شركة إكسون عام ألف وتسعمئة وستة وسبعين. لاحظ أن المسافة بين كل محطّة والتي تليها ليست ثابتة؛ العلم لا يتقدّم بخطوات متساوية.",
                "visual": {
                    "type": "timeline",
                    "items": ["١٧٨٠|غالفاني يلاحظ انقباض العضلة", "١٨٠٠|فولتا يبني العمود الفولتي", "١٨٥٩|بلانتيه وأول بطارية تُشحن", "١٩٧٦|ويتينغهام وبطارية الليثيوم"],
                    "caption": "قرنان في أربع محطّات",
                },
                "keywords": ["timeline history", "archive documents", "invention"],
            },
            {
                "heading": "ثلاثة رجال وجائزة نوبل",
                "narration": "بطارية الليثيوم الأولى كانت خطرة وغير مستقرّة، فأوقفت إكسون المشروع. هنا دخل جون غودإنَف، وكان أستاذًا في أكسفورد، فاكتشف عام ألف وتسعمئة وثمانين أن استعمال أكسيد الكوبالت كمصعد يضاعف الجهد ويجعل الخليّة أكثر أمانًا. ثم جاء الكيميائي الياباني أكيرا يوشينو فاستبدل الليثيوم المعدني الخطر بمادة كربونية عام ألف وتسعمئة وخمسة وثمانين، فصارت البطارية صالحة للاستعمال اليومي. وفي عام ألفين وتسعة عشر نال الثلاثة جائزة نوبل في الكيمياء معًا. الطريف أن غودإنَف نالها وعمره سبعة وتسعون عامًا، فصار أكبر من حصل عليها في التاريخ.",
                "visual": {
                    "type": "profile",
                    "items": ["جون غودإنَف", "١٩٢٢ — ٢٠٢٣", "أكسيد الكوبالت كمصعد، ١٩٨٠"],
                    "caption": "نوبل الكيمياء ٢٠١٩",
                },
                "keywords": ["chemistry laboratory", "nobel prize", "research scientist"],
            },
            {
                "heading": "ماذا يحدث داخل بطاريتك الآن",
                "narration": "افتح هاتفك وانظر إلى نسبة الشحن. ما يحدث خلف ذلك الرقم بسيط في جوهره. عند الشحن تُجبَر أيونات الليثيوم على مغادرة طبقة أكسيد الكوبالت والانتقال عبر سائل موصّل لتستقرّ بين طبقات الكربون. وعند الاستعمال تعود الأيونات في الاتجاه المعاكس، ويرافق عودتها سريان الإلكترونات في الدارة الخارجية، وهذا السريان هو ما يشغّل شاشتك. البطارية إذن ليست خزّانًا للكهرباء، بل مكان تذهب إليه الأيونات وتعود.",
                "visual": {
                    "type": "orbit",
                    "items": ["أيون ليثيوم", "طبقة كربون", "ذهاب وعودة"],
                    "caption": "البطارية: ذهاب أيونات وعودتها",
                },
                "keywords": ["lithium ion battery", "smartphone battery", "electrons"],
            },
            {
                "heading": "لماذا تشيخ البطاريات",
                "narration": "جرّب أن تتذكّر هاتفك بعد عامين من الاستعمال: الشحن نفسه لم يعد يكفي اليوم كلّه. السبب أن كل دورة شحن تترك أثرًا صغيرًا؛ طبقة رقيقة تتراكم على سطح المصعد وتحبس جزءًا من الليثيوم بعيدًا عن الخدمة. الحرارة تسرّع هذا التراكم، ولهذا يضرّ ترك الهاتف في سيارة مشمسة أكثر مما يضرّه الاستعمال المكثّف. الشيخوخة هنا ليست عطلًا، بل حساب تراكمي لا مفرّ منه.",
                "visual": {
                    "type": "stat",
                    "items": ["٨٠٪", "من السعة بعد نحو ٥٠٠ دورة", "والحرارة تسرّع ذلك"],
                    "caption": "كل دورة تترك أثرًا",
                },
                "keywords": ["battery degradation", "phone heat", "charging cycle"],
            },
        ],
        "outro": "من ساق ضفدع في مختبر إيطالي إلى جائزة نوبل بعد مئتين وأربعين عامًا، لم تكن الطريق مستقيمة ولا سريعة. كل محطّة فيها بدأت بشخص رفض أن يمرّ على ملاحظة غريبة دون أن يسأل لماذا. وفي المرّة القادمة حين ترى نسبة الشحن تنقص، تذكّر أنك تحمل في يدك خلاصة قرنين من الفضول.",
        "tags": ["فيزياء", "بطارية", "تاريخ العلوم", "ليثيوم", "فولتا", "تعليم", "علوم"],
    },
]


# ---------------------------------------------------------------- التحقّق

def _clean_sections(sections, cfg):
    out = []
    for raw in sections[: cfg["episode"]["max_sections"]]:
        narration = str(raw.get("narration") or "").strip()
        if not narration:
            continue
        vis = raw.get("visual") or {}
        vtype = str(vis.get("type") or "bullets").lower().strip()
        if vtype not in VISUAL_TYPES:
            vtype = "bullets"
        items = [str(i).strip() for i in (vis.get("items") or []) if str(i).strip()][:5]
        if not items:
            items = [str(raw.get("heading") or "…")]
        out.append({
            "heading": str(raw.get("heading") or "").strip(),
            "narration": narration,
            "visual": {"type": vtype, "items": items,
                       "caption": str(vis.get("caption") or "").strip()},
            "keywords": [str(k) for k in (raw.get("keywords") or [])][:4],
        })
    return out


def build_script(cfg):
    outline = _build_outline(cfg)

    if outline:
        print(f"[content] المخطّط جاهز: {outline.get('title')} "
              f"— {len(outline['sections'])} أقسام")
        sections = []
        for i in range(len(outline["sections"])):
            sec = _expand_section(outline, i, cfg)
            if sec:
                sections.append(sec)
                print(f"[content] القسم {i+1}/{len(outline['sections'])}: "
                      f"{sec['heading']} ({len(sec['narration'].split())} كلمة)")
            else:
                print(f"[content] تعذّر توسيع القسم {i+1}؛ سأتخطّاه.")

        sections = _clean_sections(sections, cfg)
        if len(sections) >= 3:
            return {
                "source": "gemini",
                "title": str(outline.get("title") or "حلقة جديدة").strip(),
                "hook": str(outline.get("hook") or "").strip(),
                "sections": sections,
                "outro": str(outline.get("outro") or "").strip(),
                "tags": [str(t) for t in (outline.get("tags") or [])][:12]
                        or ["فيزياء", "علوم", "تعليم"],
            }
        print("[content] الأقسام الناجحة قليلة؛ سأستعمل الحلقة الاحتياطية.")

    data = random.choice(FALLBACK_EPISODES)
    print("[content] استُعملت حلقة احتياطية — أقصر من الهدف ولن تُنشر تلقائيًا.")
    return {
        "source": "fallback",
        "title": data["title"],
        "hook": data["hook"],
        "sections": _clean_sections(data["sections"], cfg),
        "outro": data["outro"],
        "tags": data["tags"],
    }


def build_meta(script, cfg):
    """وصف ووسوم يوتيوب، مع فهرس الأقسام."""
    body = [script["hook"], "", "— محاور الحلقة —"]
    for s in script["sections"]:
        if s["heading"]:
            body.append(f"• {s['heading']}")
    body += ["", script["outro"], "", "#فيزياء #علوم #تاريخ_العلوم #إلكترونيات #تعليم"]
    return {
        "title": f"{script['title']} | {cfg['channel_name']}",
        "description": "\n".join(body).strip(),
        "tags": script["tags"],
    }
