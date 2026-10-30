"""boreale_site's rules: links out, UTM tags, sites.json, catalogs, checks.

    python3 -m unittest discover -s tests
"""
import json
import os
import sys
import tempfile
import unittest
from datetime import date
from unittest import mock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import boreale_site as boreale  # noqa: E402
from boreale_site import check  # noqa: E402


class Links(unittest.TestCase):
    def test_own_site(self):
        for url in ("https://boreale.dev/", "https://shelf.boreale.dev/fr/", "https://github.com/JigSawFr/PlayShelf",
                    "https://github.com/jigsawfr/boreale/releases", "https://github.com/JigSawFr"):
            self.assertTrue(boreale.own_site(url), url)
        for url in ("https://store.example.com/app/1", "https://github.com/jigsawfrx/x",
                    "https://github.com/someone/JigSawFr", "https://gist.github.com/JigSawFr/1",
                    "https://boreale.dev.example.com/", "https://notboreale.dev/", "http://boreale.dev/"):
            self.assertFalse(boreale.own_site(url), url)

    def test_utm(self):
        site = boreale.Site("atlas")
        self.assertEqual(site.utm("https://boreale.dev/fr/", "nav"),
                         "https://boreale.dev/fr/?utm_source=atlas&amp;utm_medium=nav")
        # This site itself: the tags a text came with go.
        self.assertEqual(site.utm("https://atlas.boreale.dev/?utm_source=github&amp;utm_medium=readme", "link"),
                         "https://atlas.boreale.dev/")
        # Anyone else, GitHub included: as it is.
        for url in ("https://github.com/JigSawFr/Atlas", "https://example.org/?a=1"):
            self.assertEqual(site.utm(url, "footer"), url)

    def test_links_out(self):
        site = boreale.Site("boreale")
        page = ('<header><a href="https://guard.boreale.dev/">G</a></header><main>'
                '<a href="https://example.org/" rel="external">E</a></main>'
                '<footer><a href="https://github.com/JigSawFr" rel="noreferrer">GH</a></footer>')
        out = site.links_out(page)
        self.assertIn('href="https://guard.boreale.dev/?utm_source=boreale&amp;utm_medium=nav" '
                      'referrerpolicy="strict-origin"', out)
        self.assertIn('href="https://example.org/" rel="external noreferrer"', out)
        self.assertIn('href="https://github.com/JigSawFr" referrerpolicy="strict-origin"', out)

    def test_untagged(self):
        site = boreale.Site("playguard")
        text = ("[docs](https://guard.boreale.dev/fr/docs/?utm_source=github&utm_medium=readme) "
                "[home](https://boreale.dev/?utm_source=github&utm_medium=readme) https://guard.boreale.dev/")
        self.assertEqual(site.untagged(text), "[docs](https://guard.boreale.dev/fr/docs/) "
                         "[home](https://boreale.dev/?utm_source=github&utm_medium=readme) https://guard.boreale.dev/")

    def test_site_url(self):
        site = boreale.Site("atlas", "https://jigsawfr.github.io/Atlas")
        self.assertEqual(site.address("fr", "explore/"), "https://jigsawfr.github.io/Atlas/fr/explore/")
        self.assertEqual(site.host, "jigsawfr.github.io")


