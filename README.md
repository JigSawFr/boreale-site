# boreale-site

What Boréale's websites share — [boreale.dev](https://boreale.dev/?utm_source=github&utm_medium=readme) and its
sub-domains: [guard.](https://guard.boreale.dev/?utm_source=github&utm_medium=readme),
[shelf.](https://shelf.boreale.dev/?utm_source=github&utm_medium=readme), [aurore.](https://aurore.boreale.dev/?utm_source=github&utm_medium=readme),
[atlas.](https://atlas.boreale.dev/?utm_source=github&utm_medium=readme), [lantern.](https://lantern.boreale.dev/?utm_source=github&utm_medium=readme) —
kept once, so that a rule or a site added changes in one place.

Each site has it as a git submodule, `library/boreale-site`, and keeps its own
pages, texts, `site.css` and `site.js`.

## What is here

| Path | What |
|---|---|
| `sites.json` | Boréale's sites, in the order and groups of the header's menu: `key`, `name`, `url`, `utm` (its `utm_source`), `soon`. `schema` 1; a reader treats another schema as no list and leaves unknown fields aside. |
| `i18n/<language>.json` | The texts every site uses (the menu of Boréale's sites, the language button), in the fifteen languages. A site's catalog does not repeat them: the build stops if it does. |
| `assets/` | Copied into each built site's `assets/`: the fonts (SIL Open Font License, the flags' CC-BY 4.0), each site's mark (`marks/`), Umami's tracker (`umami.js`), `lang.js`, `boreale.css` (the brand's colours and fonts, the language menu, the menu of Boréale's sites) and `boreale.js` (where the two menus open). A site that has one of them too stops the build. |
| `boreale_site/` | Python's standard library only: the languages (English as `en-US`, the consoles' and the apps' code), flags and dates, `fill()`, the two menus, the links out and their UTM tags (`Site`, `untagged()` for Markdown served as it is), the projects' latest versions from boreale.dev's `versions.json` (`latest_versions()`, `schema` 1), the common assets and catalogs; `boreale_site.check`, the checks every built site passes. |
| `tools/site_layout.py` | Each page on phones, a tablet and a desktop (Playwright), and axe-core against WCAG 2.2 AA (below). |

## In a site

```python
sys.path.insert(0, str(ROOT / "library" / "boreale-site"))
import boreale_site as boreale

site = boreale.Site("atlas", os.environ.get("SITE_URL"))  # its entry in sites.json
catalogs = boreale.catalogs(ROOT / "site" / "i18n")       # its texts and the common ones
...
values["switcher"] = site.switcher(language, catalog, root, boreale.latest_versions())
# or with the site's own wordmark and home: site.switcher(..., brand=..., home=...)
values["languages"] = site.languages(language, catalog, root, path)
values["audience"] = site.audience(root)                  # before_send="name": data-before-send, and so on
page = site.links_out(boreale.fill(template, values))
...
shutil.copytree(ROOT / "site" / "assets", out / "assets")
boreale.copy_assets(out)
```

Its template loads, in `<head>`:

```html
<link rel="stylesheet" href="{{root}}assets/boreale.css">
<link rel="stylesheet" href="{{root}}assets/site.css">
<script src="{{root}}assets/lang.js"></script>
<script src="{{root}}assets/boreale.js" defer></script>
```

A page that is not dark (a simulator's light theme) loads `boreale.css` too and
sets its own `color-scheme` and colours on `:root` after it: the two menus and
their buttons keep the night whatever the page around them.

### The language

`lang.js` keeps the language chosen in the header's menu (`boreale-lang` in
the browser's storage: the folder, `en-US` for English) and, in `<head>`
before the page is drawn:

- sends an English page that has a translation (its `<link rel="alternate"
  hreflang>`, or the home page marked `data-first-visit`) to the language
  chosen, at the same place (`?query#hash`);
- on a first visit, nothing chosen, sends the English home page
  (`data-first-visit`) to the browser's language when the site has it;
- choosing a language in the menu opens the page at the same `#hash` in it;
- the page not found, either one `404.html` per language's folder (the
  English one marked `data-lost="{{root}}"`, which sends to the others), or one
  `404.html` holding a `<div class="not-found" data-lang="…" lang="…">` per
  language (`data-lang` the code or the folder, the English one shown, the
  others `hidden`): the block of the address' folder, else the one chosen, else
  the browser's, with `<html lang>` and the title in it;
- `window.boreale.lang` (the folder chosen, or `null`) and
  `window.boreale.browser()` (the browser's folder, `null` for English) for the
  site's own scripts.

It never reads `document.referrer`: every page sends none. A site that kept the
choice under a key of its own moves it to `boreale-lang` once, in a script of
`<head>` that runs before `lang.js`.

### The checks

Its `tools/check_site.py` calls `boreale_site.check.pages()` and
`boreale_site.check_catalogs()` before its own checks:

```python
errors, count = check.pages(Path(out), site,
                            skip=("assets", "data"),      # folders not walked, wherever they are
                            apart=("simulator",),         # built apart: not walked, links into them not followed
                            tracker=os.environ.get("SITE_NOINDEX") != "1",   # a preview counts no one
                            base=os.environ.get("SITE_BASE"))  # where the root's 404.html is served
errors += boreale.check_catalogs(Path("site/i18n"), optional={"en-US": {"doc_untranslated"}})
```

`pages()` follows every link and image to the site (relative, from its root,
or the site's own address), and every `#anchor`, into the same page or another;
a `#fragment` holding a `/` is a view of a page's script (`explore/#steam/popular`).
A page that only sends its visitor on (`<meta http-equiv="refresh">`) needs
neither policy nor tracker, but sends no referrer either. An event handler
attribute (`onclick=`) is reported: the policy blocks it. `check_catalogs()`'s
`optional` keys, by language, may be left out or empty.

### The layout

The workflow checks the submodule out (`submodules: true`) and runs
`library/boreale-site/tools/site_layout.py <site-dir>`: every page on five
screens, axe on an iPhone (`SITE_AXE=<axe.min.js>`), the pages that send their
visitor on at once left out; wider than the screen, a script that throws, a
target under 24px, a field under 16px on a phone (iOS zooms) fail. A site of
many pages chooses fewer:

| Option | What |
|---|---|
| `--skip <dir>` | A folder not walked (`assets/` never is). |
| `--skip-page <glob>` | A page left out, its path matching (`[!f]*/docs/dev/*`; `404.html` when it is built for another path, `SITE_BASE`, and loads unstyled from the root). |
| `--extra <path>`, `--extra-if <dir>` | A page opened besides those found (a view behind a `#hash`), when `<dir>` is built. |
| `--wait load\|networkidle` | Measured at the page's load, or once its requests are done. |
| `--wide <glob>` | The pages the four other screens open too, by their path in each language (`''` the home page, `docs/config/`); the iPhone opens them all. Without it, every screen opens every page. |
| `--axe-english` | axe on the English pages and each other language's home page, not every page. |
| `--jobs <n>` | Pages open at once (`SITE_LAYOUT_JOBS`, 6 by default). |

`PLAYWRIGHT_CHROMIUM=<path>` points at a browser of its own.

## The rules it carries

- **Links out say nothing of the visit**: every page sends no referrer; a link
  to a third party has `rel="noreferrer"`; one to `boreale.dev`, its
  sub-domains or `github.com/JigSawFr` keeps the origin alone
  (`referrerpolicy="strict-origin"`), so GitHub's traffic insights still see
  where visits come from.
- **The audience**, counted by Umami Cloud without cookie: the tracker is
  served by each site, counts only from its own host, and a page's
  Content-Security-Policy may reach Umami's gateway and nothing else. A link
  to another of Boréale's sites carries `utm_source` (the site's `utm` in
  `sites.json`) and `utm_medium` (`nav`, `footer` or `link`); a link to the
  site itself or to anyone else carries none.
- **No e-mail address** on a page: contact goes through the repositories'
  issues, a security flaw through a private advisory.
- Nothing loaded from another site: no inline script or style, the fonts
  served with the site.

## Changing it

`python3 -m unittest discover -s tests` before a pull request. A change here
reaches a site when its submodule moves (Dependabot opens the pull request);
the site's own checks then run against it.

A site added: its entry in `sites.json`, its mark in `assets/marks/`, its
`sites_<key>` in the fifteen catalogs.
