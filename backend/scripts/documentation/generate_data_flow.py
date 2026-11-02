"""Render context, level-1, and level-2 DFDs of the implemented application.

Documentation-only dependency: reportlab. No database/API access. Uses the
horizontal-schema renderer's line-jump geometry for unconnected crossings.
"""
from __future__ import annotations

import html
import math
import copy
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A2, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from generate_horizontal_schema import commands

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs" / "diagrams"
PDF = ROOT / "output" / "pdf" / "patent-data-flow-diagram.pdf"
FONT, BOLD = "DFD", "DFDBold"
INK, MUTED, LINE = "#202b3b", "#596777", "#526274"


def measure(text, size, bold=False):
    return pdfmetrics.stringWidth(text, BOLD if bold else FONT, size)


@dataclass
class Node:
    key: str
    kind: str
    label: str
    lines: list[str]
    x: float
    y: float
    w: float
    h: float

    def port(self, side, offset=0.5):
        point = {"left": (self.x, self.y + self.h * offset),
                "right": (self.x + self.w, self.y + self.h * offset),
                "top": (self.x + self.w * offset, self.y),
                "bottom": (self.x + self.w * offset, self.y + self.h)}[side]
        return tuple(round(value, 6) for value in point)


class Sheet:
    def __init__(self, slug, title, subtitle, height=2100):
        self.slug, self.title, self.subtitle = slug, title, subtitle
        self.w, self.h = 1800, height
        self.nodes, self.flows, self.notes = {}, [], []

    def node(self, key, kind, label, lines, x, y, w=320, h=120):
        self.nodes[key] = Node(key, kind, label, lines, x, y, w, h)
        return self

    def flow(self, source, target, label, sx, tx, *, so=0.5, to=0.5, via=(), at=None, align="center"):
        start, end = self.nodes[source].port(sx, so), self.nodes[target].port(tx, to)
        self.flows.append({"source": source, "target": target, "label": label.split("\n"),
                           "points": [start, *via, end], "at": at, "align": align, "color": LINE})
        return self

    def note(self, x, y, width, lines):
        self.notes.append((x, y, width, lines))
        return self

    def verify(self):
        nodes = list(self.nodes.values())
        for index, node in enumerate(nodes):
            assert node.y >= 150 and node.x > 15 and node.x + node.w < self.w - 15
            assert node.y + node.h < self.h - 95
            for other in nodes[index + 1:]:
                assert not (max(node.x, other.x) < min(node.x + node.w, other.x + other.w) and
                            max(node.y, other.y) < min(node.y + node.h, other.y + other.h)), ("Overlapping nodes", node.key, other.key)
        for flow in self.flows:
            assert "process" in {self.nodes[flow["source"]].kind, self.nodes[flow["target"]].kind}, "DFD flows must pass through a process"
            assert flow["at"] is not None
            for a, b in zip(flow["points"], flow["points"][1:]):
                assert a[0] == b[0] or a[1] == b[1], ("Non-orthogonal segment", flow["source"], flow["target"], a, b)
                for node in nodes:
                    x, y, w, h = node.x, node.y, node.w, node.h
                    if node.kind == "process":
                        cx, cy, radius = x+w/2, y+h/2, w/2
                        dx, dy = b[0]-a[0], b[1]-a[1]
                        length = dx*dx+dy*dy
                        t = max(0, min(1, ((cx-a[0])*dx+(cy-a[1])*dy)/length)) if length else 0
                        assert math.hypot(a[0]+t*dx-cx, a[1]+t*dy-cy) >= radius-.001, ("Flow through process", flow["source"], flow["target"], node.key)
                        continue
                    horizontal = a[1] == b[1] and y < a[1] < y + h and max(min(a[0], b[0]), x) < min(max(a[0], b[0]), x + w)
                    vertical = a[0] == b[0] and x < a[0] < x + w and max(min(a[1], b[1]), y) < min(max(a[1], b[1]), y + h)
                    assert not (horizontal or vertical), ("Flow through node", flow["source"], flow["target"], node.key)
            # Arrow labels must not cover any entity, process, or store.
            lx, ly = flow["at"]
            for index, text in enumerate(flow["label"]):
                tw = measure(text, 14)
                x = lx - tw / 2 if flow["align"] == "center" else lx
                y = ly + index * 19 - 14
                for node in nodes:
                    assert not (max(x, node.x) < min(x + tw, node.x + node.w) and max(y, node.y) < min(y + 17, node.y + node.h)), ("Flow label covers node", text, node.key)
                top = ly + index * 19 - 11
                for other in self.flows:
                    for a, b in zip(other["points"], other["points"][1:]):
                        horizontal = a[1] == b[1] and top < a[1] < top + 13 and max(min(a[0], b[0]), x) < min(max(a[0], b[0]), x + tw)
                        vertical = a[0] == b[0] and x < a[0] < x + tw and max(min(a[1], b[1]), top) < min(max(a[1], b[1]), top + 13)
                        assert not (horizontal or vertical), ("Connector crosses flow label", text, other["source"], other["target"])


