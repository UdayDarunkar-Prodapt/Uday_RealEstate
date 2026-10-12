"""Build docs/DeepEval_Evaluation_Report.pdf with the Python standard library."""
from pathlib import Path
import re
import textwrap

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "DeepEval_Evaluation_Report.md"
OUTPUT = ROOT / "docs" / "DeepEval_Evaluation_Report.pdf"
WIDTH, HEIGHT = 612, 792


def escape(value):
    value = value.replace("–", "-").replace("—", "-").replace("’", "'")
    value = value.encode("ascii", "replace").decode("ascii")
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def lines_from_markdown():
    in_code = False
    result = []
    for raw in SOURCE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("```"):
            in_code = not in_code
            result.append(("", "space"))
            continue
        if not line:
            result.append(("", "space"))
            continue
        if not in_code and line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            result.append((line[level:].strip(), f"h{min(level, 2)}"))
            continue
        if not in_code:
            line = re.sub(r"[`*_]", "", line)
        style = "code" if in_code else ("table" if line.startswith("|") else "body")
        if style == "table":
            line = line.replace("|", "  |  ").strip(" |")
        result.extend((item, style) for item in textwrap.wrap(line, width=90, break_long_words=True) or [""])
    return result


def paginate(lines):
    pages, current, y = [], [], 742
    for value, style in lines:
        size, leading, font = {
            "h1": (18, 24, "F2"), "h2": (13, 18, "F2"),
            "code": (8, 11, "F3"), "table": (8, 12, "F1"),
            "space": (1, 7, "F1"), "body": (9, 13, "F1"),
        }[style]
        if y - leading < 45:
            pages.append(current)
            current, y = [], 742
        if value:
            current.append((value, font, size, y))
        y -= leading
    if current:
        pages.append(current)
    return pages


def build_pdf(pages):
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>"]
    kids = " ".join(f"{3 + 2*i} 0 R" for i in range(len(pages)))
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    font_id = 3 + 2*len(pages)
    for index, page in enumerate(pages, 1):
        ops = [f"BT /{font} {size} Tf 1 0 0 1 50 {y} Tm ({escape(value)}) Tj ET" for value, font, size, y in page]
        ops.append(f"BT /F1 8 Tf 1 0 0 1 50 24 Tm (DeepEval Evaluation Report | Page {index} of {len(pages)}) Tj ET")
        stream = "\n".join(ops).encode("ascii")
        page_id, stream_id = 3 + 2*(index-1), 4 + 2*(index-1)
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {WIDTH} {HEIGHT}] /Resources << /Font << /F1 {font_id} 0 R /F2 {font_id+1} 0 R /F3 {font_id+2} 0 R >> >> /Contents {stream_id} 0 R >>".encode())
        objs.append(b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream")
    objs.extend([
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>",
    ])
    pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, obj in enumerate(objs, 1):
        offsets.append(len(pdf))
        pdf.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(pdf)
    pdf.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        pdf.extend(f"{offset:010d} 00000 n \n".encode())
    pdf.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    OUTPUT.write_bytes(pdf)


if __name__ == "__main__":
    pages = paginate(lines_from_markdown())
    build_pdf(pages)
    print(OUTPUT)