class Sites(unittest.TestCase):
    def read(self, text):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "sites.json"
            path.write_text(text, encoding="utf-8")
            return boreale.read_sites(path)

    def test_shipped(self):
        keys = [s["key"] for _, sites in boreale.read_sites() for s in sites]
        self.assertEqual(keys[0], "boreale")
        for key in keys:
            self.assertTrue((boreale.ASSETS / "marks" / f"{key}.svg").exists(), key)
            for code, catalog in boreale.common_catalogs().items():
                self.assertIn(f"sites_{key}", catalog, code)

    def test_absent(self):
        self.assertEqual(boreale.read_sites(Path("/nonexistent/sites.json")), [])

    def test_newer_schema(self):
        self.assertEqual(self.read('{"schema": 2, "groups": [{"title": null, "sites": []}]}'), [])

    def test_unknown_field(self):
        groups = self.read(json.dumps({"schema": 1, "later": True, "groups": [{"title": None, "colour": "x", "sites": [
            {"key": "boreale", "name": "Boréale", "url": "https://boreale.dev/", "utm": "boreale", "new": 1}]}]}))
        self.assertEqual(groups, [(None, [{"key": "boreale", "name": "Boréale", "url": "https://boreale.dev/",
                                           "utm": "boreale", "soon": False}])])

    def test_switcher(self):
        catalog = boreale.common_catalogs()["fr"]
        html = boreale.Site("atlas").switcher("fr", catalog, "../", {"playguard": "1.4.0"})
        self.assertIn('href="../fr/" aria-current="true"', html)
        self.assertIn('href="https://boreale.dev/fr/"', html)
        self.assertIn('<span class="sites-version">1.4.0</span>', html)
        self.assertIn('assets/marks/atlas.svg" alt="" width="34"', html)
        self.assertIn(catalog["sites_open"], html)

    def test_switcher_brand_and_home(self):
        catalog = boreale.common_catalogs()["en-US"]
        html = boreale.Site("playguard").switcher("en-US", catalog, "../", brand="<span>Play<b>Guard</b></span>",
                                                  home="../index.html")
        self.assertIn('popovertarget="sites" aria-label="PlayGuard · ', html)
        self.assertIn('"><span>Play<b>Guard</b></span><svg class="chevron"', html)
        self.assertIn('href="../index.html" aria-current="true"', html)


class Versions(unittest.TestCase):
    def test_schema_1(self):
        self.assertEqual(boreale.read_versions({"schema": 1, "projects": {"playguard": "1.4.0", "x": 2}, "new": 1}),
                         {"playguard": "1.4.0"})

    def test_other_shapes(self):
        for document in (None, [], {"playguard": "1.4.0"}, {"schema": 2, "projects": {"playguard": "9.0.0"}},
                         {"schema": "1", "projects": {}}, {"schema": 1, "projects": []}):
            self.assertEqual(boreale.read_versions(document), {}, document)

    def test_offline(self):
        with mock.patch.dict(os.environ, {"SITE_OFFLINE": "1"}):
            self.assertEqual(boreale.latest_versions(), {})


class Text(unittest.TestCase):
    def test_day(self):
        self.assertEqual(boreale.day(date(2026, 10, 30), "en-US"), "Oct 30, 2026")
        self.assertEqual(boreale.day(date(2026, 10, 30), "fr"), "30 oct. 2026")
        self.assertEqual(boreale.day(date(2026, 10, 30), "ja"), "2026年10月30日")

    def test_folder(self):
        self.assertEqual(boreale.folder("en-US"), "")
        self.assertEqual(boreale.folder("zh-Hant"), "zh-hant/")

    def test_languages_menu(self):
        html = boreale.Site.languages("de", boreale.common_catalogs()["de"], "../", "explore/")
        self.assertEqual(html.count("<li>"), 15)
        self.assertIn('href="../de/explore/" data-lang="de" lang="de" hreflang="de" aria-current="true"', html)

    def test_common_catalogs(self):
        with tempfile.TemporaryDirectory() as d:
            own = Path(d) / "i18n"
            own.mkdir()
            for code in boreale.CODES:
                (own / f"{code}.json").write_text('{"title": "x"}', encoding="utf-8")
            self.assertEqual(boreale.check_catalogs(own), [])
            self.assertEqual(boreale.catalogs(own)["fr"]["language"], "Langue")
            (own / "fr.json").write_text('{"title": "x", "language": "Langue"}', encoding="utf-8")
            self.assertTrue(any("boreale-site's" in e for e in boreale.check_catalogs(own)))
            with self.assertRaises(SystemExit):
                boreale.catalogs(own)

    def test_optional_empty(self):
        # Aurore's English note that a page is in English: empty on purpose,
        # shown in the other languages alone.
        with tempfile.TemporaryDirectory() as d:
            own = Path(d) / "i18n"
            own.mkdir()
            for code in boreale.CODES:
                text = "" if code == "en-US" else "In English"
                (own / f"{code}.json").write_text(json.dumps({"title": "x", "doc_untranslated": text}), encoding="utf-8")
            self.assertEqual(boreale.check_catalogs(own), ["i18n/en-US.json: doc_untranslated is empty"])
            self.assertEqual(boreale.check_catalogs(own, optional={"en-US": {"doc_untranslated"}}), [])
            (own / "de.json").write_text('{"title": "x"}', encoding="utf-8")
            self.assertEqual(boreale.check_catalogs(own, optional={"en-US": {"doc_untranslated"}}),
                             ["i18n/de.json: no doc_untranslated"])


