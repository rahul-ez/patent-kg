"""One relation per horizontal row, with numbered FK-to-PK routing lanes.

Generates a single-page poster PDF and editable SVG from the SQL schema.
Documentation-only dependency: reportlab. No live database access is needed.
"""
from __future__ import annotations

import html
from collections import defaultdict
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A0
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from generate_relational_model import read_schema

ROOT = Path(__file__).resolve().parents[3]
W, H = 2600, 4000
LEFT, FIRST_Y, STEP, CELL_H = 460, 220, 154, 36
FONT, BOLD = "HorizontalSchema", "HorizontalSchemaBold"
SIZE = 14
COLORS = {"patents": "#426985", "catalog": "#80618b", "accounts": "#3c7965", "analysis": "#9a7943"}


def register_fonts():
    directory = Path("C:/Windows/Fonts")
    if (directory / "arial.ttf").exists():
        pdfmetrics.registerFont(TTFont(FONT, str(directory / "arial.ttf")))
        pdfmetrics.registerFont(TTFont(BOLD, str(directory / "arialbd.ttf")))
    else:
        from reportlab.pdfbase.pdfmetrics import Font
        pdfmetrics.registerFont(Font(FONT, "Helvetica", "WinAnsiEncoding"))
        pdfmetrics.registerFont(Font(BOLD, "Helvetica-Bold", "WinAnsiEncoding"))


def width(text, size=SIZE, bold=False):
    return pdfmetrics.stringWidth(text, BOLD if bold else FONT, size)


def group(parent):
    if parent == "patents":
        return "patents"
    if parent in {"app_users", "roles"}:
        return "accounts"
    if parent in {"analysis_cases", "analysis_runs"}:
        return "analysis"
    return "catalog"


def layout(tables):
    rows = {}
    for index, (name, table) in enumerate(tables.items()):
        heading = FIRST_Y + STEP * index
        x, cells = LEFT, {}
        for column in table.columns:
            key = column["name"]
            primary = key in table.primary
            minimum = 220 if name == "patents" and key == "patent_id" else 150 if key == table.primary[0] else 100
            cell_w = max(minimum, width(key, bold=primary) + 28)
            cells[key] = (x, heading + 30, cell_w, CELL_H)
            x += cell_w
        assert x < 2180, ("Row intrudes into reference lanes", name, x)
        rows[name] = {"title_y": heading, "end": x, "cells": cells}
    return rows


def routes(tables, rows):
    incoming, outgoing = defaultdict(list), defaultdict(list)
    edges = []
    sides = defaultdict(int)
    for child, table in tables.items():
        for column, parent, key in table.foreign:
            family = group(parent)
            side = "left" if family in {"patents", "catalog"} else "right"
            lane = 85 + 15 * sides[side] if side == "left" else 2240 + 23 * sides[side]
            sides[side] += 1
            edge = {"id": len(edges) + 1, "child": child, "column": column,
                    "parent": parent, "key": key, "side": side, "lane": lane,
                    "color": COLORS[family]}
            edges.append(edge)
            incoming[parent, key].append(edge)
            outgoing[child].append(edge)

    for (parent, key), references in incoming.items():
        x, y, w, h = rows[parent]["cells"][key]
        # Separate the actual destination-column ports, rather than stopping
        # references at a table title or merging unrelated arrows into a bus.
        for index, edge in enumerate(references):
            edge["end"] = (x + w * (index + 1) / (len(references) + 1), y + h)
            edge["target_y"] = y + h + 26 + index * 5
    for child, references in outgoing.items():
        for side in ("left", "right"):
            peers = [edge for edge in references if edge["side"] == side]
            peers.sort(key=lambda edge: rows[child]["cells"][edge["column"]][0], reverse=side == "left")
            for index, edge in enumerate(peers):
                x, y, w, _ = rows[child]["cells"][edge["column"]]
                edge["start"] = (x + w / 2, y)
                edge["source_y"] = rows[child]["title_y"] + 12 + index * 6
    for edge in edges:
        sx, sy = edge["start"]
        tx, ty = edge["end"]
        edge["points"] = [(sx, sy), (sx, edge["source_y"]),
                          (edge["lane"], edge["source_y"]),
                          (edge["lane"], edge["target_y"]),
                          (tx, edge["target_y"]), (tx, ty)]
    return edges


