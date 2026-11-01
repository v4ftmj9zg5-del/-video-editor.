"""Turn client-kit pages into fillable PDF forms (fill on a phone).

Renders each HTML page to PDF with Chromium, measures every blank in the
layout (.line / .box / .m → text fields, .checks span / ul.check li →
checkboxes) and adds AcroForm widgets at those spots, right-aligned for Hebrew.

Usage: fillable.py OUT_DIR page.html [page.html ...]
"""
import os
import sys

import pymupdf
from playwright.sync_api import sync_playwright

CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")
PX_PER_MM = 96 / 25.4
PAGE_H = 297 * PX_PER_MM
PT = 72 / 96
FILL = (0.995, 0.975, 0.94)  # faint cream so fields are visible on a phone

# Collect blanks with a label to name the field after.
JS = r"""
() => {
  const out = [];
  const lab = el => {
    if (el.dataset.name) return el.dataset.name;
    const q = el.closest('.q, .legend > div, .sign > div');
    let t = '';
    if (q) { const l = q.querySelector('label, b, .small'); t = (l ? l.childNodes[0].textContent : q.textContent); }
    return (t || '').trim().replace(/\s+/g, ' ').slice(0, 60);
  };
  const r = el => { const b = el.getBoundingClientRect(); return [b.left, b.top + scrollY, b.right, b.bottom + scrollY]; };
  document.querySelectorAll('.line, .m, .fill').forEach(el => out.push({kind: 'text', label: lab(el), rect: r(el)}));
  document.querySelectorAll('.box').forEach(el => out.push({kind: 'multi', label: lab(el), rect: r(el)}));
  document.querySelectorAll('.checks span').forEach(el => out.push({kind: 'check', label: el.dataset.name || (lab(el) + ' / ' + el.textContent.trim()), rect: r(el)}));
  document.querySelectorAll('ul.check li').forEach(el => out.push({kind: 'checkli', label: el.textContent.trim().slice(0, 60), rect: r(el)}));
  return out;
}
"""


def measure(page, html):
    page.goto("file://" + os.path.abspath(html))
    page.emulate_media(media="print")
    page.wait_for_timeout(400)
    return page.evaluate(JS)


def add_fields(pdf_path, fields):
    doc = pymupdf.open(pdf_path)
    used = {}
    for f in fields:
        x0, y0, x1, y1 = f["rect"]
        pno = int(y0 // PAGE_H)
        y0 -= pno * PAGE_H
        y1 -= pno * PAGE_H
        if pno >= len(doc):
            continue
        name = f["label"] or f["kind"]
        used[name] = used.get(name, 0) + 1
        if used[name] > 1:
            name = f"{name} ({used[name]})"
        w = pymupdf.Widget()
        w.field_name = name
        w.border_width = 0
        if f["kind"] in ("text", "multi"):
            w.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
            pad_top = 0 if f["kind"] == "multi" else (y1 - y0) * 0.15
            w.rect = pymupdf.Rect(x0 * PT, (y0 + pad_top) * PT, x1 * PT, (y1 - 1) * PT)
            w.text_fontsize = 0 if f["kind"] == "text" else 10
            w.fill_color = FILL
            if f["kind"] == "multi":
                w.field_flags |= pymupdf.PDF_TX_FIELD_IS_MULTILINE
        else:
            # The drawn box is the ::before square at the RTL start (right edge) of the item.
            s = 3.4 * PX_PER_MM
            top = y0 + (3.6 if f["kind"] == "checkli" else 1.2)
            if f["kind"] == "checkli":
                top = y0 + 1.0 * PX_PER_MM
            w.field_type = pymupdf.PDF_WIDGET_TYPE_CHECKBOX
            w.rect = pymupdf.Rect((x1 - s) * PT, top * PT, x1 * PT, (top + s) * PT)
            w.field_value = False
        annot = doc[pno].add_widget(w)
        if f["kind"] in ("text", "multi"):
            doc.xref_set_key(annot.xref, "Q", "2")  # right-aligned (Hebrew)
    cat = doc.pdf_catalog()
    af = doc.xref_get_key(cat, "AcroForm")
    if af[0] == "xref":
        doc.xref_set_key(int(af[1].split()[0]), "NeedAppearances", "true")
    else:
        doc.xref_set_key(cat, "AcroForm/NeedAppearances", "true")
    out = pdf_path.replace(".pdf", "_fillable.pdf")
    doc.save(out, garbage=3, deflate=True)
    return out, len(fields)


def main():
    out_dir, pages = sys.argv[1], sys.argv[2:]
    os.makedirs(out_dir, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, args=["--allow-file-access-from-files"])
        page = browser.new_page(viewport={"width": round(210 * PX_PER_MM), "height": 1123})
        for html in pages:
            pdf = os.path.join(out_dir, os.path.basename(html).replace(".html", ".pdf"))
            fields = measure(page, html)
            page.pdf(path=pdf, format="A4", print_background=True, prefer_css_page_size=True)
            out, n = add_fields(pdf, fields)
            print(f"wrote {out} ({n} fields)")
        browser.close()


if __name__ == "__main__":
    main()
