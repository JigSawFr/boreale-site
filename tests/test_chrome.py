"""v4's page chrome: Site.header(), Site.sky(), Site.footer(), their texts,
the checks that keep a built page to them, and the reference pages.

    python3 -m unittest discover -s tests
"""
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import boreale_site as boreale  # noqa: E402
from boreale_site import check  # noqa: E402
import sample_site  # noqa: E402

CATALOG = {**boreale.common_catalogs()["en-US"], "nav_a": "Features", "nav_b": "Docs", "nav_c": "Try it"}


def header(site, **kw):
    args = dict(links=[("nav_a", "#a"), ("nav_b", "docs/")], cta=("nav_c", "try/"), github="https://github.com/JigSawFr/Atlas")
    args.update(kw)
    return site.header("en-US", CATALOG, "", "", **args)


class Header(unittest.TestCase):
    def test_structure_and_order(self):
        out = header(boreale.Site("atlas"))
        self.assertTrue(out.startswith('<header class="top">'))
        self.assertLess(out.index('class="switcher"'), out.index('<nav class="nav" aria-label="Atlas">'))
        self.assertLess(out.index("</nav>"), out.index('class="settings"'))
        links = re.findall(r'<a href="([^"]*)"( class="[^"]*")?', out[out.index('<nav'):out.index("</nav>")])
        self.assertEqual([h for h, _ in links], ["#a", "docs/", "try/", "https://github.com/JigSawFr/Atlas"])
        self.assertEqual([c for _, c in links], ["", "", ' class="nav-cta"', ' class="nav-gh"'])

    def test_current(self):
        nav = lambda out: out[out.index("<nav"):out.index("</nav>")]  # noqa: E731
        self.assertEqual(nav(header(boreale.Site("atlas"))).count("aria-current"), 0)
        out = nav(header(boreale.Site("atlas"), current="nav_b"))
        self.assertEqual(out.count("aria-current"), 1)
        self.assertIn('<a href="docs/" aria-current="page">Docs</a>', out)
        self.assertIn('class="nav-cta" aria-current="page"', nav(header(boreale.Site("atlas"), current="nav_c")))

    def test_links_out_rules(self):
        out = header(boreale.Site("atlas"), links=[("nav_a", "https://boreale.dev/fr/"), ("nav_b", "https://example.org/?utm_source=x")],
                     cta=("nav_c", "https://atlas.boreale.dev/?utm_source=github"), github="https://github.com/someone/else")
        self.assertIn('href="https://boreale.dev/fr/?utm_source=atlas&amp;utm_medium=nav" referrerpolicy="strict-origin"', out)
        self.assertIn('href="https://example.org/?utm_source=x" rel="noreferrer"', out)
        self.assertIn('<a href="https://atlas.boreale.dev/" class="nav-cta" referrerpolicy="strict-origin">', out)
        self.assertIn('href="https://github.com/someone/else" class="nav-gh" rel="noreferrer"', out)
        # A relative link carries nothing.
        self.assertNotIn("rel=", header(boreale.Site("atlas"), github=None).split('<nav')[1].split('</nav>')[0])

    def test_links_out_is_idempotent(self):
        site = boreale.Site("atlas")
        out = header(site)
        self.assertEqual(site.links_out(out), out)

    def test_optional_parts(self):
        out = header(boreale.Site("atlas"), links=(), cta=None, github=None, label="Main")
        self.assertIn('<nav class="nav" aria-label="Main">\n\n    </nav>', out)
        self.assertNotIn("nav-cta", out)

    def test_unknown_text_stops(self):
        with self.assertRaises(KeyError):
            header(boreale.Site("atlas"), links=[("nope", "#")])

    def test_languages_and_sites(self):
        out = boreale.Site("lantern").header("fr", {**CATALOG, **boreale.common_catalogs()["fr"]}, "../", "spec/",
                                             links=[("nav_a", "#a")], cta=("nav_c", "#b"))
        self.assertIn('href="../fr/spec/" data-lang="fr" lang="fr" hreflang="fr" aria-current="true"', out)
        self.assertEqual(out.count('aria-current="true"'), 2)  # this site and this language
        self.assertIn('https://ha.boreale.dev/fr/?utm_source=lantern', out)


