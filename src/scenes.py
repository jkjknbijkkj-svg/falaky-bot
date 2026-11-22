"""
مكتبة مشاهد Manim — قلب الترقية البصرية.

بدل نصّ مرميّ على خلفية متدرّجة، كل قسم من الحلقة يصير مشهدًا مرسومًا يشرح
الفكرة: سلسلة مراحل، مقارنة، موجة، ذرّة، رقم، خط زمني، بطاقة عال攎م، أو اقتباس.

يُستدعى من visuals.py عبر سطر أوامر manim، ويقرأ:
  FALAKY_SPEC   مسار ملف JSON فيه مواصفات المشاهد + مدّة كل قسم
  FALAKY_INDEX  رقم القسم المطلوب رسمه (أو "intro" / "outro")

كل مشهد يلتزم بمدّة القسم بالضبط حتى يتزامن مع التعليق الصوتي.
"""

import json
import os

from manim import (
    Scene, Text, VGroup, VMobject, Rectangle, RoundedRectangle, Circle, Dot,
    Arrow, Line, FadeIn, Create, GrowFromCenter, ValueTracker, always_redraw,
    config, ORIGIN, UP, DOWN, LEFT, RIGHT, PI,
)
from manim.utils import rate_functions
import numpy as np

# ------------------------------------------------------------------ الإعداد

SPEC_PATH = os.environ.get("FALAKY_SPEC", "output/spec.json")
INDEX = os.environ.get("FALAKY_INDEX", "0")

with open(SPEC_PATH, encoding="utf-8") as fh:
    SPEC = json.load(fh)

D = SPEC["design"]
FONT = D.get("font_family") or "Amiri"
BG = D["bg"]
SURFACE = D["surface"]
ACCENT = D["accent"]
ACCENT_W = D["accent_warm"]
TEXT = D["text"]
MUTED = D["muted"]

config.background_color = BG


def _txt(s, size=32, color=None, weight="NORMAL"):
    return Text(str(s), font=FONT, font_size=size,
                color=color or TEXT, weight=weight)


def _split(raw, fallback="…"):
    parts = [p.strip() for p in str(raw).split("|") if p.strip()]
    return parts or [fallback]


class _Base(Scene):
    """أساس مشترك: خلفية موحّدة، عنوان ثابت، شريط سفلي، وضبط المدّة."""

    def setup_stage(self, heading="", caption=""):
        # توهّج خفيف يكسر جمود الخلفية المسطّحة
        glow = VGroup(*[
            Circle(radius=r, stroke_width=0, fill_color=ACCENT, fill_opacity=op)
            for r, op in ((5.2, 0.030), (3.6, 0.030), (2.2, 0.035))
        ]).move_to(ORIGIN + UP * 0.2)
        self.add(glow)

        # عنوان القسم أعلى اليمين + خط تحته (المحتوى عربي فالمحاذاة يمين)
        if heading:
            h = _txt(heading, 38, ACCENT)
            h.to_edge(UP, buff=0.55).to_edge(RIGHT, buff=0.9)
            rule = Line(ORIGIN, LEFT * 2.4, stroke_width=3, color=ACCENT_W)
            rule.next_to(h, DOWN, buff=0.18).align_to(h, RIGHT)
            self.add(h, rule)

        # شريط سفلي للسطر التوضيحي
        if caption:
            bar = Rectangle(width=config.frame_width, height=0.95,
                            stroke_width=0, fill_color=SURFACE, fill_opacity=0.92)
            bar.to_edge(DOWN, buff=0)
            c = _txt(caption, 28, MUTED).move_to(bar.get_center())
            self.add(bar, c)

        self.t_used = 0.0

    def play_t(self, *anims, run_time=1.0, **kw):
        self.play(*anims, run_time=run_time, **kw)
        self.t_used += run_time

    def wait_t(self, d):
        if d > 0.02:
            self.wait(d)
            self.t_used += d

    def finish(self, total):
        """يملأ ما تبقّى من المدّة حتى يطابق المشهد طول التعليق."""
        self.wait_t(max(total - self.t_used, 0.1))


# ------------------------------------------------------------------ المشاهد