class Drawing:
    def __init__(self, sheet, pdf):
        self.sheet, self.pdf = sheet, pdf
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{sheet.w}" height="{sheet.h}" viewBox="0 0 {sheet.w} {sheet.h}" role="img">', f'<title>{html.escape(sheet.title)}</title>']
        size = landscape(A2) if sheet.h <= 1300 else A2
        pdf.setPageSize(size)
        pdf.saveState()
        factor = min(size[0] / sheet.w, size[1] / sheet.h)
        pdf.translate((size[0] - sheet.w * factor) / 2, (size[1] - sheet.h * factor) / 2)
        pdf.scale(factor, factor)
        self.rect(0, 0, sheet.w, sheet.h, "#ffffff")

    def text(self, x, y, text, size=16, bold=False, color=INK, align="center"):
        anchor = "middle" if align == "center" else "start"
        self.svg.append(f'<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" fill="{color}" text-anchor="{anchor}">{html.escape(text)}</text>')
        self.pdf.setFillColor(HexColor(color))
        self.pdf.setFont(BOLD if bold else FONT, size)
        left = x - measure(text, size, bold) / 2 if align == "center" else x
        self.pdf.drawString(left, self.sheet.h - y, text)

    def rect(self, x, y, w, h, fill, stroke=None, radius=0):
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke or "none"}" stroke-width="1.7"/>')
        self.pdf.setFillColor(HexColor(fill))
        self.pdf.setStrokeColor(HexColor(stroke or fill))
        self.pdf.setLineWidth(1.7)
        if radius:
            self.pdf.roundRect(x, self.sheet.h - y - h, w, h, radius, fill=1, stroke=bool(stroke))
        else:
            self.pdf.rect(x, self.sheet.h - y - h, w, h, fill=1, stroke=bool(stroke))

    def path(self, sequence, color=LINE, linewidth=1.9):
        path, svg = self.pdf.beginPath(), []
        for kind, *values in sequence:
            svg.append(kind + " " + " ".join(str(v) for v in values))
            if kind == "M":
                path.moveTo(values[0], self.sheet.h - values[1])
            elif kind == "L":
                path.lineTo(values[0], self.sheet.h - values[1])
            else:
                path.curveTo(values[0], self.sheet.h - values[1], values[2], self.sheet.h - values[3], values[4], self.sheet.h - values[5])
        self.svg.append(f'<path d="{" ".join(svg)}" fill="none" stroke="{color}" stroke-width="{linewidth}"/>')
        self.pdf.setStrokeColor(HexColor(color))
        self.pdf.setLineWidth(linewidth)
        self.pdf.drawPath(path, fill=0, stroke=1)

    def line(self, a, b):
        self.path([("M", *a), ("L", *b)], linewidth=1.3)

    def arrow(self, points):
        x, y = points[-1]
        previous = next(point for point in reversed(points[:-1]) if point != points[-1])
        angle = math.atan2(y - previous[1], x - previous[0])
        a = (x - 10 * math.cos(angle) + 4 * math.sin(angle), y - 10 * math.sin(angle) - 4 * math.cos(angle))
        b = (x - 10 * math.cos(angle) - 4 * math.sin(angle), y - 10 * math.sin(angle) + 4 * math.cos(angle))
        self.svg.append(f'<polygon points="{x},{y} {a[0]},{a[1]} {b[0]},{b[1]}" fill="{LINE}"/>')
        path = self.pdf.beginPath()
        path.moveTo(x, self.sheet.h - y)
        path.lineTo(a[0], self.sheet.h - a[1])
        path.lineTo(b[0], self.sheet.h - b[1])
        path.close()
        self.pdf.setFillColor(HexColor(LINE))
        self.pdf.drawPath(path, fill=1, stroke=0)

    def node(self, node):
        x, y, w, h = node.x, node.y, node.w, node.h
        if node.kind == "store":
            self.rect(x, y, w, h, "#ffffff")
            self.line((x, y), (x + w, y))
            self.line((x, y + h), (x + w, y + h))
            self.text(x + w/2, y + 25, f"{node.label} - {node.lines[0]}", 16, True)
            for i, label in enumerate(node.lines[1:]):
                self.text(x + w/2, y + 48 + i * 21, label, 15)
        elif node.kind == "process":
            self.svg.append(f'<circle cx="{x+w/2}" cy="{y+h/2}" r="{w/2}" fill="#ffffff" stroke="{INK}" stroke-width="1.7"/>')
            self.pdf.setFillColor(HexColor("#ffffff"))
            self.pdf.setStrokeColor(HexColor(INK))
            self.pdf.setLineWidth(1.7)
            self.pdf.circle(x+w/2, self.sheet.h-y-h/2, w/2, fill=1, stroke=1)
            lines = process_lines(node)
            for i, (label, bold) in enumerate(lines):
                baseline = y+h/2 + (i-(len(lines)-1)/2)*19 + 5
                assert measure(label, 15, bold) < 2*math.sqrt(max(0, (w/2-9)**2-(baseline-5-y-h/2)**2)), ("Process label does not fit circle", node.key, label)
                self.text(x+w/2, baseline, label, 15, bold)
        else:
            self.rect(x, y, w, h, "#ffffff", INK)
            self.text(x + w / 2, y + 28, node.label, 18, True)
            for i, label in enumerate(node.lines):
                self.text(x + w / 2, y + 67 + i * 23, label, 17)

    def draw(self, page_number):
        s = self.sheet
        self.text(60, 62, "PATENT INTELLIGENCE PLATFORM", 30, True, align="left")
        self.text(60, 105, s.title, 23, True, align="left")
        self.text(60, 136, s.subtitle, 15, color=MUTED, align="left")
        for flow in s.flows:
            self.path(commands(flow, s.flows))
            self.arrow(flow["points"])
        for node in s.nodes.values():
            self.node(node)
        for flow in s.flows:
            x, y = flow["at"]
            for i, label in enumerate(flow["label"]):
                self.text(x, y + i * 19, label, 14, color=MUTED, align=flow["align"])
        for x, y, width, lines in s.notes:
            self.rect(x, y, width, 24 * len(lines) + 30, "#f4f6f9", "#d4dbe4")
            for i, line in enumerate(lines):
                self.text(x + 17, y + 28 + i * 24, line, 14, color=MUTED, align="left")
        y = s.h - 67
        self.line((60, y - 20), (1740, y - 20))
        self.text(60, y + 3, "Yourdon-DeMarco: circle = process | rectangle = external entity | parallel lines = data store | arrow = data flow", 13, color=MUTED, align="left")
        self.text(60, y + 27, "Arrows name the data being transferred. Repeated IDs refer to the same entity/store. Line jumps are unconnected crossings.", 12.5, color=MUTED, align="left")
        self.text(1680, y + 27, f"{page_number} / 3", 13, color=MUTED)
        (OUT / f"data-flow-{s.slug}.svg").write_text("\n".join(self.svg) + "\n</svg>\n", encoding="utf-8", newline="\n")
        self.pdf.restoreState()
        self.pdf.showPage()


