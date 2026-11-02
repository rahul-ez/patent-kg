"""Generate the overlap-free Chen patent data sheet as SVG and a single-page PDF.

Documentation-only dependency: reportlab. Does not change the combined PDF.
"""
from __future__ import annotations

import html
import math
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[3]
W, H = 2800, 2100


class Sheet:
    def __init__(self):
        font_dir = Path("C:/Windows/Fonts")
        for name, filename in [("Chen", "arial.ttf"), ("ChenBold", "arialbd.ttf")]:
            pdfmetrics.registerFont(TTFont(name, str(font_dir / filename)))
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">',
                    '<title id="title">Patent knowledge data Chen ER diagram</title>',
                    '<desc id="desc">Sheet 1: patent metadata, parties, classifications, citations, family links and snapshots. Separate routing lanes keep relationships clear of attributes.</desc>',
                    '<rect width="2800" height="2100" fill="#fff"/>']
        self.pdf_path = ROOT / "output/pdf/patent-er-sheet-1.pdf"
        self.pdf_path.parent.mkdir(parents=True, exist_ok=True)
        self.pdf = canvas.Canvas(str(self.pdf_path), pagesize=(W * .6, H * .6))
        self.pdf.scale(.6, .6)
        self.pdf.setTitle("Patent Intelligence Platform - Chen ER Diagram - Sheet 1")
        self.nodes = []
        self.paths = []

    def text(self, x, y, label, size=19, bold=False, anchor="middle", color="#172033", key=False):
        underline = ' text-decoration="underline"' if key else ''
        weight = 'bold' if bold else 'normal'
        self.svg.append(f'<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" dominant-baseline="middle" fill="{color}"{underline}>{html.escape(label)}</text>')
        font = "ChenBold" if bold else "Chen"
        self.pdf.setFont(font, size)
        self.pdf.setFillColor(HexColor(color))
        width = pdfmetrics.stringWidth(label, font, size)
        start = x - width / 2 if anchor == "middle" else x
        baseline = H - y - size * .32
        self.pdf.drawString(start, baseline, label)
        if key:
            self.pdf.setStrokeColor(HexColor(color))
            self.pdf.setLineWidth(.9)
            self.pdf.line(start, baseline - 2, start + width, baseline - 2)

    def node(self, kind, x, y, a, b, label, key=False):
        self.nodes.append((kind, x, y, a, b, label))
        fill, stroke = ("#eef6ff", "#2563eb") if kind == "entity" else (("#fff8df", "#a16207") if kind == "relationship" else ("#ffffff", "#64748b"))
        self.pdf.setFillColor(HexColor(fill))
        self.pdf.setStrokeColor(HexColor(stroke))
        self.pdf.setLineWidth(2.2 if kind == "attribute" else 3)
        style = f'fill="{fill}" stroke="{stroke}" stroke-width="{2.2 if kind == "attribute" else 3}"'
        if kind == "entity":
            self.svg.append(f'<rect x="{x}" y="{y}" width="{a}" height="{b}" {style}/>')
            self.pdf.rect(x, H-y-b, a, b, fill=1, stroke=1)
            self.text(x+a/2, y+b/2, label, size=24, bold=True)
        elif kind == "attribute":
            self.svg.append(f'<ellipse cx="{x}" cy="{y}" rx="{a}" ry="{b}" {style}/>')
            self.pdf.ellipse(x-a, H-y-b, x+a, H-y+b, fill=1, stroke=1)
            self.text(x, y, label, key=key)
        else:
            points = [(x, y-b), (x+a, y), (x, y+b), (x-a, y)]
            coords = ' '.join(f'{px},{py}' for px, py in points)
            self.svg.append(f'<polygon points="{coords}" {style}/>')
            path = self.pdf.beginPath()
            path.moveTo(points[0][0], H-points[0][1])
            for px, py in points[1:]:
                path.lineTo(px, H-py)
            path.close()
            self.pdf.drawPath(path, fill=1, stroke=1)
            lines = label.split('|')
            for i, line in enumerate(lines):
                self.text(x, y + (i-(len(lines)-1)/2)*24, line, size=17, bold=True)

    def path(self, *points):
        self.paths.append(points)
        coords = ' '.join(('M' if i == 0 else 'L') + f'{x} {y}' for i, (x, y) in enumerate(points))
        self.svg.append(f'<path d="{coords}" fill="none" stroke="#64748b" stroke-width="2.5" stroke-linejoin="round"/>')
        self.pdf.setStrokeColor(HexColor("#64748b"))
        self.pdf.setLineWidth(2.5)
        path = self.pdf.beginPath()
        path.moveTo(points[0][0], H-points[0][1])
        for x, y in points[1:]:
            path.lineTo(x, H-y)
        self.pdf.drawPath(path)

    def card(self, x, y, label):
        self.text(x, y, label, size=21, bold=True, color="#9a3412")

    def finish(self):
        boxes = []
        for kind, x, y, a, b, label in self.nodes:
            box = (x, y, x+a, y+b) if kind == "entity" else (x-a, y-b, x+a, y+b)
            assert 35 <= box[0] < box[2] <= W-35 and 150 <= box[1] < box[3] <= H-70, label
            for other, other_label in boxes:
                assert not (box[0] < other[2] and other[0] < box[2]
                            and box[1] < other[3] and other[1] < box[3]), (label, other_label)
            boxes.append((box,label))
        # Check complete connector segments, including hidden portions: no line
        # may enter any entity, diamond or attribute interior.
        for points in self.paths:
            for (x1, y1), (x2, y2) in zip(points, points[1:]):
                steps = max(1, math.ceil(math.hypot(x2-x1, y2-y1)/2))
                for i in range(steps+1):
                    px, py = x1+(x2-x1)*i/steps, y1+(y2-y1)*i/steps
                    for kind, x, y, a, b, label in self.nodes:
                        if kind == "entity":
                            inside = x+.1 < px < x+a-.1 and y+.1 < py < y+b-.1
                        elif kind == "attribute":
                            inside = ((px-x)/a)**2 + ((py-y)/b)**2 < .999
                        else:
                            inside = abs(px-x)/a + abs(py-y)/b < .999
                        if inside:
                            raise ValueError(f"Connector {points} overlaps {label} at {px}, {py}")
        self.svg.append('</svg>')
        svg = ROOT / "docs/database/er-diagram-chen-patent-data.svg"
        svg.write_text('\n'.join(self.svg)+'\n', encoding="utf-8", newline="\n")
        self.pdf.save()
        print(f"Verified {len(self.nodes)} nodes and {len(self.paths)} connectors with no connector/node overlaps")
        print(svg)
        print(self.pdf_path)