class _Flow(_Base):
    """سلسلة مراحل متتابعة — تُقرأ من اليمين إلى اليسار."""

    def build(self, items, total):
        n = len(items)
        box_w = min(2.9, (config.frame_width - 1.6) / max(n, 1) - 0.35)
        boxes = VGroup()
        for it in items:
            box = RoundedRectangle(corner_radius=0.16, width=box_w, height=1.5,
                                   stroke_color=ACCENT, stroke_width=2.5,
                                   fill_color=SURFACE, fill_opacity=0.95)
            label = _txt(it, 24).scale_to_fit_width(min(box_w - 0.3, box_w * 0.86))
            label.move_to(box.get_center())
            boxes.add(VGroup(box, label))

        boxes.arrange(LEFT, buff=0.62)          # العنصر الأول إلى اليمين
        boxes.move_to(ORIGIN + UP * 0.15)
        if boxes.width > config.frame_width - 1.0:
            boxes.scale_to_fit_width(config.frame_width - 1.0)

        arrows = VGroup()
        for i in range(n - 1):
            arrows.add(Arrow(boxes[i].get_left(), boxes[i + 1].get_right(),
                             buff=0.12, stroke_width=4, color=ACCENT_W,
                             max_tip_length_to_length_ratio=0.28))

        step = max((total - 0.8) / max(n, 1), 0.35)
        for i in range(n):
            self.play_t(FadeIn(boxes[i], shift=LEFT * 0.35),
                        run_time=min(0.55, step * 0.5))
            if i < n - 1:
                self.play_t(Create(arrows[i]), run_time=min(0.35, step * 0.3))
            self.wait_t(max(step - 0.9, 0.05))
        self.finish(total)


class _Bullets(_Base):
    """نقاط تُكشف تباعًا، بمحاذاة يمين."""

    def build(self, items, total):
        rows = VGroup()
        for it in items:
            dot = Circle(radius=0.11, stroke_width=0,
                         fill_color=ACCENT_W, fill_opacity=1)
            row = VGroup(_txt(it, 32), dot).arrange(RIGHT, buff=0.35)
            rows.add(row)
        rows.arrange(DOWN, buff=0.62, aligned_edge=RIGHT)
        rows.move_to(ORIGIN + UP * 0.1).to_edge(RIGHT, buff=1.4)
        if rows.height > 4.6:
            rows.scale_to_fit_height(4.6)

        step = max((total - 0.6) / max(len(items), 1), 0.4)
        for row in rows:
            self.play_t(FadeIn(row, shift=LEFT * 0.4), run_time=min(0.5, step * 0.5))
            self.wait_t(max(step - 0.5, 0.05))
        self.finish(total)


class _Compare(_Base):
    """لوحتان متقابلتان: الخيار وميزته وثمنه."""

    def build(self, items, total):
        items = (list(items) + list(items))[:2]
        panels = VGroup()
        for idx, raw in enumerate(items):
            parts = _split(raw)
            col = ACCENT if idx == 0 else ACCENT_W
            panel = RoundedRectangle(corner_radius=0.2, width=5.4, height=4.0,
                                     stroke_color=col, stroke_width=2.5,
                                     fill_color=SURFACE, fill_opacity=0.9)
            head = _txt(parts[0], 34, col)
            lines = VGroup(*[_txt(p, 26, MUTED) for p in parts[1:]])
            body = VGroup(head, *lines).arrange(DOWN, buff=0.42)
            if body.width > 4.8:
                body.scale_to_fit_width(4.8)
            body.move_to(panel.get_center())
            panels.add(VGroup(panel, body))

        panels.arrange(LEFT, buff=0.8).move_to(ORIGIN + UP * 0.15)

        half = max((total - 0.6) / 2, 0.4)
        self.play_t(FadeIn(panels[0], shift=LEFT * 0.3), run_time=0.6)
        self.wait_t(max(half - 0.6, 0.05))
        self.play_t(FadeIn(panels[1], shift=RIGHT * 0.3), run_time=0.6)
        self.finish(total)


class _Wave(_Base):
    """موجة متحرّكة لشرح التردّد أو الإشارة."""

    def build(self, items, total):
        amp, span = 1.25, 5.6
        tracker = ValueTracker(0.0)

        axis = Line(LEFT * span, RIGHT * span, stroke_width=2, color=MUTED)
        axis.move_to(ORIGIN + UP * 0.25)

        def make_wave():
            phase = tracker.get_value()
            pts = [np.array([x, amp * np.sin(1.5 * x + phase), 0.0]) + UP * 0.25
                   for x in np.linspace(-span, span, 160)]
            m = VMobject(stroke_color=ACCENT, stroke_width=5)
            m.set_points_as_corners(pts)
            return m

        wave = always_redraw(make_wave)
        self.add(axis, wave)

        labels = VGroup(*[_txt(i, 26, MUTED) for i in items[:3]])
        labels.arrange(LEFT, buff=1.0).next_to(axis, DOWN, buff=1.35)

        self.play_t(FadeIn(labels), run_time=0.6)
        remaining = max(total - self.t_used - 0.1, 0.4)
        self.play_t(tracker.animate.set_value(remaining * 3.4),
                    run_time=remaining, rate_func=rate_functions.linear)
        self.finish(total)