def context():
    s = Sheet("context", "Level 0 - System context", "System boundary includes the web application, analysis services and offline data preparation.", 1250)
    s.node("user", "external", "E1", ["Researcher / analyst"], 70, 400, 300, 145)
    s.node("system", "process", "0", ["Patent Intelligence", "Platform"], 710, 390, 380, 170)
    s.node("ai", "external", "E3", ["Gemini AI service"], 1410, 400, 300, 145)
    s.node("maintainer", "external", "E2", ["Data maintainer"], 710, 950, 380, 130)
    s.flow("user", "system", "Credentials, idea, settings,\ncase / graph / report requests", "right", "left", so=0.25, to=46.25/170, at=(540, 405))
    s.flow("system", "user", "Session status, ranked patents,\nassessments, guidance and history", "left", "right", so=118.75/170, to=0.75, at=(540, 548))
    s.flow("system", "ai", "Idea / evidence prompts", "right", "left", so=46.25/170, to=0.25, at=(1250, 420))
    s.flow("ai", "system", "Structured NLP, concept, scoring\nand explanation responses", "left", "right", so=0.75, to=118.75/170, at=(1250, 545))
    s.flow("maintainer", "system", "Patent exports and\npreparation settings", "top", "bottom", so=0.25, to=0.25, at=(640, 745))
    s.flow("system", "maintainer", "Import / projection counts\nand build status", "bottom", "top", so=0.75, to=0.75, at=(1190, 745))
    s.note(80, 940, 500, ["The researcher uses the React web interface.", "Gemini calls have local fallback paths.", "Internal stores appear on the next sheet."])
    return s


