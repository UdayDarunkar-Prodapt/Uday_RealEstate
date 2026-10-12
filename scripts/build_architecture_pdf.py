"""Build the architecture diagram PDF using only the Python standard library."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "architecture.pdf"
W, H = 1200, 820
ops = []


def esc(value):
    value = str(value).encode("ascii", "replace").decode("ascii")
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def text(x, y, value, size=12, color=(.12, .20, .19)):
    r, g, b = color
    ops.append(f"{r} {g} {b} rg BT /F1 {size} Tf {x} {y} Td ({esc(value)}) Tj ET")


def box(x, y, w, h, title, lines, fill=(.94, .96, .93)):
    r, g, b = fill
    ops.append(f"{r} {g} {b} rg {x} {y} {w} {h} re f .20 .31 .28 RG 1.3 w {x} {y} {w} {h} re S")
    text(x + 11, y + h - 23, title, 12)
    for i, line in enumerate(lines):
        text(x + 11, y + h - 43 - i * 16, line, 9.5)


def arrow(x1, y1, x2, y2, label=None):
    ops.append(f".20 .31 .28 RG 1.5 w {x1} {y1} m {x2} {y2} l S")
    if abs(x2-x1) >= abs(y2-y1):
        sign = 1 if x2 > x1 else -1
        ops.append(f"{x2-sign*7} {y2+4} m {x2} {y2} l {x2-sign*7} {y2-4} l S")
    else:
        sign = 1 if y2 > y1 else -1
        ops.append(f"{x2-4} {y2-sign*7} m {x2} {y2} l {x2+4} {y2-sign*7} l S")
    if label:
        text((x1+x2)/2-25, (y1+y2)/2+8, label, 8, (.30, .38, .34))


text(35, 780, "AI-Powered Real Estate Property Valuation Assistant", 22)
text(35, 755, "Architecture | Offline property index and online retrieval-grounded valuation", 12)
text(35, 710, "OFFLINE DATA, TRAINING, AND INDEX BUILD", 13)

box(30, 575, 155, 100, "Ames Housing CSV", ["2,930 sale records", "81 source columns"])
box(220, 575, 165, 100, "Preprocessing", ["Canonical field names", "Quality labels -> 1..10"], (.91, .95, .91))
box(420, 575, 165, 100, "Property records", ["One row -> one text doc", "No text chunk splitting"], (.97, .94, .85))
box(620, 575, 165, 100, "Embeddings", ["all-MiniLM-L6-v2", "Local + normalized"], (.91, .95, .91))
box(820, 575, 165, 100, "ChromaDB", ["Persistent vectors", "Cosine + metadata"], (.91, .95, .91))
box(820, 435, 165, 80, "Lexical index", ["Tokens -> BM25Okapi"], (.91, .95, .91))
box(220, 435, 165, 80, "Training", ["MAE-selected regressor"])
box(420, 435, 165, 80, "Model artifact", ["Tree model + medians"])
arrow(185, 625, 220, 625)
arrow(385, 625, 420, 625)
arrow(585, 625, 620, 625)
arrow(785, 625, 820, 625)
arrow(500, 575, 820, 475, "same property docs")
arrow(302, 575, 302, 515)
arrow(385, 475, 420, 475)

text(35, 385, "ONLINE PROPERTY REQUEST AND RAG WORKFLOW", 13)
box(25, 225, 135, 105, "User / React UI", ["Description + fields", "Dashboard sections"])
box(180, 225, 135, 105, "FastAPI request", ["Validation + routes", "OpenAPI documentation"], (.91, .95, .91))
box(335, 225, 145, 105, "Classification", ["LangGraph node", "Extract + validate facts"], (.97, .94, .85))
box(500, 225, 150, 105, "Hybrid retriever", ["Chroma semantic", "BM25 + metadata filters"])
box(670, 225, 150, 105, "RAG evidence", ["RRF ranked records", "Comparable context"], (.97, .94, .85))
box(840, 225, 150, 105, "Valuation agents", ["Model + SHAP", "Risk + decision"], (.97, .94, .85))
box(1010, 225, 160, 105, "API response -> UI", ["Estimate + range", "Evidence + safeguards"], (.91, .95, .91))
arrow(160, 277, 180, 277, "POST")
arrow(315, 277, 335, 277)
arrow(480, 277, 500, 277)
arrow(650, 277, 670, 277)
arrow(820, 277, 840, 277)
arrow(990, 277, 1010, 277)
arrow(900, 575, 575, 330)
arrow(900, 435, 575, 330)
arrow(502, 435, 915, 330)

box(365, 75, 290, 85, "Optional explanation evaluation", ["Claude judge: explanation only", "DeepEval: one GEval metric"], (.96, .92, .86))
box(715, 75, 250, 85, "Local persistence", ["SQLite: valuations + feedback", "Persistence failure is nonfatal"])
arrow(1090, 225, 655, 120, "judge route: no price changes")
arrow(250, 225, 840, 160, "history / feedback")
text(35, 28, "Retrieved evidence grounds the estimate. Claude is an optional judge, not the valuation or embedding model.", 9)

content = "\n".join(ops).encode("ascii")
objects = [
    b"<< /Type /Catalog /Pages 2 0 R >>",
    b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W} {H}] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>".encode(),
    b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
]
pdf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
offsets = [0]
for i, obj in enumerate(objects, 1):
    offsets.append(len(pdf))
    pdf.extend(f"{i} 0 obj\n".encode() + obj + b"\nendobj\n")
xref = len(pdf)
pdf.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
for offset in offsets[1:]:
    pdf.extend(f"{offset:010d} 00000 n \n".encode())
pdf.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
OUT.write_bytes(pdf)
print(OUT)
