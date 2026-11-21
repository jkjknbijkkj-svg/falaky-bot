"""
المنظّم: حقيقة -> صوت -> فيديو -> (اختياريًا) رفع.
التشغيل:
  python src/main.py            # يصنع الفيديو فقط (محرّك أولًا — تراه قبل أي نشر)
  python src/main.py --publish  # يصنع وينشر على يوتيوب (بعد ضبط أسرار YT_*)
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import content
import voice
import render


def main():
    publish = "--publish" in sys.argv or os.environ.get("PUBLISH") == "1"

    with open(os.path.join(ROOT, "config.json"), encoding="utf-8") as fh:
        cfg = json.load(fh)

    out_dir = os.path.join(ROOT, "output")
    os.makedirs(out_dir, exist_ok=True)
    voice_path = os.path.join(out_dir, "voice.mp3")
    video_path = os.path.join(out_dir, "video.mp4")

    print("[1/3] توليد الحقيقة…")
    fact = content.get_fact(cfg)
    print("      العنوان:", fact["title"])

    print("[2/3] توليد الصوت…")
    dur = voice.synth(fact["narration"], voice_path, cfg)
    print("      المدة:", round(dur, 1) if dur else "صامت")

    print("[3/3] بناء الفيديو…")
    render.build_video(fact, voice_path, dur, cfg, video_path)
    print("      تم:", video_path)

    # نحفظ بيانات الحلقة لاستعمالها في النشر
    meta = {
        "title": f"{fact['title']} | {cfg['channel_name']}",
        "description": fact["narration"] + "\n\n#فيزياء #علوم #فضاء",
        "tags": ["فيزياء", "علوم", "فضاء", "حقائق علمية", "تعليم"],
    }
    with open(os.path.join(out_dir, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False)

    if publish:
        print("[+] الرفع إلى يوتيوب…")
        import youtube

        youtube.upload(video_path, meta["title"], meta["description"], meta["tags"])
    else:
        print("[i] لم يُنشر (محرّك فقط). أضف --publish بعد أن تضبط أسرار YT_*.")


if __name__ == "__main__":
    main()
