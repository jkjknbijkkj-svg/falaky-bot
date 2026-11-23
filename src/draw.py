"""
مكتبة الرسوم الشرحية — «ارسم ولا تكتب».

حين يقول الراوي «قطار» يظهر قطار يسير على قضبان وينفث دخانًا، لا كلمة
«قطار» مكتوبة. كل رسم هنا مبنيّ بالكود بالأسلوب المتوهّج نفسه: أشكال
مسطّحة بسيطة على خلفية داكنة، حولها هالة ناعمة.

كل رسم دالّة تأخذ:
    C : لوحة الألوان (bg, surface, accent, warm, text, muted)
    t : ValueTracker يتقدّم من 0 إلى 1 خلال اللقطة — منه تأتي كل حركة
وتعيد Mobject جاهزًا للإضافة. الحركة تُبنى بـalways_redraw فتتبع t تلقائيًا.

ANIMATED تضمّ أسماء الرسوم التي فيها حركة حقيقية — يتحقّق منها الدستور.
"""

import numpy as np
from manim import (
    VGroup, VMobject, Circle, Ellipse, Square, Rectangle, RoundedRectangle,
    Polygon, Line, Arc, Dot, Arrow, Triangle, always_redraw,
    ORIGIN, UP, DOWN, LEFT, RIGHT, PI, TAU,
)


# ------------------------------------------------------------ أدوات مشتركة

def glow(shape, color, layers=3, width=16, opacity=0.08):
    """هالة ناعمة حول الشكل — سرّ المظهر المتوهّج."""
    g = VGroup()
    for i in range(layers, 0, -1):
        c = shape.copy()
        c.set_stroke(color=color, width=width * i / layers, opacity=opacity)
        c.set_fill(opacity=0)
        g.add(c)
    g.add(shape)
    return g


def _poly(points, color, fill=0.9, stroke=2):
    return Polygon(*[np.array([x, y, 0.0]) for x, y in points],
                   stroke_color=color, stroke_width=stroke,
                   fill_color=color, fill_opacity=fill)


def _wheel(r, color):
    hub = Circle(radius=r, stroke_color=color, stroke_width=3,
                 fill_color=color, fill_opacity=0.25)
    spokes = VGroup(*[Line(ORIGIN, RIGHT * r * 0.8, stroke_width=2,
                           color=color).rotate(a, about_point=ORIGIN)
                      for a in np.linspace(0, PI, 4, endpoint=False)])
    return VGroup(hub, spokes)


def _puff(center, r, color, op):
    return Circle(radius=r, stroke_width=0, fill_color=color,
                  fill_opacity=op).move_to(center)


# ------------------------------------------------------------ نقل وحركة

def train(C, t):
    """قطار يسير على قضبان وينفث دخانًا — المثال الذي طُلب بالاسم."""
    rail = VGroup(
        Line(LEFT * 6, RIGHT * 6, stroke_width=4, color=C["muted"]).shift(DOWN * 1.6),
        Line(LEFT * 6, RIGHT * 6, stroke_width=2, color=C["muted"]).shift(DOWN * 1.8),
    )
    ties = always_redraw(lambda: VGroup(*[
        Line(UP * 0.12, DOWN * 0.12, stroke_width=3, color=C["muted"])
        .move_to([((x - 2.2 * t.get_value() * 3) % 12) - 6, -1.72, 0])
        for x in np.arange(-6, 6, 1.2)
    ]))

    body = RoundedRectangle(corner_radius=0.18, width=3.4, height=1.4,
                            stroke_color=C["accent"], stroke_width=3,
                            fill_color=C["accent"], fill_opacity=0.22)
    cab = RoundedRectangle(corner_radius=0.12, width=1.2, height=0.9,
                           stroke_color=C["accent"], stroke_width=3,
                           fill_color=C["accent"], fill_opacity=0.3)
    cab.next_to(body.get_top(), DOWN, buff=0).shift(LEFT * 0.9 + UP * 0.9)
    chimney = Rectangle(width=0.34, height=0.5, stroke_width=0,
                        fill_color=C["warm"], fill_opacity=0.9)
    chimney.move_to(body.get_top() + RIGHT * 1.1 + UP * 0.25)
    wheels = VGroup(*[_wheel(0.34, C["warm"]).move_to(body.get_bottom()
                                                      + RIGHT * x + DOWN * 0.1)
                      for x in (-1.1, 0.0, 1.1)])
    loco = VGroup(body, cab, chimney, wheels).shift(DOWN * 0.5)

    def smoke():
        p = t.get_value()
        g = VGroup()
        for k in range(5):
            f = (p * 1.6 + k * 0.22) % 1.0
            g.add(_puff(chimney.get_top() + UP * (f * 2.1) + LEFT * (f * 0.9),
                        0.16 + f * 0.34, C["text"], max(0.0, 0.5 * (1 - f))))
        return g

    return VGroup(rail, ties, glow(loco, C["accent"]), always_redraw(smoke))


