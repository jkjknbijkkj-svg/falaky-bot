"""
المنظّم — يعمل على مراحل حتى يمكن رسم الأقسام بالتوازي.

    python src/main.py                      # كل المراحل بالتتابع (محليًا)
    python src/main.py --stage script       # السكريبت + التعليق + الخط الزمني
    python src/main.py --stage render --index 3
    python src/main.py --stage render --index intro
    python src/main.py --stage assemble     # التركيب (و--publish للرفع)

المرحلة الأولى تكتب output/work/spec.json و spans.json و indices.json،
ثم يرسم كل قسم في وظيفة مستقلّة، وأخيرًا تجمعها مرحلة التركيب.
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import content
import voice
import audio
import visuals
import render
import portraits
import align
import montage

OUT = os.path.join(ROOT, "output")
WORK = os.path.join(OUT, "work")


def load_cfg():
    with open(os.path.join(ROOT, "config.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _write(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _report(lines):
    """يطبع الخلاصة في السجل، ويكتبها أيضًا في صفحة التشغيلة على GitHub.

    بدونها كان التشغيل ينجح دون أن يقول هل نُشر الفيديو ولا لماذا.
    """
    text = "\n".join(lines)
    print("\n" + text)
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        try:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(text + "\n")
        except Exception as e:
            print(f"[report] تعذّرت كتابة الخلاصة: {e}")


# ------------------------------------------------------------ المرحلة الأولى

def build_spec(script, spans, cfg, parts=None):
    """مواصفات يقرأها Manim: التصميم + محتوى كل مشهد + مدّته الدقيقة.

    هنا يُحسم المونتاج: عبارات اللقطات تُحاذى على توقيت الكلمات الحقيقي،
    ثم يفرض الدستور ألّا تتجاوز أي لقطة ثلاث ثوان.
    """
    # مدّة كل مشهد = من بدايته إلى بداية ما بعده (فيبتلع الفاصل)
    durations = []
    for i, s in enumerate(spans):
        if i < len(spans) - 1:
            durations.append(round(spans[i + 1]["start"] - s["start"], 3))
        else:
            durations.append(round(s["duration"], 3))

    word_map = {p["key"]: p.get("words", []) for p in (parts or [])}

    sections = []
    total_beats, worst = 0, 0.0
    for i, sec in enumerate(script["sections"]):
        dur = durations[i + 1]             # +1 لأن أوّل جزء هو الخطّاف
        beats = align.map_beats(sec.get("beats"), word_map.get(str(i), []), dur)
        beats = montage.enforce(beats, dur)
        bad = montage.violations(beats)
        if bad:
            print(f"[montage] القسم {i}: {bad[:3]}")
        total_beats += len(beats)
        worst = max(worst, max((b["dur"] for b in beats), default=0.0))
        sections.append({
            "heading": sec["heading"],
            "visual": sec["visual"],
            "beats": beats,
            "duration": dur,
        })

    print(f"[montage] {total_beats} لقطة، أطولها {worst:.2f}s "
          f"(الحدّ {montage.MAX_HOLD}s)")

    return {
        "design": cfg["design"],
        "intro": {"items": [script["title"], cfg["channel_name"]],
                  "caption": "", "duration": durations[0]},
        "sections": sections,
        "outro": {"items": [cfg["channel_name"], "تابِع لمزيد من الحلقات"],
                  "caption": "", "duration": durations[-1]},
    }


def stage_script(cfg):
    os.makedirs(WORK, exist_ok=True)

    print("[script] كتابة السكريبت…")
    script = content.build_script(cfg)
    words = sum(len(s["narration"].split()) for s in script["sections"])
    print(f"[script] {script['title']} — {len(script['sections'])} أقسام، "
          f"{words} كلمة تقريبًا")

    print("[script] صور العلماء (ويكيميديا، ترخيص حرّ فقط)…")
    portraits.attach(script, cfg, WORK)

    print("[script] التعليق الصوتي (جزء لكل مشهد)…")
    parts = voice.synth_script(script, cfg, WORK)

    gap = float(cfg["voice"].get("section_gap_seconds", 0.5))
    spans, total = audio.layout(parts, gap)
    print(f"[script] الطول الكلّي: {total:.1f} ثانية ({total/60:.1f} دقيقة)")

    spec = build_spec(script, spans, cfg, parts)
    _write(os.path.join(WORK, "spec.json"), spec)
    _write(os.path.join(WORK, "spans.json"), {"spans": spans, "total": total})
    _write(os.path.join(WORK, "indices.json"), visuals.order_of(spec))
    _write(os.path.join(OUT, "script.json"), script)
    _write(os.path.join(OUT, "meta.json"), content.build_meta(script, cfg))
    print(f"[script] {len(visuals.order_of(spec))} مشهدًا جاهزًا للرسم.")
    return spec


# ------------------------------------------------------------ مرحلة الرسم

def stage_render(cfg, index):
    spec = _read(os.path.join(WORK, "spec.json"))
    spec_path = os.path.join(WORK, "spec.json")
    visuals.render_one(spec, spec_path, cfg, WORK, index)


# ---------------------------------------------------------- مرحلة التركيب

def stage_assemble(cfg, publish):
    spec = _read(os.path.join(WORK, "spec.json"))
    sp = _read(os.path.join(WORK, "spans.json"))
    spans, total = sp["spans"], sp["total"]

    segments = []
    for idx in visuals.order_of(spec):
        path = os.path.join(WORK, f"{visuals.seg_name(idx)}.mp4")
        if os.path.exists(path):
            segments.append(path)
        else:
            print(f"[assemble] ناقص: {path} — سأرسمه الآن.")
            segments.append(visuals.render_one(
                spec, os.path.join(WORK, "spec.json"), cfg, WORK, idx))

    video_path = os.path.join(OUT, "video.mp4")
    render.assemble(segments, spans, total, cfg, video_path)

    meta = _read(os.path.join(OUT, "meta.json"))
    script = _read(os.path.join(OUT, "script.json"))
    source = script.get("source", "?")

    report = [
        "## نتيجة الحلقة",
        f"- **العنوان:** {script.get('title', '')}",
        f"- **الأقسام:** {len(script.get('sections', []))}",
        f"- **الطول:** {total / 60:.1f} دقيقة",
        f"- **مصدر السكريبت:** {'Gemini' if source == 'gemini' else 'احتياطي'}",
    ]

    shots = sum(1 for s in script.get("sections", []) if s.get("portrait_credit"))
    if shots:
        report.append(f"- **صور علماء حرّة:** {shots} (المصادر في الوصف)")

    blocked = None
    forced_private = False

    if not publish:
        blocked = ("سرّ `YT_REFRESH_TOKEN` غير مضبوط في GitHub Secrets"
                   if not os.environ.get("YT_REFRESH_TOKEN")
                   else "النشر مُعطّل (PUBLISH=0)")
    elif source == "fallback":
        # الحلقة الاحتياطية أقصر من هدف القناة. لا نمنع رفعها — نمنع فقط
        # أن تصير عامّة. هكذا تراها وتحكم عليها بنفسك بدل أن تختفي.
        yt = dict(cfg.get("youtube", {}))
        if str(yt.get("privacy", "private")).lower() == "public":
            yt["privacy"] = "private"
            cfg = {**cfg, "youtube": yt}
            forced_private = True

    if blocked:
        report.append(f"- **لم يُنشر:** {blocked}.")
        report.append("- الفيديو محفوظ في أثر `episode` للمراجعة.")
    else:
        try:
            import youtube
            res = youtube.upload(video_path, meta["title"], meta["description"],
                                 meta["tags"], cfg)
            report.append(f"- **رُفع:** {res['url']}")
            report.append(f"- **درجة الظهور:** `{res['privacy']}` — {res['note']}.")
            if forced_private:
                report.append("- خُفِّضت من `public` تلقائيًا لأن السكريبت احتياطي "
                              "(حلقة ضعيفة لا تُنشر للجمهور).")
            if res["privacy"] == "private":
                report.append("- لتغييرها: `youtube.privacy` في `config.json` "
                              "→ `unlisted` أو `public`.")
        except Exception as e:
            report.append(f"- **فشل الرفع:** {type(e).__name__}: {e}")
            report.append("- الفيديو محفوظ في أثر `episode`.")

    _report(report)


# ------------------------------------------------------------------ المدخل

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["script", "render", "assemble", "all"],
                    default="all")
    ap.add_argument("--index", default="0")
    ap.add_argument("--publish", action="store_true")
    args = ap.parse_args()

    publish = args.publish or os.environ.get("PUBLISH") == "1"
    cfg = load_cfg()
    os.makedirs(WORK, exist_ok=True)

    if args.stage == "script":
        stage_script(cfg)
    elif args.stage == "render":
        stage_render(cfg, args.index)
    elif args.stage == "assemble":
        stage_assemble(cfg, publish)
    else:
        spec = stage_script(cfg)
        for idx in visuals.order_of(spec):
            stage_render(cfg, idx)
        stage_assemble(cfg, publish)


if __name__ == "__main__":
    main()
