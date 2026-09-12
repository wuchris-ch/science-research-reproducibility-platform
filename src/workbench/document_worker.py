"""Resource-bounded document decoding child. Its input is inert source material."""

import hashlib
import json
import resource
import sys
from contextlib import closing
from pathlib import Path


def decode(kind, path):
    data = path.read_bytes()
    if len(data) > 9_000_000:
        raise ValueError("Document exceeds 9 MB")
    identity = hashlib.sha256(data).hexdigest()
    segments = []

    def add(text, source_kind, **location):
        text = " ".join(text.split())
        if text and len(segments) < 4000:
            segments.append(
                {
                    "id": f"{identity[:16]}:{len(segments)}",
                    "source_sha256": identity,
                    "kind": source_kind,
                    "text": text[:6000],
                    **location,
                }
            )

    if kind == "pdf":
        import pypdfium2 as pdfium

        with pdfium.PdfDocument(data) as doc:
            if len(doc) > 100:
                raise ValueError("PDF exceeds 100 pages")
            for index in range(len(doc)):
                with closing(doc[index]) as page, closing(page.get_textpage()) as textpage:
                    value = textpage.get_text_range()
                    if len(value) > 100_000:
                        raise ValueError("PDF page text exceeds limit")
                    cursor = 0
                    width, height = page.get_size()
                    for line in value.splitlines(keepends=True):
                        text = line.strip()
                        offset = value.find(text, cursor) if text else cursor
                        rectangles = (
                            [textpage.get_rect(i) for i in range(textpage.count_rects(offset, len(text)))]
                            if text
                            else []
                        )
                        cursor += len(line)
                        if rectangles:
                            left = min(r[0] for r in rectangles)
                            bottom = min(r[1] for r in rectangles)
                            right = max(r[2] for r in rectangles)
                            top = max(r[3] for r in rectangles)
                            add(
                                text,
                                "pdf-text",
                                page=index + 1,
                                bbox=[left / width, 1 - top / height, right / width, 1 - bottom / height],
                                char_start=offset,
                                char_count=len(text),
                            )
    elif kind == "xml":
        from defusedxml import ElementTree

        root = ElementTree.fromstring(data)
        for index, node in enumerate(root.iter()):
            if node.tag in ("p", "preformat", "fig", "table-wrap", "supplementary-material"):
                add("".join(node.itertext()), node.tag, xml_id=node.get("id"), element_index=index)
    elif kind == "tsv":
        from .inputs import rows

        header, values = rows(data, limit=1000)
        for row, cells in enumerate(values, 2):
            add(
                "; ".join(f"{key}: {value}" for key, value in zip(header, cells, strict=True)),
                "table-row",
                row=row,
                columns=header,
            )
    else:
        raise ValueError("Supported documents are PDF, JATS XML and TSV supplements")
    if not segments:
        raise ValueError("No extractable text found; supply a text version for source-linked review")
    return {"sha256": identity, "segments": segments, "truncated": len(segments) >= 4000}


def main():
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    resource.setrlimit(resource.RLIMIT_FSIZE, (12_000_000, 12_000_000))
    resource.setrlimit(resource.RLIMIT_NOFILE, (64, 64))
    if sys.platform != "darwin":
        resource.setrlimit(resource.RLIMIT_AS, (1_500_000_000, 1_500_000_000))
    kind, file = sys.argv[1:3]
    if kind == "render":
        import pypdfium2 as pdfium

        with pdfium.PdfDocument(file) as doc, closing(doc[int(sys.argv[3]) - 1]) as page:
            scale = min(1.7, 1600 / max(page.get_size()))
            page.render(scale=scale).to_pil().save(sys.stdout.buffer, format="PNG")
    else:
        print(json.dumps(decode(kind, Path(file)), ensure_ascii=True))


if __name__ == "__main__":
    main()