def car(C, t):
    """سيارة بعجلات تدور."""
    body = _poly([(-1.7, -0.2), (-1.2, 0.45), (0.5, 0.6), (1.3, 0.1),
                  (1.8, 0.0), (1.8, -0.45), (-1.7, -0.45)], C["accent"], 0.25, 3)
    win = _poly([(-0.95, 0.3), (-0.6, 0.0), (0.35, 0.05), (0.4, 0.4)],
                C["text"], 0.35, 1)
    wheels = VGroup(*[always_redraw(
        lambda x=x: _wheel(0.36, C["warm"])
        .rotate(-t.get_value() * TAU * 2)
        .move_to([x, -0.52, 0])) for x in (-1.0, 0.95)])
    road = Line(LEFT * 5, RIGHT * 5, stroke_width=3,
                color=C["muted"]).shift(DOWN * 0.9)
    return VGroup(road, glow(VGroup(body, win), C["accent"]), wheels)


def person(C, t):
    """شخص — رأس وجذع، يتنفّس قليلًا."""
    def fig():
        s = 1 + 0.03 * np.sin(t.get_value() * TAU * 2)
        head = Circle(radius=0.55, stroke_width=0,
                      fill_color=C["accent"], fill_opacity=0.55).shift(UP * 1.3)
        eyes = VGroup(*[Ellipse(width=0.16, height=0.3, stroke_width=0,
                                fill_color=C["text"], fill_opacity=1)
                        .shift(UP * 1.35 + RIGHT * dx) for dx in (-0.2, 0.2)])
        torso = Arc(radius=1.15, start_angle=0, angle=PI, stroke_width=0,
                    fill_color=C["accent"], fill_opacity=0.4).shift(DOWN * 0.35)
        return VGroup(torso.scale(s), head, eyes)
    return always_redraw(fig)


# ------------------------------------------------------------ كهرباء ودارات

def battery(C, t):
    """بطارية يرتفع شحنها وتتدفّق منها الأيونات."""
    shell = RoundedRectangle(corner_radius=0.12, width=2.6, height=1.5,
                             stroke_color=C["accent"], stroke_width=4,
                             fill_opacity=0)
    cap = Rectangle(width=0.18, height=0.5, stroke_width=0,
                    fill_color=C["accent"], fill_opacity=1)
    cap.next_to(shell, RIGHT, buff=0)

    def level():
        p = 0.2 + 0.75 * t.get_value()
        bar = Rectangle(width=2.3 * p, height=1.15, stroke_width=0,
                        fill_color=C["warm"], fill_opacity=0.85)
        bar.align_to(shell, LEFT).shift(RIGHT * 0.15)
        bar.set_y(shell.get_y())
        return bar
    return VGroup(glow(shell, C["accent"]), cap, always_redraw(level))


def bulb(C, t):
    """مصباح يضيء تدريجيًا وتخرج منه أشعّة."""
    def lamp():
        p = t.get_value()
        b = Circle(radius=0.85, stroke_color=C["warm"], stroke_width=3,
                   fill_color=C["warm"], fill_opacity=0.15 + 0.55 * p)
        base = Rectangle(width=0.6, height=0.5, stroke_width=0,
                         fill_color=C["muted"], fill_opacity=0.9)
        base.next_to(b, DOWN, buff=0)
        rays = VGroup(*[Line(ORIGIN, RIGHT * (0.35 + 0.5 * p), stroke_width=4,
                             color=C["warm"])
                        .shift(RIGHT * 1.05).rotate(a, about_point=ORIGIN)
                        for a in np.linspace(0, TAU, 10, endpoint=False)])
        rays.set_opacity(p)
        return VGroup(rays, b, base)
    return always_redraw(lamp)


