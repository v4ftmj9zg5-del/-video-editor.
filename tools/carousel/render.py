"""Render each .slide in an HTML carousel to a 1080x1350 PNG.

Usage: render.py carousel.html OUT_DIR
"""
import os
import sys

from playwright.sync_api import sync_playwright

CHROME = os.environ.get("CHROME", "/opt/pw-browsers/chromium-1194/chrome-linux/chrome")


def main(html, out):
    os.makedirs(out, exist_ok=True)
    stem = os.path.splitext(os.path.basename(html))[0]
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=CHROME, args=["--allow-file-access-from-files"])
        page = b.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)
        page.goto("file://" + os.path.abspath(html))
        page.wait_for_timeout(600)
        for i, el in enumerate(page.query_selector_all(".slide"), 1):
            path = os.path.join(out, f"{stem}_{i}.png")
            el.screenshot(path=path)
            print("wrote", path)
        b.close()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
