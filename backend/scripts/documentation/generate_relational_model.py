"""Generate a two-sheet relational mapping directly from the implemented SQL.

Documentation-only dependency: reportlab. Does not connect to any database.
Run from any directory: python backend/scripts/documentation/generate_relational_model.py
"""
from __future__ import annotations

import html
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A2, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[3]
DOCS = ROOT / "docs" / "database"
PDF = ROOT / "output" / "pdf" / "patent-relational-model.pdf"
W, H = 1800, 1273
HEADER, COLUMNS, ROW = 36, 23, 22
INK, MUTED, BLUE, GREEN = "#17243b", "#526277", "#3064a8", "#23836e"


@dataclass
class Table:
    columns: list[dict] = field(default_factory=list)
    primary: list[str] = field(default_factory=list)
    unique: list[list[str]] = field(default_factory=list)
    foreign: list[tuple[str, str, str]] = field(default_factory=list)


def read_schema():
    tables = {}
    for filename in ("01_schema.sql", "05_auth.sql"):
        sql = (ROOT / "database" / "sql" / filename).read_text(encoding="utf-8")
        for name, body in re.findall(r"CREATE TABLE(?: IF NOT EXISTS)? (\w+)\s*\((.*?)\)\s*ENGINE=InnoDB;", sql, re.S):
            table = Table()
            for line in body.splitlines():
                match = re.match(r"\s*(\w+)\s+((?:INT|BIGINT|SMALLINT|TINYINT|DOUBLE|CHAR|VARCHAR|TEXT|JSON|BOOLEAN|DATETIME|TIMESTAMP|ENUM)(?:\([^)]*\))?(?: UNSIGNED)?)(.*)", line)
                if match is None:
                    declaration = re.match(r"\s*(\w+)\s+\w+", line)
                    if declaration and declaration[1] not in {"PRIMARY", "UNIQUE", "FOREIGN", "CONSTRAINT", "INDEX"}:
                        raise ValueError(f"Unsupported column definition in {name}: {declaration[1]}")
                    continue
                column, kind, tail = match.groups()
                table.columns.append({"name": column, "type": kind,
                                      "nullable": "NOT NULL" not in tail and "PRIMARY KEY" not in tail})
                if "PRIMARY KEY" in tail:
                    table.primary.append(column)
                if "UNIQUE" in tail:
                    table.unique.append([column])
            for columns in re.findall(r"(?:^|\n)\s*PRIMARY KEY \(([^)]+)\)", body):
                table.primary = [column.strip() for column in columns.split(",")]
            for columns in re.findall(r"UNIQUE KEY \w+ \(([^)]+)\)", body):
                table.unique.append([column.strip() for column in columns.split(",")])
            for columns, parent, keys in re.findall(r"FOREIGN KEY \(([^)]+)\) REFERENCES (\w+)\(([^)]+)\)", body):
                table.foreign.extend((column.strip(), parent, key.strip())
                                     for column, key in zip(columns.split(","), keys.split(",")))
            for column in table.columns:
                if column["name"] in table.primary:
                    column["nullable"] = False
            assert table.primary and table.columns, name
            tables[name] = table
    for name, table in tables.items():
        for column, parent, key in table.foreign:
            assert column in [c["name"] for c in table.columns], (name, column)
            assert key in [c["name"] for c in tables[parent].columns], (parent, key)
    return tables


def measure(text, size, bold=False):
    return pdfmetrics.stringWidth(text, "DiagramBold" if bold else "Diagram", size)


def wrap(text, width, size):
    result, line = [], ""
    for word in text.split():
        proposed = (line + " " + word).strip()
        if line and measure(proposed, size) > width:
            result.append(line)
            line = word
        else:
            line = proposed
    return result + ([line] if line else [])