def wire(C, t):
    """سلك تسري فيه إلكترونات من اليمين إلى اليسار."""
    path = Line(RIGHT * 4.5, LEFT * 4.5, stroke_width=6, color=C["muted"])
    def flow():
        p = t.get_value()
        g = VGroup()
        for k in range(7):
            f = (p * 1.4 + k / 7) % 1.0
            g.add(Dot(point=[4.5 - 9 * f, 0, 0], radius=0.13, color=C["accent"]))
        return g
    return VGroup(path, always_redraw(flow))


def switch(C, t):
    """مفتاح يُغلق الدارة فيمرّ التيار."""
    def sw():
        closed = t.get_value() > 0.45
        left = Line(LEFT * 2.2, LEFT * 0.7, stroke_width=6, color=C["muted"])
        right = Line(RIGHT * 0.7, RIGHT * 2.2, stroke_width=6, color=C["muted"])
        lever = Line(LEFT * 0.7, RIGHT * 0.7 if closed else
                     np.array([0.3, 0.9, 0.0]), stroke_width=6,
                     color=C["warm"] if closed else C["muted"])
        dots = VGroup(Dot(LEFT * 0.7, radius=0.1, color=C["accent"]),
                      Dot(RIGHT * 0.7, radius=0.1, color=C["accent"]))
        out = VGroup(left, right, lever, dots)
        return glow(out, C["warm"]) if closed else out
    return always_redraw(sw)


def resistor(C, t):
    """مقاومة متعرّجة يتصاعد منها الحرّ."""
    pts = [[-2.4, 0, 0], [-1.2, 0, 0]]
    for i, y in enumerate([0.5, -0.5] * 3):
        pts.append([-1.2 + 0.4 * (i + 1), y, 0])
    pts += [[1.2, 0, 0], [2.4, 0, 0]]
    z = VMobject(stroke_color=C["accent"], stroke_width=6)
    z.set_points_as_corners([np.array(p) for p in pts])

    def waves():
        p = t.get_value()
        g = VGroup()
        for k in range(4):
            f = (p * 1.3 + k * 0.25) % 1.0
            arc = Arc(radius=0.28, start_angle=PI * 0.15, angle=PI * 0.7,
                      stroke_width=3, color=C["warm"])
            arc.move_to([-0.9 + k * 0.6, 0.7 + f * 1.1, 0])
            arc.set_opacity(max(0.0, 1 - f))
            g.add(arc)
        return g
    return VGroup(glow(z, C["accent"]), always_redraw(waves))


def chip(C, t):
    """معالج بأرجل، تنبض نواته."""
    body = RoundedRectangle(corner_radius=0.14, width=2.6, height=2.6,
                            stroke_color=C["accent"], stroke_width=3,
                            fill_color=C["surface"], fill_opacity=1)
    pins = VGroup()
    for i in range(6):
        y = -1.0 + i * 0.4
        pins.add(Line([-1.3, y, 0], [-1.75, y, 0], stroke_width=4, color=C["warm"]))
        pins.add(Line([1.3, y, 0], [1.75, y, 0], stroke_width=4, color=C["warm"]))
    def core():
        p = 0.5 + 0.5 * np.sin(t.get_value() * TAU * 2)
        return Square(side_length=1.1, stroke_color=C["warm"], stroke_width=3,
                      fill_color=C["warm"], fill_opacity=0.15 + 0.45 * p)
    return VGroup(pins, glow(body, C["accent"]), always_redraw(core))