def system():
    s = Sheet("system", "Level 1 - Application processes and data stores", "MySQL is authoritative. Neo4j and FAISS are derived projections; the embedding cache contains public patent vectors only.", 2100)
    s.node("u1", "external", "E1", ["Researcher / analyst"], 70, 200, 280, 110)
    s.node("auth", "process", "1.0", ["Authenticate user"], 660, 200, 320, 110)
    s.node("accounts", "store", "D1", ["Accounts and sessions", "MySQL: users, roles, sessions", "and authentication throttles"], 1340, 200, 360, 110)
    s.node("u2", "external", "E1 (repeat)", ["Researcher / analyst"], 70, 530, 280, 110)
    s.node("research", "process", "2.0", ["Handle research requests"], 660, 530, 320, 110)
    s.node("saved", "store", "D2", ["Private saved research", "MySQL: cases, runs, results,", "evaluations, improvements"], 1340, 530, 360, 110)
    s.node("ai", "external", "E3", ["Gemini AI service"], 70, 950, 280, 130)
    s.node("analysis", "process", "3.0", ["Analyze and explore", "patent information"], 660, 950, 320, 130)
    s.node("catalog", "store", "D3", ["Public patent catalog", "MySQL: normalized patent facts"], 1190, 810, 440, 90)
    s.node("index", "store", "D4", ["Semantic index", "FAISS vectors and ID mapping"], 1190, 970, 440, 90)
    s.node("graph", "store", "D5", ["Patent knowledge graph", "Neo4j: family, CPC, citation links"], 1190, 1130, 440, 90)
    s.node("cache", "store", "D6", ["Public embedding cache", "Memory LRU + local SQLite"], 1190, 1290, 440, 90)
    s.node("maintainer", "external", "E2", ["Data maintainer"], 70, 1670, 280, 130)
    s.node("prepare", "process", "4.0", ["Prepare patent corpus", "and derived artifacts"], 660, 1670, 320, 130)
    s.node("catalog2", "store", "D3", ["Public patent catalog (repeat)", "MySQL: canonical publications"], 1340, 1540, 360, 100)
    s.node("index2", "store", "D4", ["Semantic index (repeat)", "FAISS vectors and ID mapping"], 1340, 1710, 360, 100)
    s.node("graph2", "store", "D5", ["Patent knowledge graph (repeat)", "Neo4j projection"], 1340, 1880, 360, 100)
    s.flow("u1", "auth", "Credentials / session proof", "right", "left", so=35/110, to=35/110, at=(505, 220))
    s.flow("auth", "u1", "Cookie, CSRF token, auth status", "left", "right", so=80/110, to=80/110, at=(505, 303))
    s.flow("accounts", "auth", "Account / session records", "left", "right", so=35/110, to=35/110, at=(1160, 220))
    s.flow("auth", "accounts", "Password hashes, sessions, throttles", "right", "left", so=80/110, to=80/110, at=(1160, 303))
    s.flow("auth", "research", "Authenticated principal", "bottom", "top", at=(955, 420))
    s.flow("u2", "research", "Idea, settings, case / run IDs,\ngraph / report requests", "right", "left", so=35/110, to=35/110, at=(505, 530))
    s.flow("research", "u2", "Results, saving status, history,\ngraph slices and report rows", "left", "right", so=80/110, to=80/110, at=(505, 642))
    s.flow("saved", "research", "Owner-filtered case / run snapshots", "left", "right", so=35/110, to=35/110, at=(1160, 548))
    s.flow("research", "saved", "Case changes and analysis payloads", "right", "left", so=80/110, to=80/110, at=(1160, 638))
    s.flow("research", "analysis", "Authorized idea, settings\nand owned snapshots", "bottom", "top", so=0.25, to=0.25, at=(590, 788))
    s.flow("analysis", "research", "Ranked hits, assessments, guidance,\npublic views and timings", "top", "bottom", so=0.75, to=0.75, at=(1120, 788))
    s.flow("analysis", "ai", "NLP / scoring / explanation prompts", "left", "right", so=40/130, to=40/130, at=(505, 975))
    s.flow("ai", "analysis", "Structured AI responses", "right", "left", so=90/130, to=90/130, at=(505, 1066))
    s.flow("catalog", "analysis", "Catalog facts", "left", "right", to=30/130, via=[(1080,855),(1080,980)], at=(1028, 910))
    s.flow("index", "analysis", "Nearest vectors / IDs", "left", "right", to=0.5, at=(1085, 1000))
    s.flow("graph", "analysis", "Graph relationships", "left", "right", to=100/130, via=[(1050,1175),(1050,1050)], at=(1115,1158))
    s.flow("cache", "analysis", "Cached vectors", "left", "bottom", so=1/3, to=0.5625, via=[(1010,1320),(1010,1120),(840,1120)], at=(1120,1302))
    s.flow("analysis", "cache", "New public vectors", "bottom", "left", so=0.8125, to=7/9, via=[(920,1100),(1040,1100),(1040,1360)], at=(1095,1400))
    s.note(70, 1210, 860, ["Process 3.0 groups retrieval, evaluation, improvements and public graph/report reads.", "Evaluation and improvement are separate requests, not mandatory pipeline steps.", "Process 2.0 persists their output and restores existing runs without recomputing.", "Session and case ownership are checked on every protected request."])
    s.flow("maintainer", "prepare", "Patent export files and settings", "right", "left", so=35/130, to=35/130, at=(505,1690))
    s.flow("prepare", "maintainer", "Import / build status and counts", "left", "right", so=95/130, to=95/130, at=(505,1790))
    s.flow("prepare", "catalog2", "Normalized records", "right", "left", so=30/130, to=0.4, via=[(1120,1700),(1120,1580)], at=(1230,1562))
    s.flow("catalog2", "prepare", "Canonical corpus", "left", "right", so=0.7, to=70/130, via=[(1080,1610),(1080,1740)], at=(1230,1630))
    s.flow("prepare", "index2", "FAISS vectors + ID mapping", "right", "left", so=95/130, to=0.55, at=(1160,1793))
    s.flow("prepare", "graph2", "Graph projection", "bottom", "left", via=[(820,1930)], at=(1120,1910))
    return s