class SkyAndSkip(unittest.TestCase):
    def test_sky(self):
        self.assertEqual(boreale.Site.sky(), '<div class="sky">')
        self.assertIn('<canvas id="sky" aria-hidden="true"></canvas>', boreale.Site.sky(home=True))
        still = boreale.Site.sky(home=True, canvas=False)
        self.assertIn("sky-home", still)
        self.assertNotIn("canvas", still)

    def test_skip(self):
        self.assertEqual(boreale.Site("atlas").skip(CATALOG), '<a class="skip" href="#main">Skip to content</a>')


class Footer(unittest.TestCase):
    def footer(self, key="playguard", language="en-US", **kw):
        catalog = {**boreale.common_catalogs()[language]}
        return boreale.Site(key).footer(language, catalog, "", **kw)

    def test_every_other_site_from_sites_json(self):
        out = self.footer("atlas", "de")
        for _, group in boreale.read_sites():
            for s in group:
                present = f'href="{s["url"]}de/?utm_source=atlas&amp;utm_medium=footer"' in out
                self.assertEqual(present, s["key"] != "atlas", s["key"])
        self.assertIn("Home Assistant", out)
        self.assertIn("https://boreale.dev/de/legal/", out)

    def test_a_site_added_appears(self):
        extra = boreale.read_sites() + [("sites_open", [{"key": "newcomer", "name": "Newcomer", "url": "https://new.boreale.dev/",
                                                         "utm": "new", "soon": False}])]
        site = boreale.Site("atlas", sites=extra)
        self.assertIn('href="https://new.boreale.dev/?utm_source=atlas&amp;utm_medium=footer"',
                      site.footer("en-US", boreale.common_catalogs()["en-US"], ""))

    def test_columns_about_fine_support(self):
        out = self.footer(columns=[("Docs", [("Start", "docs/"), ("Repo", "https://github.com/JigSawFr/PlayGuard")])],
                          about=["Free software."], fine="Fine print.")
        self.assertIn("<h2>Docs</h2>", out)
        self.assertIn('<li><a href="docs/">Start</a></li>', out)
        self.assertIn('href="https://github.com/JigSawFr/PlayGuard" referrerpolicy="strict-origin">Repo', out)
        self.assertIn("<p>Free software.</p>", out)
        self.assertIn('<p class="fine">Fine print.</p>', out)
        self.assertIn('href="https://ko-fi.com/jigsawfr" rel="noreferrer"', out)
        self.assertNotIn("Ko-fi", self.footer(support=False))
        self.assertNotIn('class="fine"', self.footer())

    def test_boreale_itself_has_no_part_of_link(self):
        self.assertNotIn('class="boreale"', self.footer("boreale"))
        self.assertIn('class="boreale"', self.footer("atlas"))


