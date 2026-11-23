"""
مكتبة مشاهد Manim — قلب الترقية البصرية.

بدل نصّ مرميّ على خلفية متدرّجة، كل قسم من الحلقة يصير مشهدًا مرسومًا يشرح
الفكرة: سلسلة مراحل، مقارنة، موجة، ذرّة، رقم، خط زمني، بطاقة عالِم، أو اقتباس.

يُستدعى من visuals.py عبر سطر أوامر manim، ويقرأ:
  FALAKY_SPEC   مسار ملف JSON فيه مواصفات المشاهد + مدّة كل قسم
  FALAKY_INDEX  رقم القسم المطلوب رسمه (أو "intro" / "outro")

كل مشهد يلتزم بمدّة القسم بالضبط حتى يتزامن مع التعليق الصوتي.
"""

import json
import os

from manim import (
    Scene, Text, VGroup, VMobject, Group, ImageMobject, Rectangle,
    RoundedRectangle, Circle, Dot, Arrow, Line, FadeIn, Create,
    GrowFromCenter, ValueTracker, always_redraw,
    config, ORIGIN, UP, DOWN, LEFT, RIGHT, PI,
)
from manim.utils import rate_functions
import numpy as np

import draw as DRAW
import montage as MT

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
    """Manim لا يرسم نصًّا فارغًا، فنعيد مجموعة فارغة بدل أن ينهار المشهد."""
    s = str(s).strip()
    if not s:
        return VGroup()
    return Text(s, font=FONT, font_size=size,
                color=color or TEXT, weight=weight)


def _fit_w(m, w):
    """تصغير آمن: لا نلمس مجموعة فارغة (عرضها صفر) فنتجنّب القسمة على صفر."""
    if w > 0 and getattr(m, "width", 0) > 0:
        m.scale_to_fit_width(w)
    return m


def _split(raw, fallback="…"):
    parts = [p.strip() for p in str(raw).split("|") if p.strip()]
    return parts or [fallback]


def _alive(m):
    return getattr(m, "width", 0) > 0 or getattr(m, "height", 0) > 0


def _stack(mobs, direction=DOWN, buff=0.4, aligned_edge=None):
    """يرصّ العناصر غير الفارغة فقط — عنصر فارغ يكسر arrange في Manim.

    VGroup لا يقبل إلا VMobject، والصور ليست كذلك، فنختار الحاوية المناسبة.
    """
    live = [m for m in mobs if _alive(m)]
    container = VGroup if all(isinstance(m, VMobject) for m in live) else Group
    g = container(*live)
    if live:
        if aligned_edge is None:
            g.arrange(direction, buff=buff)
        else:
            g.arrange(direction, buff=buff, aligned_edge=aligned_edge)
    return g


def _texts(items, size, color=None):
    """مجموعة نصوص بعد إسقاط الفارغ منها."""
    return VGroup(*[_txt(i, size, color) for i in items if str(i).strip()])


# تفاصيل إضافية للمشهد الحالي (مثل مسار صورة العالِم) — يملؤها _resolve
VISUAL = {}


def _portrait_path():
    """مسار صورة العالِم إن وُجدت، منسوبًا إلى مجلّد المواصفات."""
    rel = VISUAL.get("portrait")
    if not rel:
        return None
    full = os.path.join(os.path.dirname(os.path.abspath(SPEC_PATH)), rel)
    return full if os.path.exists(full) else None


PALETTE = {"bg": BG, "surface": SURFACE, "accent": ACCENT,
           "warm": ACCENT_W, "text": TEXT, "muted": MUTED}


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
            label = _fit_w(_txt(it, 24), min(box_w - 0.3, box_w * 0.86))
            if _alive(label):
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
            if not str(it).strip():
                continue
            dot = Circle(radius=0.11, stroke_width=0,
                         fill_color=ACCENT_W, fill_opacity=1)
            rows.add(_stack([_txt(it, 32), dot], RIGHT, 0.35))
        if not rows.submobjects:
            self.finish(total)
            return
        rows.arrange(DOWN, buff=0.62, aligned_edge=RIGHT)
        rows.move_to(ORIGIN + UP * 0.1).to_edge(RIGHT, buff=1.4)
        if rows.height > 4.6:
            rows.scale_to_fit_height(4.6)

        step = max((total - 0.6) / max(len(rows.submobjects), 1), 0.4)
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
            lines = _texts(parts[1:], 26, MUTED)
            body = _stack([head, *lines], DOWN, 0.42)
            _fit_w(body, 4.8)
            if _alive(body):
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

        labels = _stack(_texts(items[:3], 26, MUTED), LEFT, 1.0)
        if _alive(labels):
            labels.next_to(axis, DOWN, buff=1.35)
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

        labels = _stack(_texts(items[:3], 26, MUTED), LEFT, 0.9)

        self.play_t(GrowFromCenter(nucleus), Create(rings), run_time=0.7)
        self.add(electrons)
        if _alive(labels):
            labels.to_edge(DOWN, buff=1.5)
            self.play_t(FadeIn(labels), run_time=0.5)
        remaining = max(total - self.t_used - 0.1, 0.4)
        self.play_t(tracker.animate.set_value(remaining * 2.0),
                    run_time=remaining, rate_func=rate_functions.linear)
        self.finish(total)