def analysis():
    s = Sheet("analysis", "Level 2 - Decomposition of process 3.0", "Request-driven data transformations: retrieval, graph ranking, optional assessment/guidance, and read-only public exploration.", 2450)
    s.node("manager", "process", "2.0 (outside this scope)", ["Handle research requests", "Validated / owner-scoped input"], 60, 1690, 360, 150)
    s.node("nlp", "process", "3.1", ["Preprocess idea", "Gemini / spaCy fallback"], 620, 170, 360, 130)
    s.node("g1", "external", "E3", ["Gemini AI service"], 1330, 170, 360, 130)
    s.node("retrieve", "process", "3.2", ["Encode query and retrieve", "PatentSBERTa + FAISS"], 620, 520, 360, 130)
    s.node("catalog", "store", "D3", ["Public patent catalog", "Canonical metadata lookup"], 60, 520, 360, 110)
    s.node("index", "store", "D4", ["Semantic index", "FAISS + ID mapping"], 1330, 520, 360, 110)
    s.node("rank", "process", "3.3", ["Expand and rerank patents", "Neo4j + live GraphSAGE", "Group identical result text"], 620, 870, 360, 150)
    s.node("cache", "store", "D6", ["Public embedding cache", "Memory LRU + SQLite"], 60, 875, 360, 110)
    s.node("graph", "store", "D5", ["Patent knowledge graph", "Family / CPC / citation links"], 1330, 875, 360, 110)
    s.node("evaluate", "process", "3.4", ["Evaluate patentability", "Concept search + scoring"], 620, 1230, 360, 140)
    s.node("index2", "store", "D4", ["Semantic index (repeat)", "Per-concept search"], 60, 1220, 360, 100)
    s.node("graph2", "store", "D5", ["Patent graph (repeat)", "Concept CPC / graph signals"], 1330, 1220, 360, 100)
    s.node("g2", "external", "E3 (repeat)", ["Gemini AI service"], 1330, 1430, 360, 110)
    s.node("improve", "process", "3.5", ["Generate improvements", "Diagnosis, strategies, guidance"], 620, 1690, 360, 150)
    s.node("g3", "external", "E3 (repeat)", ["Gemini AI service"], 1330, 1690, 360, 150)
    s.node("views", "process", "3.6", ["Read public graph / reports", "Graph slices and SQL summaries"], 620, 2070, 360, 130)
    s.node("catalog2", "store", "D3", ["Public catalog (repeat)", "Patent report views"], 1330, 2000, 360, 100)
    s.node("graph3", "store", "D5", ["Patent graph (repeat)", "Read-only graph slices"], 1330, 2180, 360, 100)
    s.flow("manager", "nlp", "Authorized idea + settings", "left", "left", so=40/150, to=60/130, via=[(30,1730),(30,230)], at=(330,210))
    s.flow("nlp", "g1", "Idea-processing prompt", "right", "left", so=40/130, to=40/130, at=(1155,190))
    s.flow("g1", "nlp", "Structured NLP output", "left", "right", so=95/130, to=95/130, at=(1155,286))
    s.flow("nlp", "retrieve", "Original idea, cleaned query,\nkeywords and settings", "bottom", "top", at=(1030,405))
    s.flow("catalog", "retrieve", "Patent metadata", "right", "left", to=55/130, at=(520,555))
    s.flow("index", "retrieve", "Nearest vectors / patent IDs", "left", "right", to=55/130, at=(1155,555))
    s.flow("retrieve", "rank", "Query vector, seed hits\nand canonical metadata", "bottom", "top", at=(1030,780))
    s.flow("graph", "rank", "Family / CPC neighbours\nand subgraph edges", "left", "right", to=60/150, at=(1155,900))
    s.flow("cache", "rank", "Cached vectors", "right", "left", so=45/110, to=50/150, at=(520,900))
    s.flow("rank", "cache", "New public vectors", "left", "right", so=105/150, to=100/110, at=(520,955))
    s.flow("rank", "manager", "Ranked patent results", "left", "right", so=130/150, to=50/150, via=[(465,1000),(465,1740)], at=(540,1045))
    s.flow("rank", "evaluate", "Idea + ranked hits\n(evaluation input)", "bottom", "top", at=(1020,1135))
    s.flow("manager", "evaluate", "Saved idea + hits", "right", "left", so=30/150, to=70/140, via=[(440,1720),(440,1300)], at=(540,1288))
    s.flow("index2", "evaluate", "Per-concept matches", "right", "left", to=40/140, at=(535,1250))
    s.flow("graph2", "evaluate", "Concept CPC / graph evidence", "left", "right", so=0.4, to=30/140, at=(1155,1240))
    s.flow("evaluate", "g2", "Concept / scoring prompts", "right", "left", so=40/140, to=20/110, via=[(1100,1270),(1100,1450)], at=(1200,1410))
    s.flow("g2", "evaluate", "AI concept / scoring responses", "left", "right", so=70/110, to=100/140, via=[(1050,1500),(1050,1330)], at=(1150,1565))
    s.flow("evaluate", "manager", "Scores, risk and verdict", "left", "right", so=100/140, to=90/150, via=[(500,1330),(500,1780)], at=(620,1390))
    s.flow("evaluate", "improve", "Idea, ranked hits\nand assessment", "bottom", "top", at=(835,1565), align="left")
    s.flow("manager", "improve", "Owned idea, hits\nand assessment", "right", "left", so=70/150, to=70/150, at=(558,1715))
    s.flow("improve", "g3", "Diagnosis / strategy prompt", "right", "left", so=40/150, to=40/150, at=(1155,1710))
    s.flow("g3", "improve", "Generated explanation", "left", "right", so=105/150, to=105/150, at=(1155,1820))
    s.flow("improve", "manager", "Improvement guidance", "left", "right", so=110/150, to=110/150, at=(520,1830))
    s.flow("manager", "views", "Public graph / report parameters", "bottom", "left", via=[(240,2135)], at=(410,2115))
    s.flow("views", "manager", "Graph / report rows", "left", "bottom", so=110/130, to=80/360, via=[(140,2180)], at=(410,2205))
    s.flow("catalog2", "views", "Public patent summaries", "left", "right", to=30/130, via=[(1120,2050),(1120,2100)], at=(1160,2032))
    s.flow("graph3", "views", "Graph slice records", "left", "right", to=90/130, via=[(1090,2230),(1090,2160)], at=(1160,2255))
    s.note(60, 320, 480, ["This sheet expands 3.0, not process 2.0.", "Process 2.0 receives and saves each response.", "Evaluations and improvements are on demand.", "Saved inputs can bypass retrieval stages.", "Private query vectors are never cached in D6."])
    return s


