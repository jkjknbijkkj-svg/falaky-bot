"""
تشغيل Manim لمشهد واحد أو لكل المشاهد، مع بديل مرسوم بـPillow إن تعذّر Manim.

`render_one` هي الوحدة الأساسية: تُستدعى مرّة لكل قسم. هذا ما يسمح لنا
برسم أقسام الحلقة **بالتوازي** على GitHub Actions بدل انتظارها واحدًا تلو الآخر —
وهو الفرق بين حلقة ٢٠ دقيقة تُرسم في ساعات وأخرى تُرسم في دقائق.
"""

import glob
import os
import subprocess
import sys

import compat  # noqa: F401  — يجب أن يسبق أي استيراد لـmoviepy
import design


def manim_available():
    try:
        import manim  # noqa: F401
        return True
    except Exception:
        return False


def seg_name(idx):
    return f"seg_{idx}"


def order_of(spec):
    return ["intro"] + [str(i) for i in range(len(spec["sections"]))] + ["outro"]


def duration_of(spec, idx):
    if str(idx) in ("intro", "outro"):
        return spec[str(idx)]["duration"]
    return spec["sections"][int(idx)]["duration"]


def _find_output(media_dir, name):
    for pat in (os.path.join(media_dir, "videos", "**", f"{name}.mp4"),
                os.path.join(media_dir, "**", f"{name}.mp4")):
        hits = glob.glob(pat, recursive=True)
        if hits:
            return sorted(hits, key=os.path.getmtime)[-1]
    return None


def _render_manim(index, spec_path, media_dir, cfg, name):
    here = os.path.dirname(os.path.abspath(__file__))
    scenes = os.path.join(here, "scenes.py")
    v = cfg["video"]
    timeout = int(cfg.get("render", {}).get("manim_timeout_seconds", 2400))

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
        res = subprocess.run(cmd, env=env, capture_output=True,
                             text=True, timeout=timeout)
        if res.returncode != 0:
            print(f"[visuals] Manim فشل للقسم {index}:\n{res.stderr[-1500:]}")
            return None
    except Exception as e:
        print(f"[visuals] تعذّر تشغيل Manim للقسم {index}: {e}")
        return None
    return _find_output(media_dir, name)


# ------------------------------------------------------------- بديل Pillow

def _fallback_card(index, spec, cfg, out_dir, name, duration):
    """بطاقة ساكنة مصمّمة (ليست نصًّا على تدرّج) + حركة زوم بطيئة."""
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
    png = os.path.join(out_dir, f"{name}.png")
    img.save(png)

    clip = (ImageClip(png)
            .set_duration(duration)
            .resize(lambda t: 1.0 + 0.035 * (t / max(duration, 0.1)))
            .set_position(("center", "center")))
    mp4 = os.path.join(out_dir, f"{name}.mp4")
    CompositeVideoClip([clip], size=(w, h)).set_duration(duration).write_videofile(
        mp4, fps=v["fps"], codec="libx264", audio=False, preset="medium",
        threads=4, logger=None)
    return mp4


# ------------------------------------------------------------------ الواجهة

def render_one(spec, spec_path, cfg, work_dir, idx):
    """يرسم مشهدًا واحدًا ويعيد مسار ملفّه."""
    os.makedirs(work_dir, exist_ok=True)
    media_dir = os.path.join(work_dir, "manim")
    name = seg_name(idx)

    out = _render_manim(idx, spec_path, media_dir, cfg, name) \
        if manim_available() else None
    if out is None:
        if not manim_available():
            print("[visuals] Manim غير متاح — بطاقة مصمّمة بديلًا.")
        out = _fallback_card(idx, spec, cfg, work_dir, name,
                             duration_of(spec, idx))

    # ننسخ الناتج إلى مكان ثابت حتى تجده مرحلة التركيب
    final = os.path.join(work_dir, f"{name}.mp4")
    if os.path.abspath(out) != os.path.abspath(final):
        import shutil
        shutil.copyfile(out, final)
    print(f"[visuals] جاهز: {name}")
    return final


def render_all(spec, spec_path, cfg, work_dir):
    return [render_one(spec, spec_path, cfg, work_dir, idx)
            for idx in order_of(spec)]
