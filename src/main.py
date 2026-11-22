"""
المنظّم: سكريبت -> تعليق مقسّم -> خط زمني -> مشاهد Manim -> تركيب -> رفع.

    python src/main.py            # يصنع الفيديو فقط
    python src/main.py --publish  # يصنع وينشر على يوتيوب
"""

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


def build_spec(script, spans, cfg):
    """ملفّ يقرأه Manim: التصميم + محتوى كل مشهد + مدّته الدقيقة."""
    # مدّة كل مشهد = من بدايته إلى بداية ما بعده (فيبتلع الفاصل)
    durations = []
    for i, s in enumerate(spans):
        if i < len(spans) - 1:
            durations.append(round(spans[i + 1]["start"] - s["start"], 3))
        else:
            durations.append(round(s["duration"], 3))

    sections = []
    for i, sec in enumerate(script["sections"]):
        sections.append({
            "heading": sec["heading"],
            "visual": sec["visual"],
            "duration": durations[i + 1],      # +1 لأن أوّل جزء هو الخطّاف
        })

    return {
        "design": cfg["design"],
        "intro": {
            "items": [script["title"], cfg["channel_name"]],
            "caption": "",
            "duration": durations[0],
        },
        "sections": sections,
        "outro": {
            "items": [cfg["channel_name"], "تابِع لمزيد من الحلقات"],
            "caption": "",
            "duration": durations[-1],
        },
    }


def main():
    publish = "--publish" in sys.argv or os.environ.get("PUBLISH") == "1"

    with open(os.path.join(ROOT, "config.json"), encoding="utf-8") as fh:
        cfg = json.load(fh)

    out_dir = os.path.join(ROOT, "output")
    work_dir = os.path.join(out_dir, "work")
    os.makedirs(work_dir, exist_ok=True)
    video_path = os.path.join(out_dir, "video.mp4")

    print("[1/5] كتابة السكريبت…")
    script = content.build_script(cfg)
    print(f"      {script['title']} — {len(script['sections'])} أقسام")

    print("[2/5] التعليق الصوتي (جزء لكل مشهد)…")
    parts = voice.synth_script(script, cfg, work_dir)

    gap = float(cfg["voice"].get("section_gap_seconds", 0.5))
    spans, total = audio.layout(parts, gap)
    print(f"      الطول الكلّي: {total:.1f} ثانية ({total/60:.1f} دقيقة)")

    print("[3/5] تجهيز مواصفات المشاهد…")
    spec = build_spec(script, spans, cfg)
    spec_path = os.path.join(work_dir, "spec.json")
    with open(spec_path, "w", encoding="utf-8") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=1)

    print("[4/5] رسم المشاهد…")
    segments = visuals.render_all(spec, spec_path, cfg, work_dir)

    print("[5/5] التركيب النهائي…")
    render.assemble(segments, spans, total, cfg, video_path)

    meta = content.build_meta(script, cfg)
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(out_dir, "script.json"), "w", encoding="utf-8") as fh:
        json.dump(script, fh, ensure_ascii=False, indent=1)

    if publish:
        print("[+] الرفع إلى يوتيوب…")
        import youtube
        youtube.upload(video_path, meta["title"], meta["description"], meta["tags"])
    else:
        print("[i] لم يُنشر. أضف --publish بعد ضبط أسرار YT_*.")


if __name__ == "__main__":
    main()
