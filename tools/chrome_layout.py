#!/usr/bin/env python3
"""The v4 chrome's measures in a browser (README.md), on the reference pages
(tools/sample_site.py) or on a built site: what PlayGuard's header is, kept.

    tools/chrome_layout.py <site-dir> [<page>...] [--languages] [--rhythm-skip <page>]... [--no-cta]

At 1280px: the header is 72px, on one row, the pill before GitHub, the content
1180px wide, the first section's content 88px under its top (its own padding
and the first element's margin, whatever that element is). At 768px and 390px: two rows, the
links on the second, the pill first, GitHub hidden, the fading edge only when
the row scrolls, nothing wider than the screen. The content's width is the
first section's own box less its padding. `<page>`: a path from the site's
root ('' its home page, `docs/`); none given, the home page. A page that is
not built is reported, not a crash. `--rhythm-skip <page>`: a page whose first
section deliberately has another rhythm than 88px (its hero is under it).
`--no-cta`: a site whose header has no pill (boreale.dev): the pill is not
looked for, GitHub is still after the links.
`--languages`: every page in each of the fifteen languages at 320px and 390px,
for what is wider than the screen (a long word in a column), which is what the
longest languages (Russian, German) find. A page a language does not have (an
English-only page, a root 404.html) answers 404: it is skipped and listed at
the end, not a failure.
PLAYWRIGHT_CHROMIUM=<path> for a browser of its own.
"""
import argparse
import asyncio
import functools
import http.server
import os
import sys
import threading
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from boreale_site import LANGUAGES  # noqa: E402

MEASURE = """() => {
  const box = (s) => { const e = document.querySelector(s); if (!e || !e.getClientRects().length) return null;
    const r = e.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height }; };
  const nav = document.querySelector('.top .nav');
  const sec = document.querySelector('main .section:not(.narrow)');
  // The first section's own rhythm: its top to its first element's top (its
  // padding and that element's margin), not to the first eyebrow of the page.
  const first = document.querySelector('main .section');
  const lead = first && first.firstElementChild && first.getClientRects().length
    ? first.firstElementChild.getBoundingClientRect().y - first.getBoundingClientRect().y : null;
  const inner = sec ? (() => { const c = getComputedStyle(sec); return sec.getBoundingClientRect().width - parseFloat(c.paddingLeft) - parseFloat(c.paddingRight); })() : null;
  const wideOnes = [];
  if (document.documentElement.scrollWidth > innerWidth + 1) {
    for (const e of document.querySelectorAll('body *')) {
      if (e.getBoundingClientRect().right > innerWidth + 1 && wideOnes.length < 3) wideOnes.push(e.tagName.toLowerCase() + ' "' + (e.textContent || '').trim().slice(0, 40) + '"');
    }
  }
  return { top: box('.top'), brand: box('.top .brand'), nav: box('.top .nav'), cta: box('.nav-cta'), gh: box('.nav-gh'),
           settings: box('.settings'), section: box('main .section'), lead,
           wide: document.documentElement.scrollWidth, wideOnes, inner, screen: innerWidth, more: !!nav && nav.classList.contains('more'),
           scrolls: !!nav && nav.scrollWidth > nav.clientWidth + 2 };
}"""


def problems(width, m, rhythm=True, header=True, cta=True):
    found = []
    t = m["top"]
    if m["wide"] > width + 1:
        found.append(f"{m['wide']}px wide: " + ", ".join(m["wideOnes"]))
    if not header or not t:
        return found
    if width > 1080:
        if round(t["h"]) != 72:
            found.append(f"header {t['h']}px, not 72")
        if cta and not (m["gh"] and m["cta"] and m["cta"]["x"] < m["gh"]["x"]):
            found.append("the pill is not before GitHub on one row")
        if not cta and m["cta"]:
            found.append("a pill, on a site without one")
        if m["nav"]["y"] + 1 < m["brand"]["y"] or m["nav"]["y"] > m["brand"]["y"] + 1:
            found.append("links not on the name's row")
    else:
        if m["nav"]["y"] < m["brand"]["y"] + m["brand"]["h"]:
            found.append("links not on a row of their own")
        if m["gh"]:
            found.append("GitHub shown")
        if cta and m["cta"] and m["cta"]["x"] > m["nav"]["x"] + 1:
            found.append("the pill is not first")
        if not cta and m["cta"]:
            found.append("a pill, on a site without one")
        if m["more"] != m["scrolls"]:
            found.append("the fading edge does not follow the row's scroll")
    if rhythm and m["section"] and m["lead"] is not None and width > 860 and round(m["lead"]) != 88:
        found.append(f"section rhythm {m['lead']}px, not 88")
    if m["inner"] and width >= 1280 and round(m["inner"]) != 1180:
        found.append(f"content {m['inner']}px, not 1180")
    return found


async def main(site, paths, languages, skip_rhythm, cta=True):
    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *args):
            pass
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Quiet, directory=site))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_address[1]}/"
    failures = []
    skipped = []  # pages a language does not have (404), listed, not failed

    def built(path):
        target = Path(site) / path
        return (target / "index.html").is_file() if path == "" or path.endswith("/") else target.is_file()

    present = []
    for path in paths:
        if built(path):
            present.append(path)
        else:
            failures.append(f"/{path}: not built in {site}")
    folders = [d + "/" if d else "" for _, d, _, _ in LANGUAGES]
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=os.environ.get("PLAYWRIGHT_CHROMIUM") or None)
        # (width, height, phone, pages, everything measured): the header's rules
        # on three screens, a column's overflow on the narrowest in each language.
        runs = [(1280, 900, False, present, True), (768, 900, False, present, True), (390, 844, True, present, True)]
        if languages:
            every = [f + path for f in folders for path in present]
            runs += [(320, 640, True, every, False), (390, 844, True, every, False)]
        for width, height, phone, pages, full in runs:
            context = await browser.new_context(viewport={"width": width, "height": height}, is_mobile=phone,
                                                has_touch=phone, locale="en-US", reduced_motion="reduce")
            page = await context.new_page()
            for path in pages:
                response = await page.goto(base + path, wait_until="load")
                if response is not None and response.status >= 400:
                    # A language folder without this page (English only, a root 404.html).
                    if path not in skipped:
                        skipped.append(path)
                    continue
                found = problems(width, await page.evaluate(MEASURE), rhythm=path not in skip_rhythm, header=full, cta=cta)
                failures += [f"{width}px /{path}: {f}" for f in found]
            await context.close()
        await browser.close()
    note = (f"{len(skipped)} page(s) answered 404 and were skipped: " + ", ".join("/" + path for path in skipped[:12])
            + (", ..." if len(skipped) > 12 else "")) if skipped else ""
    if note:
        print(note)
    print("\n".join(failures) or f"chrome layout: {len(present)} page(s) on 3 screens"
          + (f", {len(present) * len(folders) - len(skipped)} more at 320px and 390px in each language" if languages else "") + ", 0 problem(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    args = argparse.ArgumentParser(description="The v4 chrome's measures in a browser.")
    args.add_argument("site")
    args.add_argument("pages", nargs="*")
    args.add_argument("--languages", action="store_true")
    args.add_argument("--rhythm-skip", action="append", default=[])
    args.add_argument("--no-cta", action="store_true", help="the header has no pill")
    options = args.parse_args()
    sys.exit(asyncio.run(main(options.site, options.pages or [""], options.languages, options.rhythm_skip, not options.no_cta)))