def plug(C, t):
    """قابس يدخل مقبسًا."""
    socket = RoundedRectangle(corner_radius=0.15, width=1.8, height=2.2,
                              stroke_color=C["muted"], stroke_width=4,
                              fill_color=C["surface"], fill_opacity=1)
    socket.shift(RIGHT * 1.6)
    holes = VGroup(*[Rectangle(width=0.16, height=0.5, stroke_width=0,
                               fill_color=C["bg"], fill_opacity=1)
                     .shift(RIGHT * 1.6 + UP * dy) for dy in (0.45, -0.45)])
    def head():
        x = -1.8 + 2.4 * min(1.0, t.get_value() * 1.5)
        body = RoundedRectangle(corner_radius=0.12, width=1.4, height=1.8,
                                stroke_color=C["accent"], stroke_width=3,
                                fill_color=C["accent"], fill_opacity=0.3)
        pins = VGroup(*[Rectangle(width=0.5, height=0.14, stroke_width=0,
                                  fill_color=C["warm"], fill_opacity=1)
                        .shift(RIGHT * 0.9 + UP * dy) for dy in (0.45, -0.45)])
        return VGroup(body, pins).shift(RIGHT * x)
    return VGroup(socket, holes, always_redraw(head))


def solar(C, t):
    """لوح شمسي تسقط عليه أشعّة."""
    panel = _poly([(-2.0, -0.6), (2.0, -0.6), (1.5, 0.7), (-2.5, 0.7)],
                  C["accent"], 0.3, 3)
    grid = VGroup(*[Line([x, -0.6, 0], [x - 0.5, 0.7, 0], stroke_width=2,
                         color=C["bg"]) for x in np.arange(-1.5, 2.0, 0.6)])
    sun = Circle(radius=0.5, stroke_width=0, fill_color=C["warm"],
                 fill_opacity=0.9).shift(UP * 2.3 + RIGHT * 2.2)
    def beams():
        p = t.get_value()
        g = VGroup()
        for k in range(5):
            f = (p * 1.5 + k * 0.2) % 1.0
            s = sun.get_center() + np.array([-0.3 * k, 0, 0])
            g.add(Line(s, s + np.array([-1.4, -2.2, 0]) * f,
                       stroke_width=3, color=C["warm"]).set_opacity(1 - f * 0.7))
        return g
    return VGroup(always_redraw(beams), glow(panel, C["accent"]), grid, sun)


# ------------------------------------------------------------ مادّة وطاقة

def atom(C, t):
    """ذرّة: نواة وإلكترونات تدور."""
    nucleus = Circle(radius=0.42, stroke_width=0, fill_color=C["warm"],
                     fill_opacity=1)
    rings = VGroup(*[Ellipse(width=w, height=w * 0.42, stroke_color=C["muted"],
                             stroke_width=2, stroke_opacity=0.6).rotate(a)
                     for w, a in ((3.4, 0), (3.4, PI / 3), (3.4, -PI / 3))])
    def els():
        p = t.get_value() * TAU
        g = VGroup()
        for k, a in enumerate((0, PI / 3, -PI / 3)):
            ang = p * (1 + k * 0.3) + k * 2
            pt = np.array([1.7 * np.cos(ang), 0.71 * np.sin(ang), 0])
            rot = np.array([pt[0] * np.cos(a) - pt[1] * np.sin(a),
                            pt[0] * np.sin(a) + pt[1] * np.cos(a), 0])
            g.add(Dot(point=rot, radius=0.13, color=C["accent"]))
        return g
    return VGroup(rings, glow(nucleus, C["warm"]), always_redraw(els))


def electron(C, t):
    """إلكترون منفرد يعبر الشاشة ويترك أثرًا."""
    def e():
        p = t.get_value()
        x = 4.0 - 8.0 * p
        trail = VGroup(*[Dot(point=[x + 0.45 * k, 0, 0], radius=0.12 - 0.02 * k,
                             color=C["accent"]).set_opacity(0.6 - 0.15 * k)
                         for k in range(4)])
        return VGroup(trail, Dot(point=[x, 0, 0], radius=0.2, color=C["accent"]))
    return always_redraw(e)


def heat(C, t):
    """حرارة متصاعدة فوق سطح."""
    base = Line(LEFT * 2.5, RIGHT * 2.5, stroke_width=6, color=C["warm"])
    def waves():
        p = t.get_value()
        g = VGroup()
        for k in range(6):
            f = (p * 1.2 + k / 6) % 1.0
            x = -2.0 + k * 0.8
            w = VMobject(stroke_color=C["warm"], stroke_width=3)
            w.set_points_as_corners([
                np.array([x + 0.25 * np.sin(u * 6 + p * 8), u * 1.6 + f * 0.9, 0])
                for u in np.linspace(0, 1, 18)])
            w.set_opacity(max(0.0, 1 - f))
            g.add(w)
        return g
    return VGroup(always_redraw(waves), base)


