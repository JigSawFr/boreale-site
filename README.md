# boreale-site

What Boréale's websites share — [boreale.dev](https://boreale.dev/?utm_source=github&utm_medium=readme) and its
sub-domains: [guard.](https://guard.boreale.dev/?utm_source=github&utm_medium=readme),
[shelf.](https://shelf.boreale.dev/?utm_source=github&utm_medium=readme), [aurore.](https://aurore.boreale.dev/?utm_source=github&utm_medium=readme),
[atlas.](https://atlas.boreale.dev/?utm_source=github&utm_medium=readme), [lantern.](https://lantern.boreale.dev/?utm_source=github&utm_medium=readme), [ha.](https://ha.boreale.dev/?utm_source=github&utm_medium=readme) —
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
| `assets/chrome.css`, `assets/chrome.js` | v4's page chrome, PlayGuard's look: the header, the sky, the container and the sections' rhythm, buttons, the pill, the card, the footer (below). Loaded after `boreale.css`; a site that does not load them is untouched. |
| `tools/sample_site.py`, `tools/sample/` | The reference pages (a home and an inner page, in the fifteen languages) built with the helpers. Not copied to a site. |
| `tools/chrome_layout.py` | The chrome's measures in a browser (72px header, two rows, 88px rhythm, 1180px) on the sample or a built site. |
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

## The page chrome (v4)

An addition: a site that loads neither file builds as before. A site that does
gives its content and nothing of the header, sky, buttons, cards or footer.

```python
header = site.header(language, catalog, root, path,
                     links=[("nav_features", f"{home}#features"), ("nav_docs", f"{home}docs/")],
                     cta=("nav_try", f"{home}simulator/"),      # the pill, in the aurora's gradient
                     github="https://github.com/JigSawFr/PlayGuard",
                     current="nav_docs")                          # aria-current="page" on that link
footer = site.footer(language, catalog, root,
                     columns=[(catalog["docs_title"], [(catalog["doc_start"], f"{home}docs/")])],
                     about=[catalog["footer_license"]], fine=catalog["footer_nintendo"])
```

```html
<link rel="stylesheet" href="{{root}}assets/boreale.css">
<link rel="stylesheet" href="{{root}}assets/chrome.css">
<link rel="stylesheet" href="{{root}}assets/site.css">
<script src="{{root}}assets/chrome.js" defer></script>
...
<body>
{{skip}}                     <!-- site.skip(catalog) -->
{{sky}}                      <!-- site.sky(home=True) opens <div class="sky sky-home"> and its canvas -->
  {{header}}
  {{hero}}
</div>
<main id="main">...</main>
{{footer}}
```

- **`Site.header(language, catalog, root, path, links, cta, github, current, label, latest, brand, home)`**:
  the name and the menu of Boréale's sites (`switcher()`), the nav, the languages
  (`languages()`). `links` are `(catalog key, href)` or `(key, href, {attributes})`
  (lang, hreflang, rel, class), `cta` the same, `github` an address. `label` is the
  nav's accessible name: **the site's name** unless given (a site that keeps its own
  "Main" text passes it; the library has no common one). Every link goes
  through `links_out()`: UTM tags to our sites (`utm_medium=nav`), `noreferrer` or
  `strict-origin` as the rule says; calling `links_out()` on the page again changes
  nothing. A phone gets two rows, the links on their own with a fading edge, the pill
  first and GitHub left to the footer (`chrome.css`, `chrome.js`).
- **`Site.sky(home=False, canvas=True, veils=True)`**: the sky's opening tag, which the page closes
  after the hero. The home page has the aurora (canvas, `chrome.js`) and the night's
  veils and stars under it. **Any other page opts out of the canvas** with
  `sky()` (the quieter sky, a line under it); a home that must stay still takes
  `sky(home=True, canvas=False)`. The veils and stars under a home's hero
  (`.sky-home:not(.no-veils) ~ main`) are left out with `veils=False` (the page not found). Nothing moves with `prefers-reduced-motion`, or while
  the sky is out of view.
- **`Site.footer(language, catalog, root, columns, about, fine, brand, support)`**: the
  project (mark, name, `about` lines, "A Boréale project"), the site's own `columns`
  (`[(heading, [(text, href) or (text, href, {attributes})])]`, texts ready for the page;
  the attributes (lang, hreflang, rel, class) go through the rules for links out), Boréale's sites **read from
  `sites.json`** (the others, in its order, and the legal notice, so a site added or ha
  appears everywhere), the support (`support=False` to leave it out), the fine print.
- `Site.skip(catalog)` is the skip link; `Site.anchor(href, label, medium, css, current)`
  one link by the same rules.
- Classes `chrome.css` provides: `.sky`, `.sky-home`, `.top`, `.brand`, `.nav`,
  `.nav-cta`, `.nav-gh`, `.settings`, `.wrap`, `.section` (`.narrow`), `.section-head`,
  `.eyebrow`, `.lede`, `.pill-eyebrow`, `.actions`, `.button` (`.primary`), `.band`,
  `.cards`/`.card` (with `.icon`, the pointer glow, the reveal), `.footer`, `.footer-fine`,
  `.sr`, `.skip`, and the tokens (`--bg`, `--surface`, `--text`, `--muted`, `--line`,
  `--accent`, `--gutter-l/r`, `--edge-l/r`, `--content`). What stays in a site's
  `site.css`: its hero, its mock visuals, its documentation, cards of its own kind
  (featured, small, with a screen), and any accent of its own.
- Texts: `chrome_skip`, `chrome_legal`, `chrome_support`, `chrome_part_of` are common
  (`i18n/`, fifteen languages); a catalog that has one stops the build.

`check.pages(..., chrome=True, bare=(), cta=True)` keeps a built page to it: one
`header.top` with the name's menu (popover), one `nav.nav` with an `aria-label`, the
pill (`cta=False`: at most one) before GitHub and after the page's links, at most one
link of the row `aria-current`, one site and one language (the page's `<html lang>`)
marked in the menus, the footer linking to every other site of `sites.json`, `chrome.css`
and `chrome.js` loaded, no `canvas#sky` without `.sky-home`. `bare` are globs of pages
without them (a simulator's). `tools/chrome_layout.py <site-dir> [page...]` measures it
in a browser; `tools/site_layout.py` (with axe) runs on the sample as on a site:

    python3 tools/sample_site.py /tmp/sample && python3 tools/site_layout.py /tmp/sample && python3 tools/chrome_layout.py /tmp/sample

### Moving a site to the chrome

1. `git submodule update --remote library/boreale-site`; add `chrome.css` after `boreale.css`
   and `chrome.js` (`defer`) to the template; the site's own `chrome.css`/`chrome.js`, if any,
   stop the build (`copy_assets`).
2. Replace the template's skip link, sky, `<header>` and `<footer>` with `site.skip()`,
   `site.sky()`, `site.header()`, `site.footer()`; the class `nav-try` becomes `nav-cta`,
   the home's `body.home` selectors (`.home main`) are `.sky-home ~ main`.
3. Delete from `site.css`: the tokens `--night-2`, `--dusk`, `--link`, `--bg`... `--gutter-*`, the
   reset (`*`, `html`, `body`, `a`, `h1-h3`, `:focus-visible`, `.sr`, `.skip`), `.sky*`, `.top`,
   `.brand`, `.nav*`, the 1080px and 860px header rules, `.eyebrow`, `.button*`, `.actions`,
   the pill (`.release-pill`/`.pill`, as `.pill-eyebrow`), `.section*`, `.band`, `.cards`/`.card`
   (base, glow, reveal), `.footer*`, the view-transition and reveal blocks.
4. Delete from `site.js`: the sky canvas, the nav's fading edge, the cards' pointer, the reveal.
5. Delete from the site's catalogs `skip`, the legal/support/"part of Boréale" texts that
   `chrome_*` replace, and the site's hand-written list of Boréale's sites in the footer.
6. In `tools/check_site.py`: `check.pages(..., chrome=True)`; drop the checks of the header's
   structure it carried.

### Layout notes (v4.1)

- **Gutters**: `.section` and `.band` carry the 16px gutters and the 1180px width themselves,
  so on a home `<main>` is a plain element holding them. On a page whose `<main class="wrap">`
  already has the gutters, `.wrap > .section` and `.wrap > .band` take none of their own, and a
  `.band` inside a `.section` neither. A **hero** (the site's own element) takes the header's edge
  (`--edge-l/r`, zero specificity: a rule of its own wins); it does not need `.wrap`. A rhythm that
  is deliberately not 88px: `tools/chrome_layout.py --rhythm-skip <page>`.
- **Mark**: `assets/marks/<key>.svg` is the family's mark, in the menu, the header (`brand=`
  default) and the footer; PlayGuard's is drawn at 1.3, as its site did, so a site drops its own.
- **Cards**: the icon beside the title and the 12px gap start at 860px (PlayGuard's) and only for a
  card with a direct `.icon` child; any other card stays a stack. `.card svg.icon` has its
  strokes (1.8, round, `currentColor`), the same as the sites' drawings carry.
- **Buttons**: the size is the page's (16.5px as PlayGuard's), `--button-size: 1rem` on `:root`
  for a site that wants 16px. A button's text turns aurora under the pointer, as a link (PlayGuard's).
  Beside a band's text, `.band-actions` stacks its buttons and takes the band's width on a phone.
- **Pill**: `.pill-eyebrow` styles its first link or span (not `.pill-more`); `.pill-eyebrow.caps`
  is in capitals; `<a class="pill-more">` beside it is the plain "more" link with its arrow.
- **Tokens a site sets on `:root`**: `--button-size`, `--cta-gap` (the pill's right margin on a
  phone, 0 by default). **Margins**: `class="reset-margins"` on `<body>` (or a container) takes the
  browser's margins off `p` and `h1`-`h3`, at zero specificity.
- **Footer**: its columns cannot be wider than the screen (`min-width: 0`, long words break; one
  column under 420px). `tools/chrome_layout.py <site> --languages` opens every page in the fifteen
  languages at 320px and 390px to keep it so.

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

## Reusable workflow

`.github/workflows/site.yml` is the part of a site's workflow that every site
copied: the checkout with its submodules, the build, the checks, the layout
check (Playwright 1.64.0 and axe-core 4.13.0, pinned here once, axe checked
against its hash) and the built folder kept as a Pages artifact. A site calls
it from its own `site.yml`:

```yaml
jobs:
  build:
    permissions: { contents: read, pages: read }   # a called workflow cannot raise them
    uses: JigSawFr/boreale-site/.github/workflows/site.yml@<sha> # v1.0.0
    with:
      build: python3 tools/build_site.py build
      check: python3 tools/check_site.py build
      pages_artifact: ${{ github.event_name != 'pull_request' }}
  deploy:
    needs: build
    if: needs.build.outputs.pages_artifact_id != ''
    runs-on: ubuntu-slim
    permissions: { pages: write, id-token: write }
    environment: { name: github-pages, url: "${{ steps.deploy.outputs.page_url }}" }
    concurrency: { group: pages, cancel-in-progress: false }
    steps:
      - id: deploy
        uses: actions/deploy-pages@368f82528645a54fb793d4d04e342629a3f51346 # v5.0.1
```

A called workflow runs in the caller's repository: its checkout is the
caller's and the layout check is the caller's `library/boreale-site`
(`library:` says where, `.` in this repository). The workflow file is the only
thing taken from here, so the two move apart: a `uses:` ref and a submodule
commit. Options are only ever added to the workflow and to `site_layout.py`,
never changed in meaning; a site that uses an option new in one of them moves
both.

### What stays in the caller

- **The triggers** (`paths`, `schedule`, `repository_dispatch`, `workflow_run`),
  the job's `if`, and **`concurrency`**: the group depends on the event, and
  the same group in both workflows would cancel the run itself.
- **The deployment** (`actions/deploy-pages`): the `github-pages`
  environment, `pages: write` and `id-token: write` are one repository's, and
  a site's previews (PlayGuard, PlayShelf publish pull requests under
  `pr-<number>/` from a `workflow_run`) deploy differently. It is a job of
  five lines that finds the artifact the called job kept, in the same run.
- Whatever builds the site and is not shared: a simulator, Doxygen, a data
  branch. It goes in `setup`, or in a job of its own whose result the called
  job downloads (`download_artifact`).

### Inputs

All optional. A list is a JSON array of strings in a string:
`wide: '["", "docs/config/"]'` (`""` is the home page).

| Input | Default | What |
|---|---|---|
| `library` | `library/boreale-site` | Where `tools/site_layout.py` is in the caller. |
| `ref`, `submodules`, `library_only`, `fetch_depth`, `filter`, `persist_credentials` | `""`, `true`, `false`, `1`, `""`, `false` | The checkout (`library_only`: of the submodules, only `library`; `fetch_depth: 0` is the history and tags; `filter: blob:none` skips old blobs). |
| `runs_on`, `timeout_minutes` | `ubuntu-26.04`, `20` | The runner and the job's timeout. |
| `download_artifact`, `download_path` | `""`, `.` | An artifact of this run to download first: a demo or simulator another job built, or the site itself for a check alone. |
| `apt` | `""` | Packages for `apt-get install`, separated by spaces. |
| `env` | `{}` | A JSON object of variables for every script below. A value from the event goes through `toJSON()`: `env: ${{ format('{{"TITLE": {0}}}', toJSON(github.event.pull_request.title)) }}`. `GITHUB_*` and `RUNNER_*` names are refused. |
| `github_token` | `false` | The job's read-only token as `GITHUB_TOKEN` in `setup`, `build`, `check` and `gate` (releases read without the API's anonymous limit). |
| `address` | `""` | `url` sets `SITE_URL` and `SITE_NOINDEX` (a pull request's build is `1`) from the Pages API (custom domain, else `<owner>.github.io/<repo>/`); `preview` also `SITE_BASE`, `MAIN_SITE` and `pr-<number>/` for a pull request. |
| `setup`, `build`, `check` | `""` | Scripts, in that order, each a file run by `bash -e` in the checkout: they are never inlined into the workflow, so an expression in them was read by the caller. `check` is for what needs the built folder (links, catalogs, CSP, a conformance suite). |
| `directory` | `build` | The built site. |
| `layout` | `true` | The layout check on `directory`. |
| `skip`, `skip_page`, `extra`, `wide` | `[]` | `--skip`, `--skip-page`, `--extra`, `--wide` (above). |
| `extra_if`, `wait`, `axe_english`, `jobs` | `""`, `load`, `false`, `0` | `--extra-if`, `--wait`, `--axe-english`, `--jobs` (0: the check's own). |
| `layout_timeout_minutes` | `10` | The check's timeout, apart from installing its browser (20). |
| `pages_artifact` | `false` | Keep `directory` as the Pages artifact. |
| `gate` | `""` | A script that writes `publish=true` to `$GITHUB_OUTPUT` to keep the Pages artifact (a scheduled build whose site is the one served says nothing). Run only when `pages_artifact` is true. |
| `include_hidden` | `true` | `.nojekyll` and `.well-known/` in the artifacts. |
| `artifact_name`, `artifact_retention_days` | `""`, `14` | Also keep `directory` as a plain artifact (a pull request's preview). |

Output: `pages_artifact_id`, empty when no Pages artifact was kept. A deploy
job tests it, so a pull request, a skipped gate and a build with
`pages_artifact: false` all end the same way.

Python is the runner's `python3` (3.14 on `ubuntu-26.04`): the sites' tools
use the standard library and the Markdown and YAML modules `apt` installs,
which a `setup-python` would hide. Node is not needed here; a site that takes
screenshots with it installs it in its own job.

### A site that builds elsewhere

PlayGuard, PlayShelf and Aurore build a simulator or a demo that takes
minutes. Their job stays; what is shared is the check, in a job that
downloads what the first one kept:

```yaml
  layout:
    needs: build
    permissions: { contents: read, pages: read }
    uses: JigSawFr/boreale-site/.github/workflows/site.yml@<sha> # v1.0.0
    with:
      library_only: true
      download_artifact: site
      download_path: out
      directory: out
      skip: '["simulator"]'
      skip_page: '["404.html"]'
      axe_english: true
```

### Moving a site to it

1. In the site's `site.yml`, replace the steps the sections above name by one
   `uses:` job; keep the triggers, `concurrency`, the job's `if` and the
   deploy; grant `pages: read` to the job (the called job asks for it).
2. The job's check run is named `<job> / site`. Nothing in the sites'
   rulesets requires a check named after these jobs (2026-10-31: PlayGuard
   requires `host-tests`, `desktop-smoke`, `conventional-title`, `switch`);
   look again before moving a job that is required.
3. `workflow_run` watchers name the caller's workflow, which does not change.

### The ref

Pin by commit, with the version in a comment, as every action in the sites'
workflows: `@3f2a… # v1.0.0`. Tags are `vX.Y.Z`, cut from main when the
workflow's behaviour changes and never moved; there is no floating `v1`
(a change nobody reviewed in the site's own pull request is how a check
starts failing in seven places at once). Dependabot's `github-actions`
ecosystem updates a reusable workflow's `uses:` as it does an action's: the
SHA and the version comment together, one pull request per site, each run by
the site's own checks. Add it to the site's `.github/dependabot.yml` (the
`gitsubmodule` entry for `library/boreale-site` is another pull request, on
its own schedule). The library's own CI runs `site.yml` on the sample site
(`test-site-workflow.yml`), so a tag is cut from a main whose workflow
passed.

## Changing it

`python3 -m unittest discover -s tests` before a pull request. A change here
reaches a site when its submodule moves (Dependabot opens the pull request);
the site's own checks then run against it.

A site added: its entry in `sites.json`, its mark in `assets/marks/`, its
`sites_<key>` in the fifteen catalogs.
