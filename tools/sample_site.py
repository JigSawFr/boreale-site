#!/usr/bin/env python3
"""The library's reference pages (README.md): a sample home page and an inner
page, built with Site.header(), Site.sky(), Site.footer() and the v4 chrome
(assets/chrome.css, assets/chrome.js), in the fifteen languages. Not shipped
to a site: it is how the library's own tests and tools/site_layout.py see the
chrome, and how to read what a site's template does.

    tools/sample_site.py <out-dir>
    tools/site_layout.py <out-dir>

The texts are placeholders, in English in every language (the common ones,
i18n/, are translated); the sample's look beyond the chrome is
tools/sample/site.css, a hero and nothing else.
"""
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import boreale_site as boreale  # noqa: E402

HERE = Path(__file__).resolve().parent
URL = "https://sample.example.org/"
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; font-src 'self'; img-src 'self' data:; "
       f"connect-src 'self' {boreale.UMAMI_GATEWAY}; manifest-src 'self'; base-uri 'none'; form-action 'none'")
TEXTS = {
    "nav_features": "Features", "nav_install": "Install", "nav_docs": "Docs", "nav_try": "Try it",
    "hero_eyebrow": "A sample site", "hero_title": "One header, <em>one look</em>",
    "hero_text": "Placeholder words under a sky, to see the chrome the sites share.",
    "pill": "v1.2.3 · Oct 31, 2026", "features": "Features", "features_lead": "What the chrome carries, nothing else.",
    "install": "Install", "cta_title": "Ready when you are", "cta_text": "A closing band, as the sites' pages end.",
    "inner_title": "An inner page", "inner_text": "A page under the quieter sky.",
    "footer_license": "Free software, a sample. Свободнораспространяемоепрограммноеобеспечениесоткрытымкодом", "footer_project": "Sample", "footer_fine": "A sample, not a site.",
    "card_a": "First card", "card_b": "Second card", "card_c": "Third card",
    "card_text": "Under the pointer, the edge lights up.",
}
ICON = ('<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.8" '
        'stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="8"/><path d="M12 8v4l3 2"/></svg>')


def page(site, language, catalog, home, inner):
    """One page of the sample in `language`: the home page or the inner one."""
    code = boreale.folder(language)
    root = "../" * code.count("/") if not inner else "../" * (code.count("/") + 1)
    base = f"{root}{code}"  # the language's home, from this page
    path = "inner/" if inner else ""
    t = {**TEXTS, **catalog}
    header = site.header(language, catalog, root, path,
                         links=[("nav_features", f"{base}#features"), ("nav_docs", f"{base}inner/")],
                         cta=("nav_try", f"{base}#install"), github="https://github.com/JigSawFr/boreale-site",
                         current="nav_docs" if inner else None, label="Sample")
    if home:
        hero = f"""  <section class="hero">
    <div class="hero-text">
      <p class="pill-eyebrow"><a href="{base}#install">{t['pill']}</a></p>
      <p class="eyebrow">{t['hero_eyebrow']}</p>
      <h1>{t['hero_title']}</h1>
      <p class="lede">{t['hero_text']}</p>
      <div class="actions">
        <a class="button primary" href="#install">{t['nav_install']}</a>
        <a class="button" href="{base}inner/">{t['nav_docs']}</a>
      </div>
    </div>
  </section>"""
        cards = "\n".join(f'      <li class="card">{ICON}<h3>{t[k]}</h3><p>{t["card_text"]}</p></li>'
                          for k in ("card_a", "card_b", "card_c", "card_a", "card_b", "card_c"))
        body = f"""    <section class="section" id="features">
      <p class="eyebrow">{t['features']}</p>
      <h2>{t['features']}</h2>
      <ul class="cards">
{cards}
      </ul>
    </section>
    <section class="section" id="install">
      <div class="section-head"><p class="eyebrow">{t['install']}</p><h2>{t['install']}</h2><p>{t['features_lead']}</p></div>
      <p><a href="https://example.org/docs">example.org</a></p>
    </section>
    <div class="band" id="end">
      <div><h2>{t['cta_title']}</h2><p>{t['cta_text']}</p></div>
      <a class="button primary" href="#features">{t['nav_try']}</a>
    </div>"""
    else:
        hero = f"""  <section class="hero hero-inner">
    <h1>{t['inner_title']}</h1>
    <p class="lede">{t['inner_text']}</p>
  </section>"""
        body = f"""    <section class="section narrow"><h2>{t['inner_title']}</h2><p>{t['inner_text']}</p></section>"""
    footer = site.footer(language, catalog, root,
                         columns=[(t["footer_project"], [(t["nav_features"], f"{base}#features"), ("GitHub", "https://github.com/JigSawFr/boreale-site")])],
                         about=[t["footer_license"]], fine=t["footer_fine"])
    title = f"{t['inner_title'] if inner else 'Sample'} · {site.name}"
    return f"""<!doctype html>
<html lang="{boreale.html_lang(language)}"{'' if inner else ' data-first-visit'}>
<head>
<meta charset="utf-8">
<meta name="referrer" content="no-referrer">
<meta http-equiv="Content-Security-Policy" content="{CSP}">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title}</title>
<meta name="description" content="The library's sample page.">
<meta name="theme-color" content="#0b1424">
{site.indexing(language, path)}
<link rel="preload" href="{root}assets/fonts/sora.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="{root}assets/fonts/figtree.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="{root}assets/boreale.css">
<link rel="stylesheet" href="{root}assets/chrome.css">
<link rel="stylesheet" href="{root}assets/site.css">
<script src="{root}assets/lang.js"></script>
<script src="{root}assets/boreale.js" defer></script>
<script src="{root}assets/chrome.js" defer></script>
{site.audience(root)}
</head>
<body>
{site.skip(catalog)}
{site.sky(home=home)}
  {header}
{hero}
</div>
<main id="main">
{body}
</main>
{footer}
</body>
</html>
"""


def build(out: Path) -> boreale.Site:
    """The sample in `out`, in every language; its Site."""
    site = boreale.Site("playguard", URL)
    common = boreale.common_catalogs()
    for language in boreale.CODES:
        catalog = {**TEXTS, **common[language]}
        for inner in (False, True):
            target = out / boreale.folder(language) / ("inner/" if inner else "") / "index.html"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(site.links_out(page(site, language, catalog, not inner, inner)), encoding="utf-8")
    (out / "assets").mkdir(exist_ok=True)
    shutil.copy2(HERE / "sample" / "site.css", out / "assets" / "site.css")
    boreale.copy_assets(out)
    return site


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    build(Path(sys.argv[1]))