class _Stat(_Base):
    """رقم واحد كبير + سطرا شرح."""

    def build(self, items, total):
        vals = [str(i).strip() for i in items if str(i).strip()][:3]
        vals += [""] * (3 - len(vals))
        big = _txt(vals[0] or "—", 130, ACCENT_W)
        l1 = _txt(vals[1], 36)
        l2 = _txt(vals[2], 28, MUTED)
        _stack([big, l1, l2], DOWN, 0.45).move_to(ORIGIN + UP * 0.2)

        self.play_t(GrowFromCenter(big), run_time=0.8)
        for m, rt in ((l1, 0.5), (l2, 0.45)):
            if _alive(m):
                self.play_t(FadeIn(m, shift=UP * 0.2), run_time=rt)
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
            if _alive(e_lbl):
                _fit_w(e_lbl, 3.0)
                e_lbl.next_to(node, DOWN, buff=0.35)
                # نزيح بالتناوب حتى لا تتلامس النصوص
                if i % 2:
                    e_lbl.shift(DOWN * 0.75)
                    self.add(Line(node.get_bottom(), e_lbl.get_top(),
                                  stroke_width=1.5, color=MUTED))

            self.play_t(GrowFromCenter(node), FadeIn(y_lbl, shift=DOWN * 0.15),
                        run_time=min(0.5, step * 0.45))
            if _alive(e_lbl):
                self.play_t(FadeIn(e_lbl), run_time=min(0.35, step * 0.3))
            self.wait_t(max(step - 0.85, 0.05))
        self.finish(total)


class _Profile(_Base):
    """بطاقة عالِم: الاسم، سنوات حياته، وإسهامه. بلا صور — هوية خطّية فقط."""

    def build(self, items, total):
        vals = [str(i).strip() for i in items if str(i).strip()][:3]
        vals += [""] * (3 - len(vals))
        name, years, deed = vals[0], vals[1], vals[2]

        panel = RoundedRectangle(corner_radius=0.25, width=9.4, height=4.2,
                                 stroke_color=ACCENT, stroke_width=2.5,
                                 fill_color=SURFACE, fill_opacity=0.92)
        panel.move_to(ORIGIN + UP * 0.1)

        R = 0.78
        monogram = Circle(radius=R, stroke_color=ACCENT_W, stroke_width=3,
                          fill_color=BG, fill_opacity=1)

        photo_path = _portrait_path()
        if photo_path:
            # الصورة مقصوصة دائريًّا مسبقًا بقناع شفّاف، فتملأ الإطار تمامًا
            photo = ImageMobject(photo_path)
            photo.height = 2 * R * 0.97
            photo.move_to(monogram.get_center())
            badge = Group(monogram, photo)
        else:
            badge = VGroup(monogram, _txt(name[:1] or "؟", 54, ACCENT_W)
                           .move_to(monogram.get_center()))

        n_lbl = _fit_w(_txt(name, 46, TEXT), 6.6)
        y_lbl = _txt(years, 30, ACCENT_W)
        d_lbl = _fit_w(_txt(deed, 26, MUTED), 6.6)
        info = _stack([n_lbl, y_lbl, d_lbl], DOWN, 0.34, aligned_edge=RIGHT)

        _stack([info, badge], LEFT, 0.75).move_to(panel.get_center())

        self.play_t(FadeIn(panel, shift=UP * 0.2), run_time=0.6)
        self.play_t(FadeIn(badge, scale=0.9), run_time=0.5)
        for m, rt, sh in ((n_lbl, 0.5, LEFT * 0.3), (y_lbl, 0.4, None),
                          (d_lbl, 0.45, None)):
            if not _alive(m):
                continue
            self.play_t(FadeIn(m, shift=sh) if sh is not None else FadeIn(m),
                        run_time=rt)
        self.finish(total)


