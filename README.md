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
| `tools/site_layout.py` | Each page on phones, a tablet and a desktop (Playwright), and axe-core against WCAG 2.2 AA. |

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
values["audience"] = site.audience(root)
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

and its `tools/check_site.py` calls `boreale_site.check.pages()` and
`boreale_site.check_catalogs()` before its own checks. The workflow checks
the submodule out (`submodules: true`) and runs
`library/boreale-site/tools/site_layout.py`.

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