def verify(tables, rows, edges):
    assert len(rows) == len(tables)
    assert max(row["title_y"] + 30 + CELL_H for row in rows.values()) < H - 260, "Rows intrude into poster footer"
    expected = {(child, col, parent, key) for child, table in tables.items() for col, parent, key in table.foreign}
    actual = {(edge["child"], edge["column"], edge["parent"], edge["key"]) for edge in edges}
    assert expected == actual
    assert len({edge["lane"] for edge in edges}) == len(edges)
    for edge in edges:
        for a, b in zip(edge["points"], edge["points"][1:]):
            for name, row in rows.items():
                top = row["title_y"] + 30
                # No connector can pass through an attribute bar or table name.
                for x, y, w, h in ((LEFT, top, row["end"] - LEFT, CELL_H),
                                   (LEFT, row["title_y"] - 20, width(name.upper(), 20, True), 21)):
                    horizontal = a[1] == b[1] and y < a[1] < y + h and max(min(a[0], b[0]), x) < min(max(a[0], b[0]), x + w)
                    vertical = a[0] == b[0] and x < a[0] < x + w and max(min(a[1], b[1]), y) < min(max(a[1], b[1]), y + h)
                    assert not (horizontal or vertical), ("Connector intersects label/bar", edge["id"], name)
        assert edge["points"][0] == edge["start"] and edge["points"][-1] == edge["end"]


def commands(edge, edges):
    """Continuous paths with small jumps at crossings; crossings are not joins."""
    result = [("M", *edge["points"][0])]
    for a, b in zip(edge["points"], edge["points"][1:]):
        if a[1] == b[1]:
            crossings = set()
            lo, hi = sorted((a[0], b[0]))
            for other in edges:
                if other is edge:
                    continue
                for c, d in zip(other["points"], other["points"][1:]):
                    if c[0] == d[0] and lo + 5 < c[0] < hi - 5 and min(c[1], d[1]) < a[1] < max(c[1], d[1]):
                        crossings.add(c[0])
            direction = 1 if b[0] > a[0] else -1
            for cross in sorted(crossings, reverse=direction < 0):
                start, end = cross - direction * 3.2, cross + direction * 3.2
                result.append(("L", start, a[1]))
                result.append(("C", start, a[1] - 4.8, end, a[1] - 4.8, end, a[1]))
        result.append(("L", *b))
    return result


class Drawing:
    def __init__(self, filename):
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img">',
                    '<title>Patent Intelligence Platform - Horizontal Relational Schema</title>',
                    '<desc>All 23 relations appear once as horizontal attribute rows. Underlines indicate primary keys; numbered arrows connect foreign-key columns to actual referenced primary-key columns.</desc>']
        self.pdf = canvas.Canvas(str(filename), pagesize=A0, pageCompression=1)
        self.pdf.setTitle("Patent Intelligence Platform - Horizontal Relational Schema")
        self.pdf.setAuthor("Patent Intelligence Platform")
        self.pdf.setSubject("ER-to-relational mapping, one horizontal attribute row per relation")
        page_w, page_h = A0
        scale = min(page_w / W, page_h / H)
        self.pdf.translate((page_w - W * scale) / 2, (page_h - H * scale) / 2)
        self.pdf.scale(scale, scale)
        self.rect(0, 0, W, H, "#ffffff")

    def text(self, x, y, label, size=14, bold=False, color="#171717", center=False, underline=False):
        anchor = "middle" if center else "start"
        self.svg.append(f'<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}" text-anchor="{anchor}"' + (' text-decoration="underline"' if underline else '') + f'>{html.escape(label)}</text>')
        self.pdf.setFillColor(HexColor(color))
        self.pdf.setFont(BOLD if bold else FONT, size)
        left = x - width(label, size, bold) / 2 if center else x
        self.pdf.drawString(left, H - y, label)
        if underline:
            self.pdf.setStrokeColor(HexColor(color))
            self.pdf.setLineWidth(0.6)
            self.pdf.line(left, H - y - 1.8, left + width(label, size, bold), H - y - 1.8)

    def rect(self, x, y, w, h, fill, stroke=None):
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke or "none"}" stroke-width="0.9"/>')
        self.pdf.setFillColor(HexColor(fill))
        self.pdf.setStrokeColor(HexColor(stroke or fill))
        self.pdf.setLineWidth(0.9)
        self.pdf.rect(x, H - y - h, w, h, fill=1, stroke=bool(stroke))

    def path(self, sequence, color):
        parts = []
        path = self.pdf.beginPath()
        for command in sequence:
            kind, *coords = command
            parts.append(kind + " " + " ".join(str(number) for number in coords))
            if kind == "M":
                path.moveTo(coords[0], H - coords[1])
            elif kind == "L":
                path.lineTo(coords[0], H - coords[1])
            else:
                path.curveTo(coords[0], H - coords[1], coords[2], H - coords[3], coords[4], H - coords[5])
        self.svg.append(f'<path d="{" ".join(parts)}" stroke="{color}" stroke-width="1.25" fill="none"/>')
        self.pdf.setStrokeColor(HexColor(color))
        self.pdf.setLineWidth(1.25)
        self.pdf.drawPath(path, fill=0, stroke=1)

    def arrow(self, x, y, color):
        # Every destination is the bottom of a referenced PK column.
        points = [(x, y), (x - 3.5, y + 7), (x + 3.5, y + 7)]
        self.svg.append(f'<polygon points="{" ".join(f"{a},{b}" for a, b in points)}" fill="{color}"/>')
        self.pdf.setFillColor(HexColor(color))
        path = self.pdf.beginPath()
        path.moveTo(x, H - y)
        for a, b in points[1:]:
            path.lineTo(a, H - b)
        path.close()
        self.pdf.drawPath(path, fill=1, stroke=0)

    def save(self, svg):
        self.svg.append("</svg>")
        svg.write_text("\n".join(self.svg) + "\n", encoding="utf-8", newline="\n")
        self.pdf.showPage()
        self.pdf.save()