PAGE = """<!doctype html><html><head><meta name="referrer" content="no-referrer">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; connect-src {connect}; base-uri 'none'">
<script src="assets/umami.js" defer></script></head><body><main id="main">{body}</main></body></html>"""


class Checks(unittest.TestCase):
    def errors(self, body, connect="'self' https://gateway.umami.is"):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            (out / "assets").mkdir()
            (out / "assets" / "umami.js").write_text("", encoding="utf-8")
            (out / "index.html").write_text(PAGE.format(body=body, connect=connect), encoding="utf-8")
            return check.pages(out, boreale.Site("atlas"))[0]

    def test_clean(self):
        self.assertEqual(self.errors('<a href="#main">top</a><a href="https://example.org/" rel="noreferrer">x</a>'
                                     '<a href="https://boreale.dev/?utm_source=atlas&amp;utm_medium=link" '
                                     'referrerpolicy="strict-origin">b</a>'), [])

    def test_problems(self):
        found = self.errors('<a href="https://example.org/">x</a><a href="https://boreale.dev/" '
                            'referrerpolicy="strict-origin">b</a><a href="nowhere/">n</a><a href="#none">a</a>'
                            '<p style="color:red">contact@boreale.dev</p><script>1</script>'
                            '<img src="https://example.org/i.png" alt="">', connect="https://example.org")
        for part in ('without rel="noreferrer"', "without utm_source=atlas", "nowhere/ leads nowhere",
                     "#none is not on the page", "style attribute", "e-mail address", "inline <script>",
                     "loads https://example.org/i.png", "connect-src"):
            self.assertTrue(any(part in e for e in found), (part, found))

    def test_reserved_address(self):
        self.assertEqual(self.errors("<p>someone@example.org</p>"), [])

    def test_event_handler(self):
        found = self.errors('<button onclick="go()">x</button>')
        self.assertEqual(found, ["index.html: onclick attribute on <button> (the Content-Security-Policy blocks it)"])

    def test_poster(self):
        self.assertEqual(self.errors('<video poster="nowhere.png"></video>'), ["index.html: nowhere.png leads nowhere"])


REDIRECT = """<!doctype html><html><head>{referrer}
<meta http-equiv="refresh" content="0; url=../getting-started/"></head><body></body></html>"""