def process_lines(node):
    """Wrap the identifier and name to the readable centre of a process bubble."""
    result = []
    for label, bold in [(node.label, True), *[(line, False) for line in node.lines]]:
        current = ""
        for word in label.split():
            candidate = f"{current} {word}".strip()
            if current and measure(candidate, 15, bold) > node.w*.74:
                result.append((current, bold))
                current = word
            else:
                current = candidate
        if current:
            result.append((current, bold))
    return result


def yourdon_demarco(sheet):
    """Replace logical process slots with circles; reconnect at their boundaries.

    Retain the original flow topology, labels and routing lanes. Only terminal
    segments change to meet the circular outline instead of a rectangular slot.
    """
    original = copy.deepcopy(sheet.nodes)
    for node in sheet.nodes.values():
        if node.kind == "process":
            diameter = max(160, node.h+40)
            node.x += (node.w-diameter)/2
            node.y += (node.h-diameter)/2
            node.w = node.h = diameter

    def terminal(key, point):
        before, after = original[key], sheet.nodes[key]
        if after.kind != "process":
            return point
        px, py = point
        cx, cy, radius = after.x+after.w/2, after.y+after.h/2, after.w/2
        if abs(px-before.x) < .001 or abs(px-before.x-before.w) < .001:
            side = -1 if abs(px-before.x) < .001 else 1
            return (cx + side*math.sqrt(max(0, radius**2-(py-cy)**2)), py)
        nx = cx + (px-before.x-before.w/2)*after.w/before.w
        side = -1 if abs(py-before.y) < .001 else 1
        return (nx, cy+side*math.sqrt(max(0, radius**2-(nx-cx)**2)))

    for flow in sheet.flows:
        old = flow["points"]
        start = terminal(flow["source"], old[0])
        end = terminal(flow["target"], old[-1])
        if len(old) == 2:
            if old[0][0] == old[-1][0] and abs(start[0]-end[0]) > .001:
                middle_y = (start[1]+end[1])/2
                points = [start, (start[0], middle_y), (end[0], middle_y), end]
            else:
                points = [start, end]
        else:
            points = [start, *old[1:-1], end]
            if old[0][0] == old[1][0]:
                points[1] = (start[0], points[1][1])
            if old[-2][0] == old[-1][0]:
                points[-2] = (end[0], points[-2][1])
        flow["points"] = [point for i, point in enumerate(points) if i == 0 or point != points[i-1]]
    return sheet