def main():
    register_fonts()
    tables = read_schema()
    rows = layout(tables)
    edges = routes(tables, rows)
    verify(tables, rows, edges)
    pdf = ROOT / "output" / "pdf" / "patent-relational-schema-horizontal.pdf"
    svg = ROOT / "docs" / "database" / "relational-schema-horizontal.svg"
    pdf.parent.mkdir(parents=True, exist_ok=True)
    drawing = Drawing(pdf)
    drawing.text(W / 2, 64, "PATENT INTELLIGENCE PLATFORM RELATIONAL SCHEMA", 31, bold=True, center=True)
    drawing.text(W / 2, 103, "Each table appears once. Underlined attributes form the primary key. Arrows point from FK columns to their referenced PK columns.", 14, center=True)
    drawing.text(W / 2, 133, "Matching small numbers identify the two ends of each continuous arrow. Small jumps indicate crossings, not connections.", 14, center=True)

    for edge in edges:
        drawing.path(commands(edge, edges), edge["color"])
        drawing.arrow(*edge["end"], edge["color"])
    for name, table in tables.items():
        row = rows[name]
        drawing.text(LEFT, row["title_y"], name.upper(), 20, bold=True)
        for column in table.columns:
            key = column["name"]
            x, y, w, h = row["cells"][key]
            drawing.rect(x, y, w, h, "#fafafa", "#70757d")
            drawing.text(x + w / 2, y + 23, key, center=True, underline=key in table.primary)
        if not table.foreign and name == "auth_rate_limits":
            drawing.text(row["end"] + 25, row["title_y"] + 53, "Independent throttle counters; no foreign keys.", 12, color="#60656d")
    for edge in edges:
        sx, sy = edge["start"]
        tx, ty = edge["end"]
        drawing.text(sx + 5, sy - 3, str(edge["id"]), 9, color=edge["color"])
        drawing.text(tx + 5, ty + 15, str(edge["id"]), 9, color=edge["color"])

    drawing.text(W / 2, 3830, "Blue: patent references  |  Purple: catalog references  |  Green: account/role references  |  Ochre: analysis references", 14, center=True)
    drawing.text(W / 2, 3865, f"{len(tables)} tables, {sum(len(table.columns) for table in tables.values())} attributes, {len(edges)} foreign keys. Every arrow is continuous between actual columns; number tags are not attributes.", 14, center=True)
    drawing.text(W / 2, 3900, "All underlined attributes in a relation together form its primary key. Source: database/sql/01_schema.sql and 05_auth.sql.", 13, center=True)
    drawing.save(svg)
    print(f"Validated all {len(edges)} FK endpoints and {sum(len(table.columns) for table in tables.values())} attributes; no connectors through table names or attribute bars.")
    print(f"PDF: {pdf}")
    print(f"SVG: {svg}")


if __name__ == "__main__":
    main()