class Scene:
    def __init__(self, number, title, subtitle):
        self.items, self.cards, self.edges = [], {}, set()
        self.number = number
        self.rect(0, 0, W, H, "#ffffff")
        self.text(60, 64, "Patent Intelligence Platform | Relational model", 31, bold=True)
        self.text(60, 100, f"Sheet {number} of 2 - {title}", 19, color=BLUE if number == 1 else GREEN, bold=True)
        self.text(60, 127, subtitle, 13, color=MUTED)

    def rect(self, x, y, w, h, fill, stroke=None, dash=False):
        self.items.append(("rect", x, y, w, h, fill, stroke, dash))

    def text(self, x, y, value, size=13, color=INK, bold=False, align="left", underline=False):
        self.items.append(("text", x, y, str(value), size, color, bold, align, underline))

    def line(self, points, color=MUTED, width=1.8, arrow=False):
        self.items.append(("line", points, color, width))
        if arrow:
            end, previous = points[-1], points[-2]
            angle = math.atan2(end[1] - previous[1], end[0] - previous[0])
            x, y = end
            a = (x - 9 * math.cos(angle) + 3.8 * math.sin(angle), y - 9 * math.sin(angle) - 3.8 * math.cos(angle))
            b = (x - 9 * math.cos(angle) - 3.8 * math.sin(angle), y - 9 * math.sin(angle) + 3.8 * math.cos(angle))
            self.items.append(("polygon", [end, a, b], color))

    def dot(self, x, y, color):
        self.items.append(("circle", x, y, 3, color))

    def card(self, name, x, y, width=300, notes=(), reference=False, support=False):
        table = TABLES[name]
        columns = table.columns[:1] if reference else table.columns
        note_lines = []
        if not reference:
            for unique in table.unique:
                if len(unique) > 1:
                    note_lines.extend(wrap("UQ (" + ", ".join(unique) + ")", width - 24, 10.5))
        for note in notes:
            note_lines.extend(wrap(note, width - 24, 10.5))
        height = HEADER + COLUMNS + ROW * len(columns) + (14 * len(note_lines) + 14 if note_lines else 8)
        self.cards[name] = (x, y, width, height, columns)
        junction = len(table.primary) > 1
        color = MUTED if reference else GREEN if support else "#9a651f" if junction else BLUE
        self.rect(x, y, width, height, "#ffffff", color, reference)
        self.rect(x, y, width, HEADER, color)
        label = name + (" [ref]" if reference else "")
        size = min(17, (width - 24) * 17 / max(measure(label, 17, True), 1))
        self.text(x + 12, y + 24, label, size, "#ffffff", True)
        self.rect(x + 1, y + HEADER, width - 2, COLUMNS, "#edf1f6")
        self.text(x + 12, y + HEADER + 16, "KEY", 10, MUTED, True)
        self.text(x + 70, y + HEADER + 16, "ATTRIBUTE", 10, MUTED, True)
        self.text(x + width - 12, y + HEADER + 16, "SQL TYPE", 10, MUTED, True, "right")
        foreign = {col for col, _, _ in table.foreign}
        single_unique = {group[0] for group in table.unique if len(group) == 1}
        for index, column in enumerate(columns):
            name_ = column["name"]
            top = y + HEADER + COLUMNS + index * ROW
            primary = name_ in table.primary
            if primary or index % 2 == 0:
                self.rect(x + 1, top, width - 2, ROW, "#fff8eb" if junction and primary else "#f1f6fc" if primary else "#f8fafc")
            flags = [flag for condition, flag in ((primary, "PK"), (name_ in foreign, "FK"), (name_ in single_unique, "UQ")) if condition]
            self.text(x + 12, top + 15, "/".join(flags), 9.3, color, True)
            kind = "ENUM" if column["type"].startswith("ENUM") else column["type"].replace(" UNSIGNED", " unsigned")
            field = name_ + (" ?" if column["nullable"] else "")
            available = width - 70 - measure(kind, 10.1) - 24
            size = min(12.2, available * 12.2 / max(measure(field, 12.2, primary), 1))
            assert size >= 9.5, (name, field, size)
            self.text(x + 70, top + 15, field, size, bold=primary, underline=primary)
            self.text(x + width - 12, top + 15, kind, 10.1, MUTED, align="right")
        for index, note in enumerate(note_lines):
            self.text(x + 12, y + HEADER + COLUMNS + len(columns) * ROW + 16 + index * 14, note, 10.5, MUTED)
        return self

    def anchor(self, name, column, side):
        x, y, width, _, columns = self.cards[name]
        index = next(i for i, value in enumerate(columns) if value["name"] == column)
        return (x if side == "left" else x + width, y + HEADER + COLUMNS + (index + 0.5) * ROW)

    def fk(self, child, column, parent, key, points, *, branch=False, color=MUTED):
        assert (column, parent, key) in TABLES[child].foreign, (child, column, parent, key)
        self.edges.add((child, column, parent, key))
        # Insert connectors behind boxes/text. Endpoints lie on table borders.
        self.line(points, color, arrow=not branch)

    def notes(self, x, y, width, title, lines, height):
        self.rect(x, y, width, height, "#f4f7fa", "#dce3ec")
        self.text(x + 20, y + 31, title, 17, bold=True)
        cursor = y + 58
        for line in lines:
            for wrapped in wrap(line, width - 40, 13):
                self.text(x + 20, cursor, wrapped, 13, MUTED)
                cursor += 20
        assert cursor < y + height - 3, title

    def footer(self):
        self.line([(60, 1206), (1740, 1206)], "#d7dfe9", 1)
        self.text(60, 1230, "PK = primary key (underlined)   FK = foreign key   UQ = unique constraint   ? = NULL permitted", 12, bold=True)
        self.text(60, 1252, "All PK-marked fields in a table form ONE key. Arrows point from FK fields to referenced PKs; joined branches share that PK target.", 11.5, MUTED)
        self.text(1740, 1230, "Source: 01_schema.sql + 05_auth.sql", 11.5, MUTED, align="right")
        self.text(1740, 1252, "Defaults and secondary indexes omitted. [ref] repeats an existing table.", 11.5, MUTED, align="right")

    def verify(self):
        cards = list(self.cards.items())
        for i, (name, (x, y, w, h, _)) in enumerate(cards):
            assert x >= 0 and y >= 145 and x + w <= W - 20 and y + h < 1200, name
            for other, (a, b, c, d, _) in cards[i + 1:]:
                assert not (max(x, a) < min(x + w, a + c) and max(y, b) < min(y + h, b + d)), (name, other)
        for item in self.items:
            if item[0] != "line":
                continue
            for (a, b), (c, d) in zip(item[1], item[1][1:]):
                for name, (x, y, w, h, _) in cards:
                    horizontal = b == d and y < b < y + h and max(min(a, c), x) < min(max(a, c), x + w)
                    vertical = a == c and x < a < x + w and max(min(b, d), y) < min(max(b, d), y + h)
                    assert not (horizontal or vertical), ("Connector intersects table", name, (a, b), (c, d))

    def svg(self):
        content = []
        # Connectors first; cards protect their interiors from crossing strokes.
        ordered = [v for v in self.items if v[0] in ("line", "polygon", "circle")] + [v for v in self.items if v[0] not in ("line", "polygon", "circle")]
        # The background must be first, before connectors.
        ordered = [self.items[0]] + [v for v in ordered if v is not self.items[0]]
        for item in ordered:
            if item[0] == "rect":
                _, x, y, w, h, fill, stroke, dash = item
                content.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke or "none"}" stroke-width="1.4"' + (' stroke-dasharray="5 4"' if dash else '') + '/>')
            elif item[0] == "text":
                _, x, y, text, size, color, bold, align, underline = item
                anchor = "end" if align == "right" else "start"
                content.append(f'<text x="{x}" y="{y}" font-family="Arial, Helvetica, sans-serif" font-size="{size}" fill="{color}" font-weight="{700 if bold else 400}" text-anchor="{anchor}"' + (' text-decoration="underline"' if underline else '') + f'>{html.escape(text)}</text>')
            elif item[0] == "line":
                _, points, color, width = item
                content.append(f'<polyline points="{" ".join(f"{x},{y}" for x, y in points)}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"/>')
            elif item[0] == "polygon":
                _, points, color = item
                content.append(f'<polygon points="{" ".join(f"{x},{y}" for x, y in points)}" fill="{color}"/>')
            elif item[0] == "circle":
                _, x, y, radius, color = item
                content.append(f'<circle cx="{x}" cy="{y}" r="{radius}" fill="{color}"/>')
        return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img"><title>Relational model, sheet {self.number}</title>\n' + "\n".join(content) + "\n</svg>\n"

    def pdf(self, target):
        page_w, page_h = landscape(A2)
        factor = min(page_w / W, page_h / H)
        target.saveState()
        target.translate((page_w - W * factor) / 2, (page_h - H * factor) / 2)
        target.scale(factor, factor)
        # Render the same scene as the SVG with top-left coordinates.
        ordered = [self.items[0]] + [v for v in self.items[1:] if v[0] in ("line", "polygon", "circle")] + [v for v in self.items[1:] if v[0] not in ("line", "polygon", "circle")]
        for item in ordered:
            if item[0] == "rect":
                _, x, y, w, h, fill, stroke, dash = item
                target.setFillColor(HexColor(fill))
                target.setStrokeColor(HexColor(stroke or fill))
                target.setLineWidth(1.4)
                target.setDash([5, 4] if dash else [])
                target.rect(x, H - y - h, w, h, fill=1, stroke=bool(stroke))
                target.setDash([])
            elif item[0] == "text":
                _, x, y, text, size, color, bold, align, underline = item
                target.setFillColor(HexColor(color))
                target.setFont("DiagramBold" if bold else "Diagram", size)
                if align == "right":
                    x -= measure(text, size, bold)
                target.drawString(x, H - y, text)
                if underline:
                    target.setStrokeColor(HexColor(color))
                    target.setLineWidth(0.65)
                    target.line(x, H - y - 1.6, x + measure(text, size, bold), H - y - 1.6)
            elif item[0] in ("line", "polygon"):
                _, points, color, *width = item
                target.setStrokeColor(HexColor(color))
                target.setFillColor(HexColor(color))
                target.setLineWidth(width[0] if width else 0)
                path = target.beginPath()
                path.moveTo(points[0][0], H - points[0][1])
                for x, y in points[1:]:
                    path.lineTo(x, H - y)
                if item[0] == "polygon":
                    path.close()
                target.drawPath(path, stroke=item[0] == "line", fill=item[0] == "polygon")
            else:
                _, x, y, radius, color = item
                target.setFillColor(HexColor(color))
                target.circle(x, H - y, radius, fill=1, stroke=0)
        target.restoreState()
        target.showPage()


