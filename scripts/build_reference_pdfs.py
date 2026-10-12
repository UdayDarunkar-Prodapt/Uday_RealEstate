"""Build readable API and dataset reference PDFs using only the Python stdlib."""
from pathlib import Path
import re
import textwrap

ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = [
    (ROOT / "docs" / "API_Documentation.md", ROOT / "docs" / "API_Documentation.pdf"),
    (ROOT / "docs" / "data_details.md", ROOT / "docs" / "data_details.pdf"),
]
PAGE_W, PAGE_H = 612, 792
LEFT, RIGHT, TOP, BOTTOM = 52, 52, 54, 48


def ascii_pdf(value):
    value = value.replace("→", "->").replace("–", "-").replace("—", "-").replace("’", "'").replace("“", '"').replace("”", '"')
    value = value.encode("ascii", "replace").decode("ascii")
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def parse_markdown(source):
    rendered = []
    fenced = False
    for raw in source.read_text(encoding="utf-8").splitlines():
        line = raw.rstrip()
        if line.strip().startswith("```"):
            fenced = not fenced
            rendered.append(("", "code" if fenced else "space"))
            continue
        if not line.strip():
            rendered.append(("", "space"))
            continue
        if not fenced and line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            rendered.append((line[level:].strip(), f"h{min(level, 3)}"))
            continue
        if not fenced:
            line = re.sub(r"\[([^]]+)\]\(([^)]+)\)", r"\1 (\2)", line)
            line = re.sub(r"[`*_]", "", line)
        style = "code" if fenced else ("table" if line.startswith("|") else "body")
        if style == "table":
            line = line.replace("|", "  |  ").strip(" |")
        width = 92 if style in {"body", "table"} else 86
        wrapped = textwrap.wrap(line, width=width, break_long_words=True, break_on_hyphens=False) or [""]
        rendered.extend((item, style) for item in wrapped)
    return rendered


def paginate(lines):
    pages, page, y = [], [], PAGE_H - TOP
    for text, style in lines:
        if style == "h1":
            size, leading, font, gap = 19, 25, "F2", 5
        elif style == "h2":
            size, leading, font, gap = 14, 19, "F2", 4
        elif style == "h3":
            size, leading, font, gap = 11, 15, "F2", 3
        elif style == "code":
            size, leading, font, gap = 8, 11, "F3", 0
        elif style == "table":
            size, leading, font, gap = 8, 12, "F1", 0
        elif style == "space":
            size, leading, font, gap = 1, 6, "F1", 0
        else:
            size, leading, font, gap = 9, 13, "F1", 0
        if y - leading - gap < BOTTOM:
            pages.append(page)
            page, y = [], PAGE_H - TOP
        if text:
            page.append((text, font, size, y))
        y -= leading + gap
    if page:
        pages.append(page)
    return pages


def make_pdf(title, pages):
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>"]
    page_ids = [3 + 2*i for i in range(len(pages))]
    kids = " ".join(f"{ident} 0 R" for ident in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    font_id = 3 + 2*len(pages)
    for index, page in enumerate(pages, start=1):
        ops = []
        for value, font, size, y in page:
            ops.append(f"BT /{font} {size} Tf 1 0 0 1 {LEFT} {y:.1f} Tm ({ascii_pdf(value)}) Tj ET")
        ops.append(f"BT /F1 8 Tf 1 0 0 1 {LEFT} 24 Tm ({ascii_pdf(title)}  |  Page {index} of {len(pages)}) Tj ET")
        content = "\n".join(ops).encode("ascii")
        page_id, stream_id = 3 + 2*(index-1), 4 + 2*(index-1)
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
            f"/Resources << /Font << /F1 {font_id} 0 R /F2 {font_id+1} 0 R /F3 {font_id+2} 0 R >> >> "
            f"/Contents {stream_id} 0 R >>".encode()
        )
        objects.append(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream")
    objects.extend([
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
    ])
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return pdf


def main():
    for source, output in DOCUMENTS:
        lines = parse_markdown(source)
        pages = paginate(lines)
        output.write_bytes(make_pdf(source.stem.replace("_", " "), pages))
        print(output)


if __name__ == "__main__":
    main()