def main():
    s = Sheet()
    s.text(90, 75, "Patent Intelligence Platform - ER Diagram, Sheet 1 of 2", size=34, bold=True, anchor="start")
    s.text(90, 115, "Patent knowledge, people, classifications, citations, and family relationships - Chen notation", size=20, anchor="start", color="#475569")
    e = lambda x,y,w,h,t: s.node("entity",x,y,w,h,t)
    a = lambda x,y,rx,t,key=False: s.node("attribute",x,y,rx,38,t,key)
    r = lambda x,y,t: s.node("relationship",x,y,105,65,t)
    p = s.path
    e(1050,900,600,150,"PATENT")
    for x,label,rx,key in [(1080,"title",90,False),(1350,"patent_id",105,True),(1620,"legal_status",110,False)]:
        a(x,650,rx,label,key); p((x,688),(x,900))
    for x,label,rx in [(1060,"abstract",100),(1350,"publication_year",125),(1640,"cited_by_count",120)]:
        a(x,1250,rx,label); p((x,1050),(x,1212))

    e(300,370,260,90,"DOMAIN")
    a(300,230,105,"domain_id",True); p((300,268),(365,370))
    a(580,230,80,"name"); p((580,268),(500,370))
    r(750,520,"BELONGS|TO")
    p((560,415),(600,415),(600,520),(645,520)); p((855,520),(900,520),(900,930),(1050,930))
    s.card(580,390,"1"); s.card(1005,915,"N")

    e(300,930,260,90,"ASSIGNEE")
    a(280,1150,115,"assignee_id",True); p((350,1020),(280,1020),(280,1112))
    a(580,1150,80,"name"); p((510,1020),(580,1020),(580,1112))
    r(750,975,"ASSIGNED|TO"); p((560,975),(645,975)); p((855,975),(1050,975))
    s.card(585,960,"N"); s.card(1005,960,"N")

    e(300,1550,260,90,"INVENTOR")
    a(280,1780,115,"inventor_id",True); p((350,1640),(280,1640),(280,1742))
    a(580,1780,80,"name"); p((510,1640),(580,1640),(580,1742))
    r(750,1500,"INVENTS")
    p((560,1595),(600,1595),(600,1500),(645,1500)); p((855,1500),(900,1500),(900,1020),(1050,1020))
    s.card(580,1570,"N"); s.card(1005,1005,"N")

    e(2180,370,300,90,"CPC CODE")
    a(2130,230,105,"cpc_code",True); p((2130,268),(2240,370))
    a(2500,230,90,"section"); p((2500,268),(2400,370))
    a(2580,600,125,"description"); p((2480,415),(2580,415),(2580,562))
    r(1950,520,"CLASSIFIED|AS")
    p((2180,415),(2100,415),(2100,520),(2055,520)); p((1845,520),(1800,520),(1800,930),(1650,930))
    s.card(2125,390,"N"); s.card(1675,915,"N")

    e(2180,930,320,90,"NPL REFERENCE")
    a(2080,1150,80,"npl_id",True); p((2220,1020),(2220,1080),(2080,1080),(2080,1112))
    a(2390,1150,90,"citation"); p((2390,1020),(2390,1112))
    a(2620,1150,125,"normalized_key"); p((2460,1020),(2460,1060),(2620,1060),(2620,1112))
    r(1950,975,"CITES"); p((1650,975),(1845,975)); p((2055,975),(2180,975))
    s.card(1675,960,"N"); s.card(2125,960,"N")

    e(2140,1550,400,90,"CITATION SNAPSHOT")
    a(2120,1780,110,"snapshot_id",True); p((2200,1640),(2200,1700),(2120,1700),(2120,1742))
    a(2490,1780,140,"cited_by_count"); p((2460,1640),(2460,1700),(2490,1700),(2490,1742))
    a(2300,1930,115,"observed_on"); p((2300,1640),(2300,1892))
    r(1950,1500,"HAS")
    p((1650,1020),(1800,1020),(1800,1500),(1845,1500)); p((2055,1500),(2100,1500),(2100,1595),(2140,1595))
    s.card(1675,1005,"1"); s.card(2105,1570,"N")

    r(1350,1840,"RELATED|TO")
    p((1200,1050),(1200,1840),(1245,1840)); p((1500,1050),(1500,1840),(1455,1840))
    s.card(1160,1660,"N"); s.card(1520,1660,"N")
    a(1730,1840,115,"relation_type"); p((1350,1905),(1350,1980),(1730,1980),(1730,1878))
    s.text(90,2050,"Underlined attributes are keys. N:N relationships use junction tables: patent_assignees, patent_inventors, patent_cpc_codes, patent_npl_references, and patent_families.",size=17,anchor="start",color="#475569")
    s.finish()


if __name__ == "__main__":
    main()
