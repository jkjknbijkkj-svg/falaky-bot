"""
توليد محتوى الحلقة.
- إن وُجد مفتاح GEMINI_API_KEY يُطلب من Gemini حقيقة جديدة بصيغة JSON.
- وإلا يُرجع حقيقة من قائمة احتياطية (حتى يعمل المشروع من أول تشغيل بلا أي مفتاح).

المخرجات دائمًا قاموس:
  { "title": str, "narration": str, "points": [str, str, ...] }
"""

import json
import os
import random

# حقائق احتياطية مكتوبة يدويًا ومُراجَعة — تضمن تشغيلًا فوريًا بدون مفتاح.
FALLBACK = [
    {
        "title": "الضوء كسولٌ بمقاييسنا",
        "narration": "ضوء الشمس يحتاج إلى نحو ثماني دقائق لكي يصل إلينا. فحين تنظر إلى الشمس، أنت ترى صورتها قبل ثماني دقائق، لا كما هي الآن.",
        "points": [
            "المسافة إلى الشمس نحو 150 مليون كيلومتر",
            "سرعة الضوء 300 ألف كيلومتر في الثانية",
            "لو انطفأت الشمس فجأة لعرفنا ذلك بعد 8 دقائق",
        ],
    },
    {
        "title": "لماذا السماء زرقاء؟",
        "narration": "الغلاف الجوي يُبعثر الضوء الأزرق أكثر من غيره لأن طول موجته أقصر. لذلك نرى السماء زرقاء نهارًا، وحمراء عند الغروب حين يقطع الضوء مسافة أطول.",
        "points": [
            "الضوء الأبيض يحوي كل الألوان",
            "الأزرق قصير الموجة فيتبعثر أكثر",
            "عند الغروب يتبقّى الأحمر الطويل الموجة",
        ],
    },
    {
        "title": "وزنك يتغيّر مع المكان",
        "narration": "كتلتك ثابتة أينما ذهبت، لكن وزنك يتغيّر حسب الجاذبية. على سطح القمر يصير وزنك سُدس وزنك على الأرض، رغم أن كمية المادة فيك لم تتغيّر.",
        "points": [
            "الكتلة: كمية المادة، ثابتة",
            "الوزن: قوة الجاذبية على الكتلة",
            "جاذبية القمر سُدس جاذبية الأرض",
        ],
    },
]


def _from_gemini(topic_prompt, model):
    import requests

    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    )
    instruction = (
        "أنت كاتب محتوى علمي عربي دقيق. أعطني حقيقة واحدة حول الموضوع التالي: "
        f"{topic_prompt}. "
        "أعد الإجابة بصيغة JSON فقط دون أي نص إضافي، بهذا الشكل بالضبط:\n"
        '{"title": "عنوان قصير", '
        '"narration": "فقرة سرد من 2 إلى 4 جمل، دقيقة علميًا وواضحة", '
        '"points": ["نقطة قصيرة", "نقطة قصيرة", "نقطة قصيرة"]}'
    )
    body = {"contents": [{"parts": [{"text": instruction}]}]}
    try:
        r = requests.post(
            url, params={"key": key}, json=body, timeout=60
        )
        r.raise_for_status()
        text = r.json()["candidates"][0]["content"]["parts"][0]["text"]
        # تنظيف أسوار الكود إن وُجدت
        text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(text)
        assert data.get("title") and data.get("narration") and data.get("points")
        return data
    except Exception as e:  # أي فشل -> نرجع None لنستعمل الاحتياطي
        print(f"[content] تعذّر توليد الحقيقة من Gemini ({e})؛ سأستعمل الاحتياطي.")
        return None


def get_fact(cfg):
    data = _from_gemini(cfg["topic_prompt"], cfg["gemini"]["model"])
    if data is None:
        data = random.choice(FALLBACK)
    # تقييد عدد النقاط حتى لا تزدحم الشاشة
    data["points"] = data["points"][:4]
    return data