def patent_sheet():
    s = Scene(1, "Patent catalog and knowledge relationships", "Mapping from Chen sheet 1 | Full table attributes, primary/foreign keys, and junction tables")
    s.card("patents", 740, 340, notes=("Year: 1800-2200 when known.", "Current incoming citation count is nonnegative."))
    for parent, child, key, y, note in (
        ("domains", "patent_domains", "domain_id", 180, "All domain memberships (M:N)."),
        ("assignees", "patent_assignees", "assignee_id", 440, "ASSIGNED TO (M:N)."),
        ("inventors", "patent_inventors", "inventor_id", 700, "INVENTS (M:N)."),
    ):
        s.card(parent, 60, y).card(child, 410, y, notes=(note,))
        source, target = s.anchor(child, key, "left"), s.anchor(parent, key, "right")
        s.fk(child, key, parent, key, [source, (385, source[1]), (385, target[1]), target])
    for parent, child, key, y, note in (
        ("cpc_codes", "patent_cpc_codes", "cpc_code", 180, "CLASSIFIED AS (M:N)."),
        ("npl_references", "patent_npl_references", "npl_id", 440, "CITES (M:N)."),
    ):
        s.card(child, 1090, y, notes=(note,)).card(parent, 1440, y)
        source, target = s.anchor(child, key, "right"), s.anchor(parent, key, "left")
        s.fk(child, key, parent, key, [source, (1415, source[1]), (1415, target[1]), target])
    s.card("citation_snapshots", 1440, 740, notes=("HAS: one patent, zero or more snapshots.",))
    s.card("patent_families", 1090, 995, notes=("RELATED TO: both FK fields reference patents.", "A publication cannot be related to itself."))
    left = ["patent_domains", "patent_assignees", "patent_inventors"]
    right = ["patent_cpc_codes", "patent_npl_references", "citation_snapshots", "patent_families"]
    for child in left + right:
        side, bus = ("right", 725) if child in left else ("left", 1065)
        source = s.anchor(child, "patent_id", side)
        s.fk(child, "patent_id", "patents", "patent_id", [source, (bus, source[1])], branch=True, color=BLUE)
        s.dot(bus, source[1], BLUE)
    source = s.anchor("patent_families", "related_patent_id", "left")
    s.fk("patent_families", "related_patent_id", "patents", "patent_id", [source, (1065, source[1])], branch=True, color=BLUE)
    s.dot(1065, source[1], BLUE)
    for bus, top, bottom, side in ((725, 250, 770, "left"), (1065, 250, source[1], "right")):
        s.line([(bus, top), (bus, bottom)], BLUE)
        target = s.anchor("patents", "patent_id", side)
        s.line([(bus, target[1]), target], BLUE, arrow=True)
    source, target = s.anchor("patents", "domain_id", "left"), s.anchor("domains", "domain_id", "left")
    s.fk("patents", "domain_id", "domains", "domain_id", [source, (735, source[1]), (735, 900), (25, 900), (25, target[1]), target], color=BLUE)
    s.text(90, 885, "Optional preferred display domain (separate from all-domain memberships)", 12, BLUE)
    s.notes(60, 965, 960, "Chen relationships become relational keys", [
        "ASSIGNED TO, INVENTS, CLASSIFIED AS and CITES become separate junction tables.",
        "patent_domains retains every domain membership; patents.domain_id selects a preferred domain.",
        "The family relation has a three-part PK: patent_id, related_patent_id and relation_type.",
        "Citation snapshots keep observation history; patent publication IDs remain separate records.",
    ], 190)
    s.footer()
    return s