class _Orbit(_Base):
    """نواة وإلكترونات تدور — للمقاومة والتيار والذرّة."""

    def build(self, items, total):
        center = ORIGIN + UP * 0.25
        nucleus = Circle(radius=0.45, stroke_width=0,
                         fill_color=ACCENT_W, fill_opacity=1).move_to(center)
        rings = VGroup(*[
            Circle(radius=r, stroke_color=MUTED, stroke_width=1.6,
                   stroke_opacity=0.55).move_to(center)
            for r in (1.5, 2.3)
        ])
        tracker = ValueTracker(0.0)

        def electron(radius, speed, offset):
            return always_redraw(lambda: Dot(
                point=center + np.array([
                    radius * np.cos(tracker.get_value() * speed + offset),
                    radius * np.sin(tracker.get_value() * speed + offset) * 0.62,
                    0.0]),
                radius=0.13, color=ACCENT))

        electrons = VGroup(
            electron(1.5, 1.0, 0.0),
            electron(1.5, 1.0, PI),
            electron(2.3, -0.72, PI / 2),
        )

        labels = VGroup(*[_txt(i, 26, MUTED) for i in items[:3]])
        labels.arrange(LEFT, buff=0.9).to_edge(DOWN, buff=1.5)

        self.play_t(GrowFromCenter(nucleus), Create(rings), run_time=0.7)
        self.add(electrons)
        self.play_t(FadeIn(labels), run_time=0.5)
        remaining = max(total - self.t_used - 0.1, 0.4)
        self.play_t(tracker.animate.set_value(remaining * 2.0),
                    run_time=remaining, rate_func=rate_functions.linear)
        self.finish(total)


class _Stat(_Base):
    """رقم واحد كبير + سطرا شرح."""

    def build(self, items, total):
        items = (list(items) + ["", ""])[:3]
        big = _txt(items[0], 130, ACCENT_W)
        l1 = _txt(items[1], 36)
        l2 = _txt(items[2], 28, MUTED)
        VGroup(big, l1, l2).arrange(DOWN, buff=0.45).move_to(ORIGIN + UP * 0.2)

        self.play_t(GrowFromCenter(big), run_time=0.8)
        self.play_t(FadeIn(l1, shift=UP * 0.2), run_time=0.5)
        self.play_t(FadeIn(l2, shift=UP * 0.2), run_time=0.45)
        self.finish(total)


class _Timeline(_Base):
    """خط زمني للاكتشاف والاختراع — الأقدم يمينًا (اتجاه القراءة العربي)."""

    def build(self, items, total):
        n = max(len(items), 1)
        span = min(5.8, 1.6 * n)
        axis = Line(RIGHT * span, LEFT * span, stroke_width=3, color=MUTED)
        axis.move_to(ORIGIN + UP * 0.35)
        self.play_t(Create(axis), run_time=0.6)

        xs = np.linspace(span, -span, n) if n > 1 else np.array([0.0])
        step = max((total - 0.6) / n, 0.45)

        for i, raw in enumerate(items):
            parts = _split(raw)
            year = parts[0]
            event = parts[1] if len(parts) > 1 else ""

            pos = axis.get_center() + RIGHT * float(xs[i])
            node = Circle(radius=0.16, stroke_width=3, stroke_color=ACCENT_W,
                          fill_color=BG, fill_opacity=1).move_to(pos)
            y_lbl = _txt(year, 30, ACCENT_W).next_to(node, UP, buff=0.3)
            e_lbl = _txt(event, 23, TEXT)
            if e_lbl.width > 3.0:
                e_lbl.scale_to_fit_width(3.0)
            e_lbl.next_to(node, DOWN, buff=0.35)
            # نزيح بالتناوب حتى لا تتلامس النصوص
            if i % 2:
                e_lbl.shift(DOWN * 0.75)
                self.add(Line(node.get_bottom(), e_lbl.get_top(),
                              stroke_width=1.5, color=MUTED))

            self.play_t(GrowFromCenter(node), FadeIn(y_lbl, shift=DOWN * 0.15),
                        run_time=min(0.5, step * 0.45))
            self.play_t(FadeIn(e_lbl), run_time=min(0.35, step * 0.3))
            self.wait_t(max(step - 0.85, 0.05))
        self.finish(total)


