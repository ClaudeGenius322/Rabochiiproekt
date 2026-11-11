#!/usr/bin/env python3
"""Чертёж листа оргстекла 404 x 523 (проект «МАЗ РЕЙКИ»).

Генерирует:
  orgsteklo_404x523.dxf  - только контуры реза (слой CUT), мм, для лазера/ЧПУ
  orgsteklo_404x523.pdf  - чертёж с размерами, A3

Запуск:  python3 make_drawing.py
Зависимости:  pip install ezdxf reportlab

Система координат: начало (0,0) - левый нижний угол листа, X вправо, Y вверх, мм.
Все размеры, которые надо уточнить, собраны в словаре P ниже.
"""
import math
import os

import ezdxf
from ezdxf import units
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# --------------------------------------------------------------------------
# ПАРАМЕТРЫ
# --------------------------------------------------------------------------
P = dict(
    W=404.0,          # ширина листа - задано заказчиком
    H=523.0,          # высота листа - задано заказчиком
    T=3.0,            # толщина оргстекла - подтверждено заказчиком
    # треугольный вырез - измерено рулеткой по образцу и совпадает с моделью БАЗИС
    tri_leg=50.0,     # катеты 50 x 50, прямой угол вверху слева
    tri_off=16.0,     # отступ вершин от левой и от нижней кромки (= толщина ЛДСП)
    # отверстия под петли (2 шт., на ПРАВОЙ кромке) - Ø26 подтверждён заказчиком
    hinge_d=26.0,
    hinge_gap=5.0,    # * от правой кромки до края отверстия (замер на образце, центр ~18 мм)
    hinge_from_top=95.0,     # * от верхней кромки до центра верхней петли - оценка по скрину БАЗИС
    hinge_from_bottom=132.0, # * от нижней кромки до центра нижней петли - оценка по скрину БАЗИС
    # отверстие под замок (у левой кромки)
    lock_d=19.0,      # Ø под замок, круглое, без лысок - подтверждено заказчиком
    lock_x=33.0,      # * от левой кромки до оси замка (вылет язычка ~33) - оценка
    lock_from_top=261.5,  # * от верхней кромки до оси замка (середина высоты) - оценка
)

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "orgsteklo_404x523"


def geometry(p=P):
    """Вся геометрия в одном месте, чтобы DXF и PDF не расходились."""
    W, H = p["W"], p["H"]
    o, L = p["tri_off"], p["tri_leg"]
    A = (o, o + L)          # прямой угол (вверху слева)
    B = (o + L, o + L)      # конец горизонтального катета
    C = (o, o)              # нижняя вершина
    hr = p["hinge_d"] / 2
    hx = W - p["hinge_gap"] - hr
    return dict(
        outline=[(0, 0), (W, 0), (W, H), (0, H)],
        triangle=[A, B, C],
        hinges=[(hx, H - p["hinge_from_top"]), (hx, p["hinge_from_bottom"])],
        lock=(p["lock_x"], H - p["lock_from_top"]),
        hyp=math.hypot(L, L),
    )


# --------------------------------------------------------------------------
# DXF - только контуры реза
# --------------------------------------------------------------------------
def make_dxf(path, p=P):
    g = geometry(p)
    doc = ezdxf.new("R2010", setup=True)
    doc.units = units.MM
    doc.layers.add("CUT", color=7)
    msp = doc.modelspace()
    at = {"layer": "CUT"}
    msp.add_lwpolyline(g["outline"], close=True, dxfattribs=at)
    msp.add_lwpolyline(g["triangle"], close=True, dxfattribs=at)
    for c in g["hinges"]:
        msp.add_circle(c, p["hinge_d"] / 2, dxfattribs=at)
    msp.add_circle(g["lock"], p["lock_d"] / 2, dxfattribs=at)
    doc.saveas(path)


