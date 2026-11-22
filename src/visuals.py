"""
تشغيل Manim لكل قسم، مع بديل مرسوم بـPillow إن تعذّر Manim.

المخرجات: قائمة مسارات mp4 بترتيب الأقسام (مع intro و outro).
"""

import glob
import json
import os
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import design


def manim_available():
    try:
        import manim  # noqa: F401
        return True
    except Exception:
        return False


def _find_output(media_dir, name):
    pats = [
        os.path.join(media_dir, "videos", "**", f"{name}.mp4"),
        os.path.join(media_dir, "**", f"{name}.mp4"),
    ]
    for p in pats:
        hits = glob.glob(p, recursive=True)
        if hits:
            return sorted(hits, key=os.path.getmtime)[-1]
    return None


def _render_manim(index, spec_path, media_dir, cfg, name):
    here = os.path.dirname(os.path.abspath(__file__))
    scenes = os.path.join(here, "scenes.py")
    v = cfg["video"]

    env = dict(os.environ)
    env["FALAKY_SPEC"] = os.path.abspath(spec_path)
    env["FALAKY_INDEX"] = str(index)

    cmd = [
        sys.executable, "-m", "manim", "render",
        "-r", f"{v['width']},{v['height']}",
        "--fps", str(v["fps"]),
        "--format", "mp4",
        "--media_dir", media_dir,
        "--disable_caching",
        "-o", name,
        scenes, "SectionScene",
    ]
    try:
        res = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=900)
        if res.returncode != 0:
            print(f"[visuals] Manim فشل للقسم {index}:\n{res.stderr[-1200:]}")
            return None
    except Exception as e:
        print(f"[visuals] تعذّر تشغيل Manim للقسم {index}: {e}")
        return None
    return _find_output(media_dir, name)


# ------------------------------------------------------------- بديل Pillow

def _fallback_card(index, spec, cfg, out_dir, name, duration):
    """بطاقة ساكنة مصمّمة (ليست نصّا على تدرّج) + حركة زوم بطيئة."""
    from moviepy.editor import ImageClip, CompositeVideoClip

    v, d = cfg["video"], cfg["design"]
    w, h = v["width"], v["height"]

    if str(index) in ("intro", "outro"):
        block = spec[str(index)]
        heading, items, caption = "", block["items"], block.get("caption", "")
    else:
        sec = spec["sections"][int(index)]
        heading = sec.get("heading", "")
        items = sec["visual"]["items"]
        caption = sec["visual"].get("caption", "")

    img = design.card(w, h, heading, items, caption, d)
    path = os.path.join(out_dir, f"{name}.png")
    img.save(path)

    clip = (ImageClip(path)
            .set_duration(duration)
            .resize(lambda t: 1.0 + 0.035 * (t / max(duration, 0.1))))
    clip = clip.set_position(("center", "center"))
    mp4 = os.path.join(out_dir, f"{name}.mp4")
    CompositeVideoClip([clip], size=(w, h)).set_duration(duration).write_videofile(
        mp4, fps=v["fps"], codec="libx264", audio=False, preset="medium",
        threads=4, logger=None)
    return mp4


# ------------------------------------------------------------------ الواجهة

def render_all(spec, spec_path, cfg, work_dir):
    os.makedirs(work_dir, exist_ok=True)
    media_dir = os.path.join(work_dir, "manim")
    use_manim = manim_available()
    if not use_manim:
        print("[visuals] Manim غير متاح — سأستعمل البطاقات المصمّمة بديلاً.")

    order = ["intro"] + [str(i) for i in range(len(spec["sections"]))] + ["outro"]
    paths = []
    for idx in order:
        name = f"seg_{idx}"
        out = None
        if use_manim:
            out = _render_manim(idx, spec_path, media_dir, cfg, name)
        if out is None:
            if idx in ("intro", "outro"):
                dur = spec[idx]["duration"]
            else:
                dur = spec["sections"][int(idx)]["duration"]
            out = _fallback_card(idx, spec, cfg, work_dir, name, dur)
        paths.append(out)
        print(f"[visuals] جاهز: {name}")
    return paths
