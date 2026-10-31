#!/usr/bin/env python3
"""The v4 chrome's measures in a browser (README.md), on the reference pages
(tools/sample_site.py) or on a built site: what PlayGuard's header is, kept.

    tools/chrome_layout.py <site-dir> [<page>...]

At 1280px: the header is 72px, on one row, the pill before GitHub, the content
1180px wide, a section 88px under its top. At 768px and 390px: two rows, the
links on the second, the pill first, GitHub hidden, the fading edge only when
the row scrolls, nothing wider than the screen. PLAYWRIGHT_CHROMIUM=<path> for
a browser of its own.
"""
import asyncio
import functools
import http.server
import os
import sys
import threading

from playwright.async_api import async_playwright

MEASURE = """() => {
  const box = (s) => { const e = document.querySelector(s); if (!e || !e.getClientRects().length) return null;
    const r = e.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height }; };
  const nav = document.querySelector('.top .nav');
  return { top: box('.top'), brand: box('.top .brand'), nav: box('.top .nav'), cta: box('.nav-cta'), gh: box('.nav-gh'),
           settings: box('.settings'), section: box('main .section'), eyebrow: box('main .section > .eyebrow, main .section-head .eyebrow'),
           wide: document.documentElement.scrollWidth, screen: innerWidth, more: nav.classList.contains('more'),
           scrolls: nav.scrollWidth > nav.clientWidth + 2 };
}"""


def problems(width, m):
    found = []
    t = m["top"]
    if m["wide"] > width + 1:
        found.append(f"{m['wide']}px wide")
    if width > 1080:
        if round(t["h"]) != 72:
            found.append(f"header {t['h']}px, not 72")
        if not (m["gh"] and m["cta"] and m["cta"]["x"] < m["gh"]["x"]):
            found.append("the pill is not before GitHub on one row")
        if m["nav"]["y"] + 1 < m["brand"]["y"] or m["nav"]["y"] > m["brand"]["y"] + 1:
            found.append("links not on the name's row")
    else:
        if m["nav"]["y"] < m["brand"]["y"] + m["brand"]["h"]:
            found.append("links not on a row of their own")
        if m["gh"]:
            found.append("GitHub shown")
        if m["cta"] and m["cta"]["x"] > m["nav"]["x"] + 1:
            found.append("the pill is not first")
        if m["more"] != m["scrolls"]:
            found.append("the fading edge does not follow the row's scroll")
    if m["section"] and m["eyebrow"] and width > 860 and round(m["eyebrow"]["y"] - m["section"]["y"]) != 88:
        found.append(f"section rhythm {m['eyebrow']['y'] - m['section']['y']}px, not 88")
    if m["eyebrow"] and width >= 1280 and round(m["eyebrow"]["w"]) != 1180:
        found.append(f"content {m['eyebrow']['w']}px, not 1180")
    return found


async def main(site, paths):
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=site))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/"
    failures = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=os.environ.get("PLAYWRIGHT_CHROMIUM") or None)
        for width, height, phone in ((1280, 900, False), (768, 900, False), (390, 844, True)):
            context = await browser.new_context(viewport={"width": width, "height": height}, is_mobile=phone,
                                                has_touch=phone, locale="en-US", reduced_motion="reduce")
            page = await context.new_page()
            for path in paths:
                await page.goto(base + path, wait_until="load")
                found = problems(width, await page.evaluate(MEASURE))
                failures += [f"{width}px /{path}: {f}" for f in found]
            await context.close()
        await browser.close()
    print("\n".join(failures) or f"chrome layout: {len(paths)} page(s) on 3 screens, 0 problem(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    sys.exit(asyncio.run(main(sys.argv[1], sys.argv[2:] or ["", "inner/"])))
