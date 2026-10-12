"""Build docs/design_document.pdf from the Markdown design document (stdlib only)."""
from pathlib import Path
import re
import textwrap

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "docs" / "design_document.md"
OUTPUT = ROOT / "docs" / "design_document.pdf"
PAGE_W, PAGE_H = 612, 792


def pdf_string(value: str) -> str:
    value = value.encode("ascii", "replace").decode("ascii")
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_pages():
    lines = []
    for raw in SOURCE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line:
            lines.append("")
            continue
        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            title = line[level:].strip()
            lines.extend(["", title.upper() if level == 1 else title, ""])
            continue
        line = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", line)
        line = re.sub(r"[`*_]", "", line)
        lines.extend(textwrap.wrap(line, width=88, subsequent_indent="  ") or [""])
    pages, page = [], []
    for line in lines:
        if len(page) >= 47:
            pages.append(page)
            page = []
        page.append(line)
    if page:
        pages.append(page)
    return pages


def build():
    pages = make_pages()
    objects = []
    page_ids = [3 + i * 2 for i in range(len(pages))]
    kids = " ".join(f"{ident} 0 R" for ident in page_ids)
    objects.append(f"<< /Type /Catalog /Pages 2 0 R >>".encode())
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    for index, lines in enumerate(pages):
        page_id = 3 + index * 2
        stream_id = page_id + 1
        ops = ["BT /F1 10 Tf 48 752 Td 13 TL"]
        for line in lines:
            if line:
                size = 14 if line.isupper() and len(line) < 100 else 10
                ops.append(f"/F1 {size} Tf ({pdf_string(line)}) Tj")
            ops.append("T*")
        ops.append("ET")
        content = "\n".join(ops).encode("ascii")
        objects.append(
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
            f"/Resources << /Font << /F1 {3 + len(pages) * 2} 0 R >> >> "
            f"/Contents {stream_id} 0 R >>".encode()
        )
        objects.append(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream")
    font_id = 3 + len(pages) * 2
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
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
    OUTPUT.write_bytes(pdf)
    print(OUTPUT)


if __name__ == "__main__":
    build()
