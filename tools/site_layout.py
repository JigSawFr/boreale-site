#!/usr/bin/env python3
"""A website's layout on phones, a tablet and a desktop (README.md), the
same check for each of Boréale's sites.

Serves a built site (its tools/build_site.py <out-dir>) and opens each page in
headless Chromium (Playwright), failing when one:

- is wider than the screen (a long word, a table, a header that does not
  fit): the page scrolls sideways;
- throws (site.js, lang.js);
- has a target under 24px a finger cannot hit (WCAG 2.2, 2.5.8);
- has a field under 16px on a phone (iOS zooms into it when it is touched).

Every page on a small phone (320), an iPhone (402x874), a phone in landscape
(874x402), a tablet (1024) and a desktop (1440); images and videos not
loaded (their boxes are in the pages), the pages that send their visitor on
at once (<meta http-equiv="refresh">) left out. With SITE_AXE set to
axe-core's axe.min.js, also what axe finds against WCAG 2.2 A and AA on an
iPhone, on every page.

A site of many pages chooses fewer: --wide, the pages the other screens see
besides the iPhone, which sees them all; --axe-english, axe on the English
pages and each other language's home page alone (their texts, not their
layout nor their colours, differ).

Usage:

    library/boreale-site/tools/site_layout.py <site-dir> [--skip <dir>]...
        [--skip-page <glob>]... [--extra <path>]... [--extra-if <dir>]
        [--wait load|networkidle] [--wide <glob>]... [--axe-english]
        [--jobs <n>]

--skip: a folder of the site not walked for pages (assets/ always is);
--skip-page: a page left out, its path (fr/docs/dev/) matching the glob;
--extra: a page opened besides those found (an explorer's view behind a
#hash), only when <site-dir>/<dir> of --extra-if is there (its data built);
--wait: when a page is measured, at its load (the default) or once its
requests are done (a page that reads its data);
--wide: a page the small phone, the phone in landscape, the tablet and the
desktop open too, its path in its language (docs/config/, '' for the home
page) matching the glob, in each language; without it, they open every page;
--axe-english: axe on every English page and each other language's home
page, rather than every page;
--jobs: pages open at once (SITE_LAYOUT_JOBS, 6 by default).
Needs Playwright for Python with Chromium, PLAYWRIGHT_CHROMIUM=<path> for a
browser of its own.
"""
import argparse
import asyncio
import fnmatch
import functools
import http.server
import os
import re
import sys
import threading
from pathlib import Path

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from boreale_site import LANGUAGES  # noqa: E402

ARGS = argparse.ArgumentParser(description="A built site's layout on phones, a tablet and a desktop.")
ARGS.add_argument("site")
ARGS.add_argument("--skip", action="append", default=[])
ARGS.add_argument("--skip-page", action="append", default=[])
ARGS.add_argument("--extra", action="append", default=[])
ARGS.add_argument("--extra-if")
ARGS.add_argument("--wait", choices=["load", "networkidle"], default="load")
ARGS.add_argument("--wide", action="append", default=[])
ARGS.add_argument("--axe-english", action="store_true")
ARGS.add_argument("--jobs", type=int, default=int(os.environ.get("SITE_LAYOUT_JOBS") or 6))
OPTIONS = ARGS.parse_args()
SITE = OPTIONS.site
AXE = os.environ.get("SITE_AXE")
AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"]
# (name, width, height, a phone): the iPhone first, which sees every page.
SCREENS = [("iPhone", 402, 874, True), ("small phone", 320, 640, True), ("phone in landscape", 874, 402, True),
           ("tablet", 1024, 768, False), ("desktop", 1440, 900, False)]
FOLDERS = [d for _, d, _, _ in LANGUAGES if d]
# Images and videos not loaded: their boxes are in the pages.
MEDIA = "**/*.{png,webp,jpg,jpeg,gif,mp4,webm}"
REFRESH = re.compile(r"<meta\b[^>]*http-equiv=[\"']?refresh", re.IGNORECASE)

# What a page reports: how wide it is, what is wider than the screen (its
# width: on a phone, the page's viewport widens to the page), the targets
# under 24px, the fields under 16px.
MEASURE = """(screen) => {
  const out = { width: document.documentElement.scrollWidth, wide: [], small: [], fields: [] };
  if (out.width > screen + 1) {
    // The widest elements not inside something that scrolls on its own.
    for (const e of document.querySelectorAll('body *')) {
      if (e.getBoundingClientRect().right <= screen + 1) continue;
      let a = e.parentElement, clipped = false;
      for (; a && a !== document.body; a = a.parentElement) {
        if (getComputedStyle(a).overflowX !== 'visible') { clipped = true; break; }
      }
      if (!clipped) out.wide.push(`${e.tagName.toLowerCase()} "${(e.textContent || '').trim().slice(0, 40)}"`);
      if (out.wide.length >= 3) break;
    }
  }
  for (const e of document.querySelectorAll('a[href], button')) {
    const r = e.getBoundingClientRect();
    if (r.width && r.height && (r.width < 24 || r.height < 24) && getComputedStyle(e).display !== 'inline')
      out.small.push(`${e.tagName.toLowerCase()} "${(e.textContent || '').trim().slice(0, 30)}"`);
  }
  for (const e of document.querySelectorAll('input, select, textarea')) {
    if (['checkbox', 'radio', 'hidden', 'range', 'color'].includes(e.type) || !e.getClientRects().length) continue;
    if (parseFloat(getComputedStyle(e).fontSize) < 16) out.fields.push(e.id || e.name || e.tagName.toLowerCase());
  }
  return out;
}"""


