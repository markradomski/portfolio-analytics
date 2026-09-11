"""Build minimal single- or multi-page PDFs from plain text.

Real statements cannot be committed, so end-to-end tests need synthetic PDFs
that still exercise the extraction layer. This writes the smallest valid PDF
that pdfplumber will read text out of.
"""

from __future__ import annotations

from pathlib import Path


def _escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")


def _content_stream(lines: list[str]) -> bytes:
    body = ["BT", "/F1 9 Tf", "40 750 Td", "12 TL"]
    body += [f"({_escape(line)}) Tj T*" for line in lines]
    body.append("ET")
    return "\n".join(body).encode("latin-1", "replace")


def build_pdf(path: Path, pages: list[list[str]]) -> Path:
    """Write a PDF whose pages contain the given lines, one line per row."""
    objects: list[bytes] = []

    def add(raw: bytes) -> int:
        objects.append(raw)
        return len(objects)          # 1-indexed object number

    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    page_ids: list[int] = []
    content_ids: list[int] = []
    for lines in pages:
        stream = _content_stream(lines)
        content_ids.append(add(
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n"
            + stream + b"\nendstream"))
        page_ids.append(0)           # placeholder, filled below

    pages_obj = len(objects) + len(pages) + 1
    for index, content_id in enumerate(content_ids):
        page_ids[index] = add(
            b"<< /Type /Page /Parent " + str(pages_obj).encode()
            + b" 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 "
            + str(font).encode() + b" 0 R >> >> /Contents "
            + str(content_id).encode() + b" 0 R >>")

    kids = b" ".join(f"{pid} 0 R".encode() for pid in page_ids)
    add(b"<< /Type /Pages /Kids [" + kids + b"] /Count "
        + str(len(pages)).encode() + b" >>")
    catalog = add(b"<< /Type /Catalog /Pages " + str(pages_obj).encode() + b" 0 R >>")

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += str(number).encode() + b" 0 obj\n" + body + b"\nendobj\n"

    xref_at = len(out)
    out += b"xref\n0 " + str(len(objects) + 1).encode() + b"\n"
    out += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        out += f"{offset:010d} 00000 n \n".encode()
    out += (b"trailer\n<< /Size " + str(len(objects) + 1).encode()
            + b" /Root " + str(catalog).encode() + b" 0 R >>\nstartxref\n"
            + str(xref_at).encode() + b"\n%%EOF\n")

    path.write_bytes(bytes(out))
    return path