class Site(unittest.TestCase):
    """check.pages() on a site of several files: {path: body or whole page}."""

    def errors(self, files, site=None, **options):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            (out / "assets").mkdir()
            (out / "assets" / "umami.js").write_text("", encoding="utf-8")
            for path, text in files.items():
                (out / path).parent.mkdir(parents=True, exist_ok=True)
                page = text if text.startswith("<!doctype") else PAGE.format(
                    body=text, connect="'self' https://gateway.umami.is")
                root = "../" * path.count("/")
                (out / path).write_text(page.replace('src="assets/', f'src="{root}assets/'), encoding="utf-8")
            return check.pages(out, site or boreale.Site("atlas"), **options)[0]

    def test_anchor_in_another_page(self):
        files = {"index.html": '<a href="docs/#setup">s</a><a href="docs/#nothing">n</a>',
                 "docs/index.html": '<h2 id="setup">Setup</h2><a href="../#main">home</a>'}
        self.assertEqual(self.errors(files), ["index.html: docs/#nothing: #nothing is not on docs/index.html"])

    def test_view_of_a_script(self):
        # A #fragment holding a "/" is a view (Atlas's explorer), not an id.
        self.assertEqual(self.errors({"index.html": '<a href="explore/#steam/popular">e</a>',
                                      "explore/index.html": ""}), [])

    def test_own_address(self):
        site = boreale.Site("atlas", "https://jigsawfr.github.io/Atlas/")
        files = {"index.html": '<link rel="canonical" href="https://jigsawfr.github.io/Atlas/">'
                               '<link rel="alternate" hreflang="fr" href="https://jigsawfr.github.io/Atlas/fr/">'
                               '<a href="https://jigsawfr.github.io/Atlas/docs/#setup" rel="noreferrer">d</a>',
                 "fr/index.html": "", "docs/index.html": ""}
        self.assertEqual(self.errors(files, site), [
            "index.html: https://jigsawfr.github.io/Atlas/docs/#setup: #setup is not on docs/index.html"])
        del files["fr/index.html"]
        self.assertIn("index.html: https://jigsawfr.github.io/Atlas/fr/ leads nowhere", self.errors(files, site))

    def test_apart(self):
        files = {"index.html": '<a href="simulator/">s</a><a href="simulator/x.html#y">x</a>',
                 "simulator/index.html": "<!doctype html><html><body>built apart, no policy</body></html>"}
        found = self.errors(files)
        self.assertTrue(any("simulator/index.html: no Content-Security-Policy" in e for e in found), found)
        self.assertEqual(self.errors(files, apart=("simulator",)), [])
        del files["simulator/index.html"]
        self.assertEqual(self.errors(files, apart=("simulator",)), [])

    def test_redirect(self):
        # No script runs there: neither policy nor tracker, but no referrer.
        files = {"index.html": '<a href="docs/">docs</a>', "docs/getting-started/index.html": "",
                 "docs/index.html": REDIRECT.format(referrer='<meta name="referrer" content="no-referrer">')}
        self.assertEqual(self.errors(files), [])
        files["docs/index.html"] = REDIRECT.format(referrer="")
        self.assertEqual(self.errors(files), ['docs/index.html: no <meta name="referrer" content="no-referrer">'])

    def test_preview(self):
        files = {"index.html": PAGE.format(body="", connect="'self' https://gateway.umami.is")
                 .replace('<script src="assets/umami.js" defer></script>', "")}
        self.assertEqual(self.errors(files), ["index.html: no Umami tracker (assets/umami.js)"])
        self.assertEqual(self.errors(files, tracker=False), [])

    def test_lost_base(self):
        # 404.html, served at any address: its links start from SITE_BASE.
        files = {"404.html": '<a href="/PlayGuard/pr-9/">home</a><a href="/PlayGuard/pr-9/fr/">fr</a>',
                 "index.html": "", "fr/index.html": ""}
        site = boreale.Site("playguard", "https://jigsawfr.github.io/PlayGuard/pr-9/")
        self.assertEqual(self.errors(files, site), [])
        self.assertEqual(self.errors(files, site, base="/PlayGuard/pr-9/"), [])
        site = boreale.Site("playguard")
        self.assertEqual(self.errors(files, site, base="/PlayGuard/pr-9"), [])
        self.assertEqual(self.errors(files, site), ["404.html: /PlayGuard/pr-9/ leads nowhere",
                                                    "404.html: /PlayGuard/pr-9/fr/ leads nowhere"])


if __name__ == "__main__":
    unittest.main()