def wave(C, t):
    """موجة تسير."""
    def w():
        p = t.get_value() * TAU * 2
        m = VMobject(stroke_color=C["accent"], stroke_width=6)
        m.set_points_as_corners([
            np.array([x, 1.1 * np.sin(1.4 * x + p), 0])
            for x in np.linspace(-5.4, 5.4, 150)])
        return m
    axis = Line(LEFT * 5.6, RIGHT * 5.6, stroke_width=2, color=C["muted"])
    return VGroup(axis, always_redraw(w))


def lightning(C, t):
    """صاعقة تومض."""
    bolt = _poly([(-0.5, 1.6), (0.35, 0.25), (-0.05, 0.25), (0.6, -1.6),
                  (-0.3, -0.1), (0.1, -0.1)], C["warm"], 1.0, 0)
    def flash():
        p = t.get_value()
        b = bolt.copy()
        b.set_opacity(0.35 + 0.65 * abs(np.sin(p * TAU * 3)))
        return glow(b, C["warm"], layers=4, opacity=0.12)
    return always_redraw(flash)


def magnet(C, t):
    """مغناطيس وخطوط مجاله."""
    u = _poly([(-1.1, 0.9), (-0.45, 0.9), (-0.45, -0.5), (0.45, -0.5),
               (0.45, 0.9), (1.1, 0.9), (1.1, -1.1), (-1.1, -1.1)],
              C["accent"], 0.35, 3)
    poles = VGroup(
        Rectangle(width=0.65, height=0.35, stroke_width=0, fill_color=C["warm"],
                  fill_opacity=1).move_to([-0.78, 0.92, 0]),
        Rectangle(width=0.65, height=0.35, stroke_width=0, fill_color=C["muted"],
                  fill_opacity=1).move_to([0.78, 0.92, 0]))
    def field():
        p = t.get_value()
        g = VGroup()
        for k in range(4):
            f = (p + k * 0.25) % 1.0
            r = 0.6 + f * 1.8
            g.add(Arc(radius=r, start_angle=PI * 0.12, angle=PI * 0.76,
                      stroke_width=3, color=C["accent"])
                  .shift(UP * 0.9).set_opacity(max(0.0, 1 - f)))
        return g
    return VGroup(always_redraw(field), glow(u, C["accent"]), poles)


def motor(C, t):
    """محرّك يدور."""
    case = Circle(radius=1.5, stroke_color=C["accent"], stroke_width=4,
                  fill_color=C["surface"], fill_opacity=1)
    def rotor():
        a = t.get_value() * TAU * 3
        arms = VGroup(*[Rectangle(width=2.2, height=0.28, stroke_width=0,
                                  fill_color=C["warm"], fill_opacity=0.95)
                        .rotate(a + k * PI / 3) for k in range(3)])
        return VGroup(arms, Circle(radius=0.26, stroke_width=0,
                                   fill_color=C["text"], fill_opacity=1))
    shaft = Rectangle(width=1.2, height=0.2, stroke_width=0,
                      fill_color=C["muted"], fill_opacity=1).shift(RIGHT * 2.0)
    return VGroup(glow(case, C["accent"]), always_redraw(rotor), shaft)


def gear(C, t):
    """ترسان متعاشقان يدوران في اتجاهين."""
    def one(r, teeth, color):
        g = VGroup(Circle(radius=r, stroke_color=color, stroke_width=4,
                          fill_color=color, fill_opacity=0.15))
        for a in np.linspace(0, TAU, teeth, endpoint=False):
            g.add(Rectangle(width=r * 0.3, height=r * 0.34, stroke_width=0,
                            fill_color=color, fill_opacity=1)
                  .move_to([r * np.cos(a), r * np.sin(a), 0]).rotate(a))
        return g
    def pair():
        a = t.get_value() * TAU
        g1 = one(1.1, 10, C["accent"]).rotate(a).shift(LEFT * 1.1)
        g2 = one(0.75, 7, C["warm"]).rotate(-a * 1.45).shift(RIGHT * 1.0 + DOWN * 0.3)
        return VGroup(g1, g2)
    return always_redraw(pair)


