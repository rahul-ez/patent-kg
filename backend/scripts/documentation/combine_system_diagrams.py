"""Assemble the existing Chen ER, horizontal schema, and DFD into one vector PDF.

Documentation-only dependencies: reportlab, pypdf, svglib.
An optional --dependency-dir can point to isolated documentation dependencies.
The original diagrams are never modified.
"""
from __future__ import annotations

import argparse
from io import BytesIO
from pathlib import Path
import sys
import xml.etree.ElementTree as ET


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dependency-dir", type=Path)
    args = parser.parse_args()
    if args.dependency_dir:
        sys.path.insert(0, str(args.dependency_dir.resolve()))

    from pypdf import PdfReader, PdfWriter, Transformation
    from reportlab.graphics import renderPDF
    from reportlab.graphics.shapes import String
    from reportlab.lib.colors import HexColor
    from reportlab.lib.pagesizes import A2, landscape
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas
    from svglib.svglib import svg2rlg

    root = Path(__file__).resolve().parents[3]
    output = root / "output/pdf/patent-system-diagrams.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    fonts = Path("C:/Windows/Fonts")
    if (fonts / "arial.ttf").exists():
        pdfmetrics.registerFont(TTFont("Arial", str(fonts / "arial.ttf")))
        pdfmetrics.registerFont(TTFont("Arial-Bold", str(fonts / "arialbd.ttf")))
        pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold")

    sources = []
    for filename, label in [
        ("er-diagram-chen-patent-data.svg", "Chen ER model - patent knowledge data"),
        ("er-diagram-chen-analysis-data.svg", "Chen ER model - analysis and access data"),
    ]:
        svg = root / "docs/database" / filename
        drawing = svg2rlg(str(svg))
        if drawing is None:
            raise ValueError(f"Cannot read {svg}")
        svg_root = ET.parse(svg).getroot()
        elements = svg_root.findall("{http://www.w3.org/2000/svg}text")
        view_box = [float(value) for value in svg_root.get("viewBox").split()]
        sx, sy = drawing.width / view_box[2], drawing.height / view_box[3]
        bold_labels = {element.text for element in elements
                       if element.get("class") in {"title", "entity-text", "card"}}

        def preserve_bold(shape):
            # svglib does not retain numeric CSS font-weight on these sheets.
            if isinstance(shape, String) and shape.text in bold_labels:
                shape.fontName = "Arial-Bold" if (fonts / "arialbd.ttf").exists() else "Helvetica-Bold"
            for child in getattr(shape, "contents", []):
                preserve_bold(child)

        preserve_bold(drawing)
        stream = BytesIO()
        page = canvas.Canvas(stream, pagesize=(drawing.width, drawing.height))
        renderPDF.draw(drawing, page, 0, 0)
        # Retain Chen key underlines: SVG text-decoration is not converted by
        # svglib. Draw the same decoration explicitly in vector coordinates.
        page.setStrokeColor(HexColor("#172033"))
        page.setLineWidth(.8)
        for element in elements:
            if element.get("text-decoration") == "underline":
                font = "Arial" if (fonts / "arial.ttf").exists() else "Helvetica"
                text_width = pdfmetrics.stringWidth(element.text or "", font, 16) * sx
                cx = (float(element.get("x")) - view_box[0]) * sx
                baseline = drawing.height - (float(element.get("y")) - view_box[1]) * sy
                page.line(cx - text_width / 2, baseline - 2 * sy,
                          cx + text_width / 2, baseline - 2 * sy)
        page.save()
        sources.append((PdfReader(BytesIO(stream.getvalue())).pages[0], label,
                        landscape(A2)))

    schema = PdfReader(root / "output/pdf/patent-relational-schema-horizontal.pdf")
    if len(schema.pages) != 1:
        raise ValueError("Expected one horizontal relational schema sheet")
    page = schema.pages[0]
    sources.append((page, "Relational schema mapping - all relations and foreign keys",
                    (float(page.mediabox.width), float(page.mediabox.height))))
    dfd = PdfReader(root / "output/pdf/patent-data-flow-diagram.pdf")
    labels = ["Data flow - system context", "Data flow - system processes",
              "Data flow - analysis pipeline"]
    if len(dfd.pages) != len(labels):
        raise ValueError("Expected three data flow sheets")
    for page, label in zip(dfd.pages, labels):
        sources.append((page, label,
                        (float(page.mediabox.width), float(page.mediabox.height))))

    writer = PdfWriter()
    for index, (source, label, (width, height)) in enumerate(sources, 1):
        # Keep each source's aspect ratio and generous margins. Large schema
        # pages retain their native size, so every table remains zoomable.
        margin, top, bottom = 28, 54, 38
        sw, sh = float(source.mediabox.width), float(source.mediabox.height)
        scale = min((width - 2 * margin) / sw, (height - top - bottom) / sh)
        x = (width - sw * scale) / 2
        y = bottom + (height - top - bottom - sh * scale) / 2
        assert x >= margin - .01 and y >= bottom - .01
        assert x + sw * scale <= width - margin + .01
        assert y + sh * scale <= height - top + .01
        target = writer.add_blank_page(width, height)
        transform = (Transformation().translate(-float(source.mediabox.left),
                                                  -float(source.mediabox.bottom))
                     .scale(scale).translate(x, y))
        target.merge_transformed_page(source, transform)

        stream = BytesIO()
        overlay = canvas.Canvas(stream, pagesize=(width, height))
        overlay.setFillColor(HexColor("#334155"))
        overlay.setFont("Helvetica-Bold", 12)
        overlay.drawString(margin, height - 24, "PATENT INTELLIGENCE PLATFORM")
        overlay.setFont("Helvetica", 11)
        overlay.drawRightString(width - margin, height - 24, label)
        overlay.setStrokeColor(HexColor("#cbd5e1"))
        overlay.setLineWidth(.6)
        overlay.line(margin, height - 35, width - margin, height - 35)
        overlay.line(margin, 28, width - margin, 28)
        overlay.setFillColor(HexColor("#64748b"))
        overlay.setFont("Helvetica", 10)
        overlay.drawString(margin, 14, "ER model / Relational schema mapping / Data flow")
        overlay.drawRightString(width - margin, 14, f"{index} / {len(sources)}")
        overlay.save()
        target.merge_page(PdfReader(BytesIO(stream.getvalue())).pages[0])
        writer.add_outline_item(label, index - 1)
        print(f"Page {index}: {label} ({width:.0f} x {height:.0f} pt)")

    writer.add_metadata({"/Title": "Patent Intelligence Platform - System Diagrams",
                         "/Subject": "Chen ER model, relational schema mapping, and data flow",
                         "/Author": "Patent Intelligence Platform"})
    writer.page_mode = "/UseOutlines"
    with output.open("wb") as stream:
        writer.write(stream)
    result = PdfReader(output)
    assert len(result.pages) == 6
    for page in result.pages:
        assert len(page.extract_text()) > 200
    print(f"Written {output} ({output.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