class _Quote(_Base):
    """اقتباس قصير مع قائله."""

    def build(self, items, total):
        vals = [str(i).strip() for i in items if str(i).strip()][:2]
        vals += [""] * (2 - len(vals))
        mark = _txt("”", 110, ACCENT)
        body = _fit_w(_txt(vals[0], 38, TEXT), config.frame_width - 3.0)
        rule = Line(LEFT * 1.4, RIGHT * 1.4, stroke_width=3, color=ACCENT_W)
        who = _txt(vals[1], 28, MUTED)

        _stack([mark, body, rule, who], DOWN, 0.42).move_to(ORIGIN + UP * 0.1)

        self.play_t(FadeIn(mark), run_time=0.5)
        if _alive(body):
            self.play_t(FadeIn(body, shift=UP * 0.25), run_time=0.8)
        self.play_t(Create(rule), run_time=0.4)
        if _alive(who):
            self.play_t(FadeIn(who), run_time=0.45)
        self.finish(total)


class _Title(_Base):
    """بطاقة العنوان — هوية ثابتة لكل حلقة."""

    def build(self, items, total):
        vals = [str(i).strip() for i in items if str(i).strip()]
        title = _fit_w(_txt(vals[0] if vals else "", 66, TEXT),
                       config.frame_width - 2.0)
        rule = Line(LEFT * 2.2, RIGHT * 2.2, stroke_width=4, color=ACCENT_W)
        sub = _txt(vals[1] if len(vals) > 1 else "", 30, MUTED)
        _stack([title, rule, sub], DOWN, 0.5).move_to(ORIGIN)

        if _alive(title):
            self.play_t(FadeIn(title, shift=UP * 0.3), run_time=0.9)
        self.play_t(Create(rule), run_time=0.5)
        if _alive(sub):
            self.play_t(FadeIn(sub), run_time=0.5)
        self.finish(total)


class _Beats(_Base):
    """سلسلة لقطات مرسومة، كل لقطة مربوطة بالعبارة التي تُقال أثناءها.

    هذا هو المونتاج الذي يتبع الكلام: لا شاشة تبقى على حالها، ولا لقطة
    تتجاوز ثلاث ثوان، والرسم يسبق الكلمة بلحظة لأن العين أسرع من الأذن.
    """

    def build(self, beats, total):
        if not beats:
            self.finish(total)
            return

        for b in beats:
            dur = max(float(b.get("dur", MT.MIN_HOLD)), 0.25)
            dur = min(dur, MT.MAX_HOLD)          # الحدّ لا يُتجاوز أبدًا

            # الرسوم مبنيّة بـalways_redraw: محدّثها يعيد بناءها كل إطار،
            # فأي move_to أو FadeIn عليها يُمحى فورًا. نضيفها كما هي،
            # والرسم نفسه مُصمَّم حول المركز، والتسمية تُوضع بإحداثيّ ثابت.
            tracker = ValueTracker(0.0)
            art = DRAW.get(b.get("draw"))(PALETTE, tracker)
            self.add(art)

            label = _fit_w(_txt(b.get("label", ""), 34, TEXT),
                           config.frame_width - 3.4)
            used = 0.0
            if _alive(label):
                label.move_to(ORIGIN + DOWN * 2.45)
                fade = min(0.22, dur * 0.3)
                self.play_t(FadeIn(label, shift=UP * 0.15), run_time=fade)
                used = fade

            self.play_t(tracker.animate.set_value(1.0),
                        run_time=max(dur - used, 0.05),
                        rate_func=rate_functions.linear)

            art.clear_updaters()
            self.remove(art)
            if _alive(label):
                self.remove(label)

        self.finish(total)


_BUILDERS = {
    "beats": _Beats,
    "flow": _Flow, "bullets": _Bullets, "compare": _Compare,
    "wave": _Wave, "orbit": _Orbit, "stat": _Stat,
    "timeline": _Timeline, "profile": _Profile, "figure": _Profile,
    "quote": _Quote, "title": _Title,
}


# ------------------------------------------------------- المشهد الذي يُستدعى

def _resolve():
    global VISUAL
    if INDEX in ("intro", "outro"):
        block = SPEC[INDEX]
        VISUAL = {}
        return "title", block["items"], "", block.get("caption", ""), block["duration"]
    sec = SPEC["sections"][int(INDEX)]
    v = sec.get("visual", {})
    VISUAL = v

    # اللقطات هي الأصل: مونتاج يتبع الكلام. البطاقات تبقى للأقسام التي
    # لم يُولَّد لها لقطات (أو حين يتعذّر النموذج).
    beats = sec.get("beats")
    if beats:
        return ("beats", beats, sec.get("heading", ""),
                v.get("caption", ""), sec["duration"])

    return (v.get("type", "bullets"), v.get("items", []), sec.get("heading", ""),
            v.get("caption", ""), sec["duration"])


class SectionScene(_Base):
    def construct(self):
        vtype, items, heading, caption, duration = _resolve()
        cls = _BUILDERS.get(vtype, _Bullets)
        # نستعير منطق البناء من الصنف المناسب دون إنشاء مشهد جديد
        self.setup_stage(heading, caption)
        cls.build(self, items, float(duration))