def fan(C, t):
    """مروحة تدور."""
    ring = Circle(radius=1.6, stroke_color=C["muted"], stroke_width=4,
                  fill_opacity=0)
    def blades():
        a = t.get_value() * TAU * 4
        g = VGroup()
        for k in range(4):
            b = Ellipse(width=1.9, height=0.7, stroke_width=0,
                        fill_color=C["accent"], fill_opacity=0.6)
            b.shift(RIGHT * 0.75).rotate(a + k * PI / 2, about_point=ORIGIN)
            g.add(b)
        return VGroup(g, Circle(radius=0.25, stroke_width=0,
                                fill_color=C["warm"], fill_opacity=1))
    return VGroup(ring, always_redraw(blades))


def thermometer(C, t):
    """ميزان حرارة يرتفع."""
    tube = RoundedRectangle(corner_radius=0.22, width=0.55, height=3.2,
                            stroke_color=C["muted"], stroke_width=4,
                            fill_color=C["surface"], fill_opacity=1)
    bulbb = Circle(radius=0.48, stroke_color=C["muted"], stroke_width=4,
                   fill_color=C["warm"], fill_opacity=1).shift(DOWN * 1.8)
    def mercury():
        p = 0.15 + 0.8 * t.get_value()
        return Rectangle(width=0.28, height=3.0 * p, stroke_width=0,
                         fill_color=C["warm"], fill_opacity=1)\
            .align_to(tube, DOWN).shift(UP * 0.12)
    return VGroup(tube, always_redraw(mercury), glow(bulbb, C["warm"]))


# ------------------------------------------------------------ أجهزة ومشاهد

def phone(C, t):
    """هاتف تضيء شاشته."""
    body = RoundedRectangle(corner_radius=0.28, width=1.9, height=3.6,
                            stroke_color=C["accent"], stroke_width=4,
                            fill_color=C["surface"], fill_opacity=1)
    def screen():
        p = 0.25 + 0.6 * abs(np.sin(t.get_value() * TAU))
        return RoundedRectangle(corner_radius=0.16, width=1.55, height=3.0,
                                stroke_width=0, fill_color=C["accent"],
                                fill_opacity=p).shift(UP * 0.12)
    home = Line(LEFT * 0.3, RIGHT * 0.3, stroke_width=4,
                color=C["muted"]).shift(DOWN * 1.6)
    return VGroup(glow(body, C["accent"]), always_redraw(screen), home)


def laptop(C, t):
    """حاسوب محمول."""
    screen = RoundedRectangle(corner_radius=0.12, width=3.4, height=2.2,
                              stroke_color=C["accent"], stroke_width=3,
                              fill_color=C["surface"], fill_opacity=1).shift(UP * 0.9)
    def lit():
        p = 0.2 + 0.5 * abs(np.sin(t.get_value() * TAU))
        return Rectangle(width=3.1, height=1.9, stroke_width=0,
                         fill_color=C["accent"], fill_opacity=p).shift(UP * 0.9)
    base = _poly([(-2.2, -0.3), (2.2, -0.3), (1.8, -0.55), (-1.8, -0.55)],
                 C["muted"], 0.9, 0)
    return VGroup(screen, always_redraw(lit), base)


def building(C, t):
    """مبنى بنوافذ تضيء تباعًا."""
    body = Rectangle(width=2.8, height=3.6, stroke_color=C["accent"],
                     stroke_width=3, fill_color=C["surface"], fill_opacity=1)
    roof = _poly([(-1.6, 1.8), (1.6, 1.8), (0, 2.6)], C["accent"], 0.5, 2)
    def wins():
        p = t.get_value()
        g = VGroup()
        for i in range(4):
            for j in range(3):
                k = i * 3 + j
                on = ((p * 12 + k) % 12) < 7
                g.add(Rectangle(width=0.5, height=0.45, stroke_width=0,
                                fill_color=C["warm"] if on else C["bg"],
                                fill_opacity=0.9)
                      .move_to([-0.85 + j * 0.85, 1.2 - i * 0.85, 0]))
        return g
    return VGroup(glow(body, C["accent"]), roof, always_redraw(wins))