def analysis_sheet():
    s = Scene(2, "Accounts, saved analysis and authentication", "Mapping from Chen sheet 2 | Authentication support tables added from the current implementation")
    s.card("app_users", 60, 180, 320, support=True)
    s.card("user_roles", 500, 180, notes=("HAS ROLE (M:N).",))
    s.card("roles", 900, 180)
    s.card("patents", 1410, 190, 330, reference=True, notes=("Same publication table as sheet 1.",))
    s.card("analysis_cases", 500, 480, 320, notes=("Owner may be NULL for preserved legacy cases.",))
    s.card("analysis_runs", 980, 480, 340, notes=("query_id is NOT unique; run_id identifies a run.", "top_k: 1-100. Each run belongs to one case."))
    s.card("run_patent_results", 1410, 480, 330)
    s.card("evaluation_metrics", 980, 940, 340, notes=("UNIQUE run_id: zero or one evaluation per run.",))
    s.card("improvement_recommendations", 1410, 940, 330)
    s.card("auth_sessions", 60, 520, 320, support=True, notes=("Stores token hashes, never raw session tokens.",))
    s.card("auth_rate_limits", 60, 900, 320, support=True, notes=("Independent hashed throttle buckets.", "No foreign key to users or sessions."))
    for child, column, side in (("user_roles", "user_id", "left"), ("analysis_cases", "owner_user_id", "left"), ("auth_sessions", "user_id", "right")):
        source = s.anchor(child, column, side)
        s.fk(child, column, "app_users", "user_id", [source, (420, source[1])], branch=True, color=GREEN)
        s.dot(420, source[1], GREEN)
    target = s.anchor("app_users", "user_id", "right")
    s.line([(420, target[1]), (420, s.anchor("auth_sessions", "user_id", "right")[1])], GREEN)
    s.line([(420, target[1]), target], GREEN, arrow=True)
    for child, column, parent, key, bus, side in (
        ("user_roles", "role_id", "roles", "role_id", 850, "right"),
        ("analysis_runs", "case_id", "analysis_cases", "case_id", 900, "left"),
    ):
        source = s.anchor(child, column, side)
        target = s.anchor(parent, key, "left" if side == "right" else "right")
        s.fk(child, column, parent, key, [source, (bus, source[1]), (bus, target[1]), target])
    for child, side in (("run_patent_results", "left"), ("evaluation_metrics", "right"), ("improvement_recommendations", "left")):
        source = s.anchor(child, "run_id", side)
        s.fk(child, "run_id", "analysis_runs", "run_id", [source, (1370, source[1])], branch=True, color=GREEN)
        s.dot(1370, source[1], GREEN)
    target = s.anchor("analysis_runs", "run_id", "right")
    s.line([(1370, target[1]), (1370, s.anchor("evaluation_metrics", "run_id", "right")[1])], GREEN)
    s.line([(1370, target[1]), target], GREEN, arrow=True)
    source, target = s.anchor("run_patent_results", "patent_id", "right"), s.anchor("patents", "patent_id", "right")
    s.fk("run_patent_results", "patent_id", "patents", "patent_id", [source, (1765, source[1]), (1765, target[1]), target], color=BLUE)
    s.notes(500, 900, 400, "Chen relationship mapping", [
        "HAS ROLE -> user_roles (composite PK).",
        "OWNS -> analysis_cases.owner_user_id.",
        "CONTAINS -> analysis_runs.case_id.",
        "RETRIEVES RESULT -> run_patent_results.",
        "EVALUATES -> evaluation_metrics.run_id (UNIQUE).",
        "PRODUCES -> improvement_recommendations.run_id.",
    ], 265)
    s.text(500, 365, "Cases have zero or more runs. Each saved result references one run and one patent.", 13, MUTED)
    s.text(500, 389, "An evaluation is optional. Multiple recommendations may belong to one run.", 13, MUTED)
    s.footer()
    return s