def in_language(path):
    """A page's path in its language: its folder (fr/, zh-hant/) removed."""
    first, _, rest = path.partition("/")
    return rest if first in FOLDERS else path


def english(path):
    """An English page, or another language's home page (fr/)."""
    return path.partition("/")[0] not in FOLDERS or in_language(path).partition("#")[0] == ""


def pages():
    """Every page found (but those that send their visitor on and those
    left out), and the --extra ones."""
    found = []
    for root, dirs, files in os.walk(SITE):
        dirs[:] = [d for d in dirs if d != "assets" and d not in OPTIONS.skip]
        for f in files:
            if not f.endswith(".html"):
                continue
            file = os.path.join(root, f)
            with open(file, encoding="utf-8") as text:
                if REFRESH.search(text.read()):
                    continue
            path = os.path.relpath(file, SITE).replace(os.sep, "/").removesuffix("index.html")
            if not any(fnmatch.fnmatchcase(path, glob) for glob in OPTIONS.skip_page):
                found.append(path)
    extra = not OPTIONS.extra_if or os.path.isdir(os.path.join(SITE, OPTIONS.extra_if))
    return sorted(found) + (OPTIONS.extra if extra else [])


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve():
    handler = functools.partial(Quiet, directory=SITE)
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{server.server_address[1]}/"


async def each(context, paths, visit):
    """`visit(page, path)` for each path, OPTIONS.jobs pages at once."""
    queue = list(reversed(paths))

    async def worker():
        page = await context.new_page()
        while queue:
            await visit(page, queue.pop())
        await page.close()

    await asyncio.gather(*(worker() for _ in range(max(1, min(OPTIONS.jobs, len(paths))))))


async def check(browser, base, screen, paths, failures):
    name, width, height, phone = screen
    # In English, so the first visit stays on the page asked for (assets/lang.js).
    context = await browser.new_context(viewport={"width": width, "height": height}, is_mobile=phone,
                                        has_touch=phone, locale="en-US", reduced_motion="reduce")
    await context.route(MEDIA, lambda route: route.abort())
    found = {}

    async def visit(page, path):
        errors = []
        thrown = lambda e: errors.append(str(e))  # noqa: E731
        page.on("pageerror", thrown)
        await page.goto(base + path, wait_until=OPTIONS.wait)
        m = await page.evaluate(MEASURE, width)
        page.remove_listener("pageerror", thrown)
        where = f"{name} ({width}px) /{path}"
        problems = []
        if m["width"] > width + 1:
            problems.append(f"{where}: {m['width']}px wide: " + ", ".join(m["wide"]))
        if m["small"]:
            problems.append(f"{where}: targets under 24px: {', '.join(m['small'])}")
        if phone and m["fields"]:
            problems.append(f"{where}: fields under 16px (iOS zooms into them): {', '.join(m['fields'])}")
        problems.extend(f"{where}: {e}" for e in errors)
        found[path] = problems

    await each(context, paths, visit)
    await context.close()
    failures.extend(p for path in paths for p in found.get(path, []))


async def accessible(browser, base, paths, failures):
    name, width, height, phone = SCREENS[0]
    # axe is a script added to the page, which the site's CSP refuses.
    context = await browser.new_context(viewport={"width": width, "height": height}, is_mobile=phone,
                                        has_touch=phone, locale="en-US", bypass_csp=True, reduced_motion="reduce")
    await context.route(MEDIA, lambda route: route.abort())
    source = open(AXE, encoding="utf-8").read()
    found = {}

    async def visit(page, path):
        await page.goto(base + path, wait_until=OPTIONS.wait)
        await page.add_script_tag(content=source)
        violations = await page.evaluate("""(tags) => axe.run(document, {
            runOnly: { type: 'tag', values: tags }, resultTypes: ['violations'] })
          .then((r) => r.violations.map((v) => ({ id: v.id, help: v.help,
            where: v.nodes.slice(0, 3).map((n) => n.target.join(' ')) })))""", AXE_TAGS)
        found[path] = [f"axe /{path}: {v['id']} ({v['help']}): {', '.join(v['where'])}" for v in violations]

    await each(context, paths, visit)
    await context.close()
    failures.extend(p for path in paths for p in found.get(path, []))


async def main():
    every = pages()
    wide = [p for p in every if any(fnmatch.fnmatchcase(in_language(p), g) for g in OPTIONS.wide)] \
        if OPTIONS.wide else every
    axe = [p for p in every if english(p)] if OPTIONS.axe_english else every
    base = serve()
    failures = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=os.environ.get("PLAYWRIGHT_CHROMIUM") or None)
        for screen in SCREENS:
            await check(browser, base, screen, every if screen is SCREENS[0] else wide, failures)
        if AXE:
            await accessible(browser, base, axe, failures)
        await browser.close()
    for f in failures:
        print(f"::error::{f}" if os.environ.get("GITHUB_ACTIONS") else f)
    others = f"{len(every)} pages on {len(SCREENS)} screens" if wide is every else \
        f"{len(every)} pages on an iPhone, {len(wide)} on each of {len(SCREENS) - 1} other screens"
    print(f"site layout: {others}" + (f", {len(axe)} with axe" if AXE else "") + f", {len(failures)} problem(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