def factory(C, t):
    """مصنع بمداخن تدخّن."""
    body = Rectangle(width=3.6, height=1.8, stroke_color=C["accent"],
                     stroke_width=3, fill_color=C["surface"],
                     fill_opacity=1).shift(DOWN * 0.6)
    stacks = VGroup(*[Rectangle(width=0.5, height=1.4, stroke_width=0,
                                fill_color=C["muted"], fill_opacity=1)
                      .move_to([x, 0.9, 0]) for x in (-1.1, 0.1)])
    def smoke():
        p = t.get_value()
        g = VGroup()
        for i, x in enumerate((-1.1, 0.1)):
            for k in range(4):
                f = (p * 1.4 + k * 0.25 + i * 0.1) % 1.0
                g.add(_puff([x - f * 0.5, 1.6 + f * 1.6, 0], 0.18 + f * 0.3,
                            C["text"], max(0.0, 0.45 * (1 - f))))
        return g
    return VGroup(always_redraw(smoke), stacks, glow(body, C["accent"]))


def lab(C, t):
    """دورق يغلي فيه السائل."""
    flask = _poly([(-0.35, 1.3), (0.35, 1.3), (0.35, 0.5), (1.3, -1.2),
                   (-1.3, -1.2), (-0.35, 0.5)], C["accent"], 0.12, 3)
    liquid = _poly([(0.95, -0.55), (1.3, -1.2), (-1.3, -1.2), (-0.95, -0.55)],
                   C["warm"], 0.7, 0)
    def bubbles():
        p = t.get_value()
        g = VGroup()
        for k in range(6):
            f = (p * 1.6 + k / 6) % 1.0
            g.add(Circle(radius=0.07 + 0.05 * f, stroke_width=0,
                         fill_color=C["text"], fill_opacity=0.7 * (1 - f))
                  .move_to([-0.6 + k * 0.25, -1.1 + f * 1.4, 0]))
        return g
    return VGroup(glow(flask, C["accent"]), liquid, always_redraw(bubbles))


def clock(C, t):
    """ساعة تدقّ."""
    face = Circle(radius=1.5, stroke_color=C["accent"], stroke_width=4,
                  fill_color=C["surface"], fill_opacity=1)
    ticks = VGroup(*[Line(RIGHT * 1.25, RIGHT * 1.42, stroke_width=3,
                          color=C["muted"]).rotate(a, about_point=ORIGIN)
                     for a in np.linspace(0, TAU, 12, endpoint=False)])
    def hands():
        p = t.get_value()
        h = Line(ORIGIN, UP * 0.8, stroke_width=6,
                 color=C["text"]).rotate(-p * TAU * 0.5, about_point=ORIGIN)
        m = Line(ORIGIN, UP * 1.15, stroke_width=4,
                 color=C["warm"]).rotate(-p * TAU * 3, about_point=ORIGIN)
        return VGroup(h, m, Dot(ORIGIN, radius=0.09, color=C["warm"]))
    return VGroup(glow(face, C["accent"]), ticks, always_redraw(hands))


def money(C, t):
    """عملة تدور."""
    def coin():
        p = abs(np.cos(t.get_value() * TAU))
        c = Ellipse(width=0.4 + 1.8 * p, height=2.2, stroke_color=C["warm"],
                    stroke_width=4, fill_color=C["warm"], fill_opacity=0.25)
        return glow(c, C["warm"])
    return always_redraw(coin)


def book(C, t):
    """كتاب تتقلّب صفحاته."""
    left = _poly([(-2.0, 1.2), (-0.05, 1.0), (-0.05, -1.2), (-2.0, -1.0)],
                 C["accent"], 0.22, 3)
    right = _poly([(2.0, 1.2), (0.05, 1.0), (0.05, -1.2), (2.0, -1.0)],
                  C["accent"], 0.22, 3)
    def page():
        p = (t.get_value() * 1.5) % 1.0
        w = 1.9 * np.cos(p * PI)
        return _poly([(0, 1.05), (w, 1.15), (w, -1.1), (0, -1.15)],
                     C["text"], 0.35, 1)
    return VGroup(glow(VGroup(left, right), C["accent"]), always_redraw(page))