class _Profile(_Base):
    """بطاقة عال攎م: الاسم، سنوات حياته، وإسهامه. بلا صور — هوية خطّية فقط."""

    def build(self, items, total):
        items = (list(items) + ["", "", ""])[:3]
        name, years, deed = items[0], items[1], items[2]

        panel = RoundedRectangle(corner_radius=0.25, width=9.4, height=4.2,
                                 stroke_color=ACCENT, stroke_width=2.5,
                                 fill_color=SURFACE, fill_opacity=0.92)
        panel.move_to(ORIGIN + UP * 0.1)

        monogram = Circle(radius=0.72, stroke_color=ACCENT_W, stroke_width=3,
                          fill_color=BG, fill_opacity=1)
        badge = VGroup(monogram,
                       _txt(str(name)[:1], 52, ACCENT_W).move_to(monogram.get_center()))

        n_lbl = _txt(name, 46, TEXT)
        y_lbl = _txt(years, 30, ACCENT_W)
        d_lbl = _txt(deed, 26, MUTED)
        for m in (n_lbl, d_lbl):
            if m.width > 6.6:
                m.scale_to_fit_width(6.6)
        info = VGroup(n_lbl, y_lbl, d_lbl).arrange(DOWN, buff=0.34,
                                                   aligned_edge=RIGHT)

        VGroup(info, badge).arrange(LEFT, buff=0.75).move_to(panel.get_center())

        self.play_t(FadeIn(panel, shift=UP * 0.2), run_time=0.6)
        self.play_t(GrowFromCenter(badge), run_time=0.5)
        self.play_t(FadeIn(n_lbl, shift=LEFT * 0.3), run_time=0.5)
        self.play_t(FadeIn(y_lbl), run_time=0.4)
        self.play_t(FadeIn(d_lbl), run_time=0.45)
        self.finish(total)


class _Quote(_Base):
    """اقتباس قصير مع قائله."""

    def build(self, items, total):
        items = (list(items) + ["", ""])[:2]
        mark = _txt("”", 110, ACCENT)
        body = _txt(items[0], 38, TEXT)
        if body.width > config.frame_width - 3.0:
            body.scale_to_fit_width(config.frame_width - 3.0)
        rule = Line(LEFT * 1.4, RIGHT * 1.4, stroke_width=3, color=ACCENT_W)
        who = _txt(items[1], 28, MUTED)

        VGroup(mark, body, rule, who).arrange(DOWN, buff=0.42)\
            .move_to(ORIGIN + UP * 0.1)

        self.play_t(FadeIn(mark), run_time=0.5)
        self.play_t(FadeIn(body, shift=UP * 0.25), run_time=0.8)
        self.play_t(Create(rule), run_time=0.4)
        self.play_t(FadeIn(who), run_time=0.45)
        self.finish(total)


class _Title(_Base):
    """بطاقة العنوان — هوية ثابتة لكل حلقة."""

    def build(self, items, total):
        title = _txt(items[0] if items else "", 66, TEXT)
        if title.width > config.frame_width - 2.0:
            title.scale_to_fit_width(config.frame_width - 2.0)
        rule = Line(LEFT * 2.2, RIGHT * 2.2, stroke_width=4, color=ACCENT_W)
        sub = _txt(items[1] if len(items) > 1 else "", 30, MUTED)
        VGroup(title, rule, sub).arrange(DOWN, buff=0.5).move_to(ORIGIN)

        self.play_t(FadeIn(title, shift=UP * 0.3), run_time=0.9)
        self.play_t(Create(rule), run_time=0.5)
        self.play_t(FadeIn(sub), run_time=0.5)
        self.finish(total)


_BUILDERS = {
    "flow": _Flow, "bullets": _Bullets, "compare": _Compare,
    "wave": _Wave, "orbit": _Orbit, "stat": _Stat,
    "timeline": _Timeline, "profile": _Profile, "figure": _Profile,
    "quote": _Quote, "title": _Title,
}


# ------------------------------------------------------- المشهد الذي يُستدعى

def _resolve():
    if INDEX in ("intro", "outro"):
        block = SPEC[INDEX]
        return "title", block["items"], "", block.get("caption", ""), block["duration"]
    sec = SPEC["sections"][int(INDEX)]
    v = sec["visual"]
    return (v["type"], v["items"], sec.get("heading", ""),
            v.get("caption", ""), sec["duration"])


class SectionScene(_Base):
    def construct(self):
        vtype, items, heading, caption, duration = _resolve()
        cls = _BUILDERS.get(vtype, _Bullets)
        # نستعير منطق البناء من الصنف المناسب دون إنشاء مشهد جديد
        self.setup_stage(heading, caption)
        cls.build(self, items, float(duration))