def mermaid():
    lines = ["%% Generated from database/sql/01_schema.sql and 05_auth.sql.", "erDiagram"]
    for child, table in TABLES.items():
        for column, parent, key in table.foreign:
            nullable = next(c["nullable"] for c in table.columns if c["name"] == column)
            to_one = any(group == [column] for group in table.unique + [table.primary])
            lines.append(f"  {parent.upper()} {'o|' if nullable else '||'}--{'o|' if to_one else 'o{'} {child.upper()} : {column}")
    for name, table in TABLES.items():
        lines.extend(["", f"  {name.upper()} {{"])
        foreign = {col for col, _, _ in table.foreign}
        for column in table.columns:
            key = column["name"]
            flags = [label for condition, label in ((key in table.primary, "PK"), (key in foreign, "FK"), ([key] in table.unique, "UK")) if condition]
            kind = re.match(r"\w+", column["type"]).group().lower()
            lines.append(f"    {kind} {key}" + (" " + ", ".join(flags) if flags else ""))
        lines.append("  }")
        for unique in table.unique:
            if len(unique) > 1:
                lines.append(f"  %% {name}: UNIQUE ({', '.join(unique)})")
    return "\n".join(lines) + "\n"


def main():
    global TABLES
    font_dir = Path("C:/Windows/Fonts")
    if (font_dir / "arial.ttf").exists():
        pdfmetrics.registerFont(TTFont("Diagram", str(font_dir / "arial.ttf")))
        pdfmetrics.registerFont(TTFont("DiagramBold", str(font_dir / "arialbd.ttf")))
    else:
        from reportlab.pdfbase.pdfmetrics import Font
        pdfmetrics.registerFont(Font("Diagram", "Helvetica", "WinAnsiEncoding"))
        pdfmetrics.registerFont(Font("DiagramBold", "Helvetica-Bold", "WinAnsiEncoding"))
    TABLES = read_schema()
    sheets = [patent_sheet(), analysis_sheet()]
    for sheet in sheets:
        sheet.verify()
    expected = {(child, col, parent, key) for child, table in TABLES.items() for col, parent, key in table.foreign}
    drawn = set().union(*(sheet.edges for sheet in sheets))
    assert expected == drawn, ("Missing/unexpected FK connectors", expected - drawn, drawn - expected)
    assert set(TABLES) == set().union(*(set(sheet.cards) for sheet in sheets)), "Unmapped table"
    PDF.parent.mkdir(parents=True, exist_ok=True)
    DOCS.mkdir(parents=True, exist_ok=True)
    target = canvas.Canvas(str(PDF), pagesize=landscape(A2), pageCompression=1)
    target.setTitle("Patent Intelligence Platform - ER to Relational Model")
    target.setAuthor("Patent Intelligence Platform")
    target.setSubject("Implemented SQL relations mapped from the two Chen ER sheets")
    for sheet, slug in zip(sheets, ("patent-data", "analysis-data")):
        (DOCS / f"relational-model-{slug}.svg").write_text(sheet.svg(), encoding="utf-8", newline="\n")
        sheet.pdf(target)
    target.save()
    overview = f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H * 2}" viewBox="0 0 {W} {H * 2}">\n'
    for index, sheet in enumerate(sheets):
        svg = sheet.svg().replace('viewBox="0 0 1800 1273"', f'y="{index * H}" viewBox="0 0 1800 1273"', 1)
        overview += svg
    (DOCS / "er-model.svg").write_text(overview + "</svg>\n", encoding="utf-8", newline="\n")
    (DOCS / "er-model.mmd").write_text(mermaid(), encoding="utf-8", newline="\n")
    print(f"Generated {len(TABLES)} tables, {sum(len(t.columns) for t in TABLES.values())} columns, {len(expected)} foreign keys.")
    print(f"PDF: {PDF}")
    print("Validated: complete table/FK coverage; no overlapping cards or connectors through table interiors.")


if __name__ == "__main__":
    main()