def drawio_model(sheet):
    """Native editable geometry; draw.io routes the attached directional edges."""
    model = ET.Element("mxGraphModel", adaptiveColors="auto", grid="1", gridSize="10",
                       page="1", pageScale="1", pageWidth=str(sheet.w), pageHeight=str(sheet.h))
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")

    def vertex(key, value, style, x, y, w, h):
        cell = ET.SubElement(root, "mxCell", id=key, value=value,
                             style=style+"html=1;fontFamily=Arial;", vertex="1", parent="1")
        ET.SubElement(cell, "mxGeometry", x=str(x), y=str(y), width=str(w), height=str(h), **{"as":"geometry"})

    vertex("title", html.escape(sheet.title)+"<br><small>Yourdon-DeMarco notation</small>",
           "text;strokeColor=none;fillColor=none;align=left;fontSize=24;fontStyle=1;", 60, 35, 1500, 70)
    common = f"whiteSpace=wrap;strokeColor={INK};strokeWidth=1.7;fillColor=#ffffff;fontColor={INK};"
    for node in sheet.nodes.values():
        if node.kind == "process":
            value = '<br>'.join((f'<b>{html.escape(line)}</b>' if bold else html.escape(line)) for line,bold in process_lines(node))
            style = "ellipse;aspect=fixed;perimeter=ellipsePerimeter;fontSize=15;spacing=4;"
        elif node.kind == "store":
            value = f'<b>{node.label} - {html.escape(node.lines[0])}</b><br>'+'<br>'.join(html.escape(line) for line in node.lines[1:])
            style = "shape=partialRectangle;left=0;right=0;top=1;bottom=1;fontSize=15;spacing=6;"
        else:
            value = f'<b>{html.escape(node.label)}</b><br>'+'<br>'.join(html.escape(line) for line in node.lines)
            style = "rounded=0;fontSize=17;spacing=6;"
        vertex(node.key, value, style+common, node.x, node.y, node.w, node.h)

    for index, flow in enumerate(sheet.flows):
        source, target = sheet.nodes[flow["source"]], sheet.nodes[flow["target"]]
        start, end = flow["points"][0], flow["points"][-1]
        sx, sy = (start[0]-source.x)/source.w, (start[1]-source.y)/source.h
        tx, ty = (end[0]-target.x)/target.w, (end[1]-target.y)/target.h
        style = (f"edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=classic;startArrow=none;"
                 f"strokeColor={LINE};strokeWidth=1.9;fontSize=14;fontColor={MUTED};"
                 f"exitX={sx};exitY={sy};exitPerimeter=0;entryX={tx};entryY={ty};entryPerimeter=0;"
                 "jumpStyle=arc;jumpSize=8;labelBackgroundColor=default;defaultLabelBackgroundColor=page;")
        edge = ET.SubElement(root, "mxCell", id=f"flow-{index}", parent="1", edge="1",
                             source=source.key, target=target.key, style=style,
                             value='<br>'.join(html.escape(label) for label in flow["label"]))
        ET.SubElement(edge, "mxGeometry", relative="1", **{"as":"geometry"})
    for index, (x,y,w,lines) in enumerate(sheet.notes):
        vertex(f"note-{index}", '<br>'.join(html.escape(line) for line in lines),
               "text;strokeColor=#d4dbe4;fillColor=#f4f6f9;align=left;spacing=12;fontSize=14;", x,y,w,24*len(lines)+30)
    vertex("legend", "Circle: process | Rectangle: external entity | Parallel lines: data store | Arrows: data flows",
           "text;strokeColor=none;fillColor=none;align=left;fontSize=14;",60,sheet.h-65,1650,40)
    return model