# --------------------------------------------------------------------------
# PDF - чертёж с размерами
# --------------------------------------------------------------------------
pdfmetrics.registerFont(TTFont("DV", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DVB", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))

THICK, THIN = 1.6, 0.5   # pt
TXT = 3.2                # высота цифр размеров, мм


def fmt(v):
    s = ("%.1f" % v).rstrip("0").rstrip(".")
    return s.replace(".", ",")


class View:
    """Вид с масштабом s; (ox, oy) - положение точки (0,0) модели на листе, мм."""

    def __init__(self, c, ox, oy, s):
        self.c, self.ox, self.oy, self.s = c, ox, oy, s

    def pt(self, x, y):
        return (self.ox + x * self.s) * mm, (self.oy + y * self.s) * mm

    def line(self, a, b, w=THICK, dash=None):
        c = self.c
        c.setLineWidth(w)
        c.setDash(dash or [])
        c.line(*self.pt(*a), *self.pt(*b))
        c.setDash([])

    def poly(self, pts, w=THICK):
        c = self.c
        c.setLineWidth(w)
        path = c.beginPath()
        path.moveTo(*self.pt(*pts[0]))
        for q in pts[1:]:
            path.lineTo(*self.pt(*q))
        path.close()
        c.drawPath(path, stroke=1, fill=0)

    def circle(self, cen, r, w=THICK):
        self.c.setLineWidth(w)
        x, y = self.pt(*cen)
        self.c.circle(x, y, r * self.s * mm, stroke=1, fill=0)

    def centermarks(self, cen, r):
        ext = r + 4
        x, y = cen
        self.line((x - ext, y), (x + ext, y), THIN, [8, 1.5, 1.5, 1.5])
        self.line((x, y - ext), (x, y + ext), THIN, [8, 1.5, 1.5, 1.5])

    # --- размеры (смещения off и вылеты - в мм на бумаге) -------------------
    def _arrow(self, x, y, ang, size=2.6):
        """Стрелка в точке (x,y) бумаги (мм), остриё направлено под углом ang."""
        c = self.c
        a = math.radians(ang)
        w = size / 3.6
        bx, by = x - size * math.cos(a), y - size * math.sin(a)
        nx, ny = -math.sin(a), math.cos(a)
        path = c.beginPath()
        path.moveTo(x * mm, y * mm)
        path.lineTo((bx + nx * w) * mm, (by + ny * w) * mm)
        path.lineTo((bx - nx * w) * mm, (by - ny * w) * mm)
        path.close()
        c.setFillColorRGB(0, 0, 0)
        c.drawPath(path, stroke=0, fill=1)

    def hdim(self, x1, x2, y_ref, off, text, y1=None, y2=None, outside=False):
        """Горизонтальный размер; линия на бумаге выше (off>0) / ниже (off<0) y_ref."""
        c = self.c
        y1 = y_ref if y1 is None else y1
        y2 = y_ref if y2 is None else y2
        py = self.oy + y_ref * self.s + off
        px1, px2 = self.ox + x1 * self.s, self.ox + x2 * self.s
        sgn = 1 if off > 0 else -1
        c.setLineWidth(THIN)
        for xx, yy in ((px1, y1), (px2, y2)):
            y0 = self.oy + yy * self.s
            c.line(xx * mm, (y0 + sgn * 1.0) * mm, xx * mm, (py + sgn * 1.8) * mm)
        lo, hi = min(px1, px2), max(px1, px2)
        if outside:
            c.line((lo - 7) * mm, py * mm, (hi + 7) * mm, py * mm)
            self._arrow(lo, py, 0)
            self._arrow(hi, py, 180)
        else:
            c.line(lo * mm, py * mm, hi * mm, py * mm)
            self._arrow(lo, py, 180)
            self._arrow(hi, py, 0)
        c.setFont("DV", TXT * 2.835 / 1.0 * 0.9)
        c.setFillColorRGB(0, 0, 0)
        c.drawCentredString((lo + hi) / 2 * mm, (py + 1.0) * mm, text)

    def vdim(self, y1, y2, x_ref, off, text, x1=None, x2=None):
        """Вертикальный размер; линия на бумаге правее (off>0) / левее (off<0) x_ref."""
        c = self.c
        x1 = x_ref if x1 is None else x1
        x2 = x_ref if x2 is None else x2
        px = self.ox + x_ref * self.s + off
        py1, py2 = self.oy + y1 * self.s, self.oy + y2 * self.s
        sgn = 1 if off > 0 else -1
        c.setLineWidth(THIN)
        for yy, xx in ((py1, x1), (py2, x2)):
            x0 = self.ox + xx * self.s
            c.line((x0 + sgn * 1.0) * mm, yy * mm, (px + sgn * 1.8) * mm, yy * mm)
        lo, hi = min(py1, py2), max(py1, py2)
        c.line(px * mm, lo * mm, px * mm, hi * mm)
        self._arrow(px, lo, 270)
        self._arrow(px, hi, 90)
        c.saveState()
        c.translate((px - 1.0) * mm, (lo + hi) / 2 * mm)
        c.rotate(90)
        c.setFont("DV", TXT * 2.835 * 0.9)
        c.setFillColorRGB(0, 0, 0)
        c.drawCentredString(0, 0, text)
        c.restoreState()

    def leader(self, cen, r, ang_deg, length, text, align="left"):
        """Выноска с диаметром: от окружности под углом, потом полка с текстом."""
        c = self.c
        a = math.radians(ang_deg)
        x0 = self.ox + cen[0] * self.s + r * self.s * math.cos(a)
        y0 = self.oy + cen[1] * self.s + r * self.s * math.sin(a)
        x1, y1 = x0 + length * math.cos(a), y0 + length * math.sin(a)
        c.setLineWidth(THIN)
        c.line(x0 * mm, y0 * mm, x1 * mm, y1 * mm)
        self._arrow(x0, y0, ang_deg + 180)
        tw = pdfmetrics.stringWidth(text, "DV", TXT * 2.835 * 0.9) / mm
        if align == "left":
            c.line(x1 * mm, y1 * mm, (x1 - tw - 2) * mm, y1 * mm)
            c.setFont("DV", TXT * 2.835 * 0.9)
            c.drawRightString((x1 - 1) * mm, (y1 + 0.8) * mm, text)
        else:
            c.line(x1 * mm, y1 * mm, (x1 + tw + 2) * mm, y1 * mm)
            c.setFont("DV", TXT * 2.835 * 0.9)
            c.drawString((x1 + 1) * mm, (y1 + 0.8) * mm, text)


def text(c, x, y, s, size=3.5, font="DV", align="l"):
    c.setFont(font, size * 2.835)
    c.setFillColorRGB(0, 0, 0)
    {"l": c.drawString, "c": c.drawCentredString, "r": c.drawRightString}[align](x * mm, y * mm, s)


def breakline(v, a, b, amp=1.2):
    """Волнистая линия обрыва (рисуется на бумаге) между точками модели a и b."""
    v.line(a, b, THIN)


def make_pdf(path, p=P):
    g = geometry(p)
    W, H, T = p["W"], p["H"], p["T"]
    o, L = p["tri_off"], p["tri_leg"]
    hd = p["hinge_d"]
    hr = hd / 2
    hcx = W - p["hinge_gap"] - hr           # x центров петельных отверстий
    ht, hb = p["hinge_from_top"], p["hinge_from_bottom"]
    hup = (hcx, H - ht)                     # верхняя петля

    PW, PH = 420, 297
    c = canvas.Canvas(path, pagesize=(PW * mm, PH * mm))
    c.setTitle("Оргстекло 404x523 - чертёж (черновик)")
    c.setAuthor("")

    # рамка
    c.setLineWidth(1.4)
    c.rect(20 * mm, 5 * mm, (PW - 25) * mm, (PH - 10) * mm)

    # ---------------- основной вид 1:2.5 ----------------
    s = 0.4
    VX, VY = 46, 58
    v = View(c, VX, VY, s)
    v.poly(g["outline"])
    v.poly(g["triangle"])
    for hc in g["hinges"]:
        v.circle(hc, hr)
        v.centermarks(hc, hr)
    v.circle(g["lock"], p["lock_d"] / 2)
    v.centermarks(g["lock"], p["lock_d"] / 2)

    # габариты
    v.hdim(0, W, H, 12, fmt(W))
    v.vdim(0, H, 0, -20, fmt(H))
    # привязка петель по правой кромке (цепочка)
    v.vdim(H - ht, H, W, 9, fmt(ht) + "*", x1=hcx, x2=W)
    v.vdim(hb, H - ht, W, 9, fmt(H - ht - hb) + "*", x1=hcx, x2=hcx)
    v.vdim(0, hb, W, 9, fmt(hb) + "*", x1=hcx, x2=W)
    # привязка замка
    v.vdim(H - p["lock_from_top"], H, 0, -9, fmt(p["lock_from_top"]) + "*",
           x1=g["lock"][0], x2=0)
    v.hdim(0, p["lock_x"], g["lock"][1], 12, fmt(p["lock_x"]) + "*",
           y1=g["lock"][1], y2=g["lock"][1])
    # выноски
    v.leader(g["hinges"][1], hr, -135, 10, "2 отв. Ø" + fmt(hd), align="left")
    v.leader(g["lock"], p["lock_d"] / 2, -45, 12, "Ø" + fmt(p["lock_d"]), align="right")

    # метки деталей: штрихпунктирные окружности вокруг зон А и Б
    def zone(cx, cy, r, label, lx, ly):
        px, py = v.pt(cx, cy)
        c.setLineWidth(THIN)
        c.setDash([5, 1.5])
        c.circle(px, py, r * mm, stroke=1, fill=0)
        c.setDash([])
        text(c, lx, ly, label, 4, "DVB", "c")

    pa = v.pt(o + L / 2, o + L / 2)
    pb = v.pt(*hup)
    zone(o + L / 2, o + L / 2, 16, "А", pa[0] / mm + 21, pa[1] / mm + 2)
    zone(hup[0], hup[1], 14, "Б", pb[0] / mm - 20, pb[1] / mm + 6)
    text(c, VX + (W / 2) * s, VY - 8, "Вид спереди, М 1:2,5", 3.5, "DV", "c")

    # ---------------- детали ----------------
    # Деталь А: треугольный вырез, М 2:1 (нижний левый угол листа)
    s2 = 2.0
    ax, ay = 268, 136
    a = View(c, ax, ay, s2)
    ext = 68
    a.line((0, 0), (ext, 0))            # нижняя кромка листа
    a.line((0, 0), (0, ext))            # левая кромка листа
    a.line((ext, 0), (ext, ext), THIN, [6, 2])   # границы фрагмента
    a.line((0, ext), (ext, ext), THIN, [6, 2])
    a.poly(g["triangle"])
    A_, B_, C_ = g["triangle"]
    a.hdim(0, o, 0, -9, fmt(o), y1=o, y2=o)                  # 16 от левой кромки
    a.vdim(0, o, 0, -9, fmt(o), x1=o, x2=o)                  # 16 от нижней кромки
    a.hdim(o, o + L, o + L, 11, fmt(L))                      # 50 - горизонтальный катет
    a.vdim(o, o + L, 0, -9, fmt(L), x1=o, x2=o)              # 50 - вертикальный катет (цепочка с 16)
    # гипотенуза - справочный размер
    mx, my = (B_[0] + C_[0]) / 2, (B_[1] + C_[1]) / 2
    hx, hy_ = a.pt(mx, my)
    text(c, hx / mm + 3, hy_ / mm - 9, "[%s]" % fmt(round(g["hyp"], 1)), 3.2, "DV", "l")
    text(c, ax + ext * s2 / 2, ay + ext * s2 + 14, "Деталь А (треугольный вырез), М 2:1", 3.5, "DVB", "c")

    # Деталь Б: отверстие под петлю на правой кромке, М 1:1
    # локальные координаты: (0,0) - центр отверстия; правая кромка листа - x = +gap+hr
    s1 = 1.0
    ex = p["hinge_gap"] + hr          # расстояние центр - правая кромка
    half = 30
    bcx, bcy = 330, 86                # положение центра отверстия на листе, мм
    b = View(c, bcx, bcy, s1)
    b.line((ex, -half), (ex, half))                        # правая кромка листа
    b.line((ex - 30, half), (ex, half), THIN, [6, 2])      # границы фрагмента
    b.line((ex - 30, -half), (ex, -half), THIN, [6, 2])
    b.circle((0, 0), hr)
    b.centermarks((0, 0), hr)
    b.hdim(0, ex, half, 8, fmt(ex) + "*", y1=0, y2=half)
    b.leader((0, 0), hr, -135, 9, "Ø" + fmt(hd), align="left")
    text(c, bcx - 4, bcy - half - 8, "Деталь Б, М 1:1", 3.5, "DVB", "c")

    # ---------------- примечания ----------------
    text(c, 24, 40, "Примечания:", 3.5, "DVB")
    notes = [
        "1. Материал: оргстекло прозрачное, толщина %s мм. Кромки - резка, без фаски." % fmt(T),
        "2. Размеры со звёздочкой (*) оценены по фото образца и скрину БАЗИС - подтвердить перед запуском в рез.",
        "3. Без звёздочки: габариты 404 × 523, Ø26 (петли), Ø19 (замок) - заказчик; треугольный вырез и отступ 16 - замер по образцу и БАЗИС.",
        "4. Петли - на правой кромке, замок - на левой (вид спереди). Деталь Б - отверстие верхней петли (нижнее такое же).",
        "5. Размер в квадратных скобках - справочный. Файл реза: %s.dxf (слой CUT, мм)." % NAME,
    ]
    for i, n in enumerate(notes):
        text(c, 24, 34 - i * 5, n, 3.0)

    # ---------------- штамп ----------------
    sx, sy, sw, sh = PW - 5 - 150, 5, 150, 40
    c.setLineWidth(1.4)
    c.rect(sx * mm, sy * mm, sw * mm, sh * mm)
    c.setLineWidth(0.5)
    c.line(sx * mm, (sy + 25) * mm, (sx + sw) * mm, (sy + 25) * mm)
    c.line(sx * mm, (sy + 12) * mm, (sx + sw) * mm, (sy + 12) * mm)
    c.line((sx + 90) * mm, sy * mm, (sx + 90) * mm, (sy + 25) * mm)
    text(c, sx + sw / 2, sy + 30, "Оргстекло 404 × 523, ЧЕРНОВИК", 6, "DVB", "c")
    text(c, sx + 3, sy + 17, "Проект: МАЗ РЕЙКИ (органайзер, ЛДСП 16 мм)", 3.4)
    text(c, sx + 3, sy + 5, "Материал: оргстекло, t = %s мм" % fmt(T), 3.4)
    text(c, sx + 93, sy + 17, "Масштаб: 1:2,5", 3.4)
    text(c, sx + 93, sy + 5, "Лист 1 из 1", 3.4)
    c.showPage()
    c.save()


if __name__ == "__main__":
    make_dxf(os.path.join(HERE, NAME + ".dxf"))
    make_pdf(os.path.join(HERE, NAME + ".pdf"))
    g = geometry()
    print("OK:", NAME, "hyp=%.2f" % g["hyp"])