class Catalogs(unittest.TestCase):
    def test_new_texts_in_every_language(self):
        keys = {"chrome_skip", "chrome_legal", "chrome_support", "chrome_part_of"}
        for code, catalog in boreale.common_catalogs().items():
            self.assertTrue(keys <= set(catalog), code)
            self.assertTrue(all(catalog[k].strip() for k in keys), code)

    def test_library_catalogs_are_consistent(self):
        errors = [e for e in boreale.check_catalogs(ROOT / "i18n") if "boreale-site/i18n" in e]
        self.assertEqual(errors, [])

    def test_site_catalog_repeating_them_stops(self):
        with tempfile.TemporaryDirectory() as d:
            own = Path(d) / "i18n"
            own.mkdir()
            for code in boreale.CODES:
                (own / f"{code}.json").write_text('{"chrome_skip": "x"}', encoding="utf-8")
            with self.assertRaises(SystemExit):
                boreale.catalogs(own)

    def test_asset_names_do_not_collide_with_a_site_that_has_its_own(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            (out / "assets").mkdir()
            (out / "assets" / "site.css").write_text("", encoding="utf-8")
            boreale.copy_assets(out)
            self.assertTrue((out / "assets" / "chrome.css").exists() and (out / "assets" / "chrome.js").exists())
            with self.assertRaises(SystemExit):  # a site's own chrome.css stops the build
                boreale.copy_assets(out)


class Sample(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dir = tempfile.TemporaryDirectory()
        cls.out = Path(cls.dir.name)
        cls.site = sample_site.build(cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.dir.cleanup()

    def test_sample_passes_every_check(self):
        errors, count = check.pages(self.out, self.site, chrome=True)
        self.assertEqual(errors, [])
        self.assertEqual(count, 30)

    def test_home_has_the_canvas_and_inner_does_not(self):
        home = (self.out / "index.html").read_text(encoding="utf-8")
        inner = (self.out / "inner" / "index.html").read_text(encoding="utf-8")
        self.assertIn('<canvas id="sky"', home)
        self.assertNotIn("canvas", inner)
        self.assertIn('<div class="sky">', inner)

    def break_page(self, edit, name="inner/index.html"):
        path = self.out / name
        original = path.read_text(encoding="utf-8")
        try:
            path.write_text(edit(original), encoding="utf-8")
            return check.pages(self.out, self.site, chrome=True)[0]
        finally:
            path.write_text(original, encoding="utf-8")

    def test_drift_is_reported(self):
        cases = {
            "no call to action": (lambda t: t.replace(' class="nav-cta"', ""), "call to action"),
            "two currents in the row": (lambda t: t.replace('<a href="#features">', '<a href="#features" aria-current="page">'), None),
            "no sites menu": (lambda t: t.replace('popover aria-label="Boréale', 'aria-label="Boréale', 1), "menu of Boréale's sites"),
            "no languages menu": (lambda t: t.replace('id="languages" class="langs" popover', 'id="languages" class="langs"'), "language button"),
            "no current language": (lambda t: t.replace(' aria-current="true"><span class="flag" aria-hidden="true">🇺🇸', '><span class="flag" aria-hidden="true">🇺🇸'), "languages marked"),
            "no nav label": (lambda t: t.replace('<nav class="nav" aria-label="Sample">', '<nav class="nav">'), "aria-label"),
            "no chrome.js": (lambda t: t.replace('<script src="../assets/chrome.js" defer></script>', ""), "chrome.js"),
            "a site missing from the footer": (lambda t: t.replace("https://lantern.boreale.dev/", "https://example.org/"), "no link to Lantern"),
            "canvas without the home sky": (lambda t: t.replace('<div class="sky">', '<div class="sky"><canvas id="sky"></canvas>'), "canvas#sky"),
            "no header": (lambda t: t.replace('<header class="top">', "<header>"), "<header class"),
        }
        for name, (edit, expected) in cases.items():
            errors = self.break_page(edit)
            if name == "two currents in the row":
                errors = self.break_page(lambda t: t.replace('<a href="../#features">', '<a href="../#features" aria-current="page">'))
                expected = "more than one link"
            self.assertTrue(any(expected in e for e in errors), f"{name}: {errors}")

    def test_bare_pages_and_redirects_are_left_alone(self):
        (self.out / "plain.html").write_text("<!doctype html><title>x</title>", encoding="utf-8")
        try:
            errors, _ = check.pages(self.out, self.site, chrome=True, bare=("plain.html",))
            self.assertFalse([e for e in errors if "plain.html" in e and "header" in e])
            errors, _ = check.pages(self.out, self.site, chrome=True)
            self.assertTrue([e for e in errors if "plain.html" in e and "header" in e])
            errors, _ = check.pages(self.out, self.site)  # without chrome=True, no change
            self.assertFalse([e for e in errors if "plain.html" in e and "header" in e])
        finally:
            (self.out / "plain.html").unlink()

    def test_cta_optional(self):
        errors = self.break_page(lambda t: t.replace(' class="nav-cta"', ""))
        self.assertTrue(errors)
        path = self.out / "inner" / "index.html"
        original = path.read_text(encoding="utf-8")
        try:
            path.write_text(original.replace(' class="nav-cta"', ""), encoding="utf-8")
            errors, _ = check.pages(self.out, self.site, chrome=True, cta=False)
            self.assertEqual(errors, [])
        finally:
            path.write_text(original, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