def export_drawio(sheets):
    document = ET.Element("mxfile", host="app.diagrams.net", type="device")
    for sheet in sheets:
        model = drawio_model(sheet)
        page = ET.SubElement(document, "diagram", id=f"dfd-{sheet.slug}", name=sheet.title)
        page.append(model)
    ET.indent(document, space="  ")
    with (OUT/"patent-data-flow.drawio").open("w", encoding="utf-8", newline="\n") as output:
        output.write(ET.tostring(document, encoding="unicode"))
        output.write("\n")


def main():
    fonts = Path("C:/Windows/Fonts")
    if (fonts / "arial.ttf").exists():
        pdfmetrics.registerFont(TTFont(FONT, str(fonts / "arial.ttf")))
        pdfmetrics.registerFont(TTFont(BOLD, str(fonts / "arialbd.ttf")))
    else:
        from reportlab.pdfbase.pdfmetrics import Font
        pdfmetrics.registerFont(Font(FONT, "Helvetica", "WinAnsiEncoding"))
        pdfmetrics.registerFont(Font(BOLD, "Helvetica-Bold", "WinAnsiEncoding"))
    sheets = [yourdon_demarco(sheet) for sheet in [context(), system(), analysis()]]
    for sheet in sheets:
        sheet.verify()
    OUT.mkdir(parents=True, exist_ok=True)
    PDF.parent.mkdir(parents=True, exist_ok=True)
    export_drawio(sheets)
    target = canvas.Canvas(str(PDF), pageCompression=1)
    target.setTitle("Patent Intelligence Platform - Data Flow Diagram")
    target.setAuthor("Patent Intelligence Platform")
    target.setSubject("Context, application decomposition, and analysis data flow based on current code")
    for index, sheet in enumerate(sheets, 1):
        Drawing(sheet, target).draw(index)
    target.save()
    print(f"Created {len(sheets)} DFD sheets, {sum(len(s.flows) for s in sheets)} labelled data flows.")
    print("Validated process-mediated flows, arrow endpoints, label clearance, and node/connector overlap.")
    print(PDF)


if __name__ == "__main__":
    main()