def sun(C, t):
    """شمس بأشعّة تنبض."""
    core = Circle(radius=1.0, stroke_width=0, fill_color=C["warm"],
                  fill_opacity=0.95)
    def rays():
        p = t.get_value()
        g = VGroup()
        for i, a in enumerate(np.linspace(0, TAU, 12, endpoint=False)):
            ln = 0.45 + 0.3 * np.sin(p * TAU * 2 + i)
            g.add(Line(RIGHT * 1.25, RIGHT * (1.25 + ln), stroke_width=5,
                       color=C["warm"]).rotate(a, about_point=ORIGIN))
        return g
    return VGroup(always_redraw(rays), glow(core, C["warm"], layers=4))


def antenna(C, t):
    """برج يبثّ موجات."""
    mast = VGroup(
        Line([0, -1.6, 0], [0, 1.4, 0], stroke_width=5, color=C["muted"]),
        Line([-0.8, -1.6, 0], [0, 0.4, 0], stroke_width=3, color=C["muted"]),
        Line([0.8, -1.6, 0], [0, 0.4, 0], stroke_width=3, color=C["muted"]))
    def pulses():
        p = t.get_value()
        g = VGroup()
        for k in range(4):
            f = (p * 1.5 + k * 0.25) % 1.0
            g.add(Arc(radius=0.5 + f * 2.3, start_angle=PI * 0.18,
                      angle=PI * 0.64, stroke_width=3, color=C["accent"])
                  .shift(UP * 1.4).set_opacity(max(0.0, 1 - f)))
        return g
    return VGroup(always_redraw(pulses), mast,
                  Dot([0, 1.4, 0], radius=0.14, color=C["warm"]))


def arrow_flow(C, t):
    """أسهم متتابعة من اليمين إلى اليسار — اتجاه القراءة العربي."""
    def arrows():
        p = t.get_value()
        g = VGroup()
        for k in range(5):
            f = (p * 1.3 + k / 5) % 1.0
            x = 4.2 - 8.4 * f
            g.add(Arrow([x + 0.9, 0, 0], [x, 0, 0], buff=0, stroke_width=7,
                        color=C["accent"],
                        max_tip_length_to_length_ratio=0.45)
                  .set_opacity(min(1.0, 2.2 * min(f, 1 - f) + 0.25)))
        return g
    return always_redraw(arrows)


def pulse(C, t):
    """نبضة عامّة — الرسم الافتراضي حين لا يُحدّد غيره."""
    def p():
        s = 0.6 + 0.5 * abs(np.sin(t.get_value() * TAU))
        c = Circle(radius=1.1 * s, stroke_color=C["accent"], stroke_width=5,
                   fill_color=C["accent"], fill_opacity=0.12)
        return glow(c, C["accent"])
    return always_redraw(p)


# ------------------------------------------------------------ الفهرس

CATALOG = {
    "train": train, "car": car, "person": person,
    "battery": battery, "bulb": bulb, "wire": wire, "switch": switch,
    "resistor": resistor, "chip": chip, "plug": plug, "solar": solar,
    "atom": atom, "electron": electron, "heat": heat, "wave": wave,
    "lightning": lightning, "magnet": magnet, "motor": motor, "gear": gear,
    "fan": fan, "thermometer": thermometer,
    "phone": phone, "laptop": laptop, "building": building,
    "factory": factory, "lab": lab, "clock": clock, "money": money,
    "book": book, "sun": sun, "antenna": antenna,
    "arrow_flow": arrow_flow, "pulse": pulse,
}

# كلّها متحرّكة بحكم التصميم: لا رسم ساكن في هذه المكتبة
ANIMATED = set(CATALOG)

NAMES = sorted(CATALOG)

# مصدر الحقيقة للأسماء هو montage.DRAW_NAMES لأن مولّد النصّ يقرأ منه
# دون استيراد Manim. نتحقّق من التطابق هنا فلا يفترق الاثنان صامتَين.
try:
    import montage as _MT
    _missing = set(_MT.DRAW_NAMES) - set(CATALOG)
    _extra = set(CATALOG) - set(_MT.DRAW_NAMES)
    if _missing or _extra:
        print(f"[draw] تحذير: فهرس الرسوم لا يطابق montage.DRAW_NAMES "
              f"(ناقص: {sorted(_missing)} | زائد: {sorted(_extra)})")
except Exception:
    pass


def get(name):
    return CATALOG.get(str(name).strip().lower(), pulse)
