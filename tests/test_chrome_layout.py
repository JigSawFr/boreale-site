"""tools/chrome_layout.py: the measures' verdicts (problems(), no browser) and,
where a browser is at hand (PLAYWRIGHT_CHROMIUM or Playwright's own), a run on
the sample with a root 404.html and a page only English has.

    python3 -m unittest discover -s tests
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

try:
    import chrome_layout
except ImportError:  # no Playwright here
    chrome_layout = None

BOX = {"x": 0, "y": 0, "w": 100, "h": 72}


def measure(**kw):
    m = {"top": {**BOX, "h": 72}, "brand": {**BOX, "h": 44}, "nav": BOX, "cta": {**BOX, "x": 10}, "gh": {**BOX, "x": 50},
         "settings": BOX, "section": {**BOX, "y": 300}, "lead": 88, "wide": 1280, "wideOnes": [], "inner": 1180,
         "screen": 1280, "more": False, "scrolls": False}
    m.update(kw)
    return m


@unittest.skipIf(chrome_layout is None, "Playwright is not installed")
class Verdicts(unittest.TestCase):
    def test_a_clean_page(self):
        self.assertEqual(chrome_layout.problems(1280, measure()), [])

    def test_rhythm_is_the_first_sections_own(self):
        # A first section without an eyebrow: its content's distance is what counts, nothing else on the page.
        self.assertEqual(chrome_layout.problems(1280, measure(lead=88)), [])
        self.assertEqual(chrome_layout.problems(1280, measure(lead=176)), ["section rhythm 176px, not 88"])
        self.assertEqual(chrome_layout.problems(1280, measure(lead=None)), [])  # a section with no element in it
        self.assertEqual(chrome_layout.problems(1280, measure(lead=40), rhythm=False), [])
        self.assertEqual(chrome_layout.problems(768, measure(lead=40, wide=768, top={**BOX, "h": 100}, nav={**BOX, "y": 60}, cta={**BOX, "x": 0},
                                                             gh=None, inner=None), ), [])

    def test_no_pill(self):
        bare = measure(cta=None)
        self.assertIn("the pill is not before GitHub on one row", chrome_layout.problems(1280, bare))
        self.assertEqual(chrome_layout.problems(1280, bare, cta=False), [])
        self.assertEqual(chrome_layout.problems(1280, measure(), cta=False), ["a pill, on a site without one"])

    def test_a_page_without_the_header(self):
        self.assertEqual(chrome_layout.problems(1280, measure(top=None, nav=None, brand=None, cta=None, gh=None, more=False, scrolls=False)), [])


@unittest.skipIf(chrome_layout is None, "Playwright is not installed")
class Browser(unittest.TestCase):
    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(ROOT / "tools" / "chrome_layout.py"), *args], capture_output=True, text=True,
                              env={**os.environ}, timeout=300)

    def test_languages_skip_the_pages_a_language_lacks(self):
        import sample_site
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            sample_site.build(out)
            shutil.copy(out / "index.html", out / "404.html")  # a root 404.html
            (out / "only-en").mkdir()
            shutil.copy(out / "inner" / "index.html", out / "only-en" / "index.html")
            result = self.run_tool(str(out), "", "404.html", "only-en/", "--languages", "--rhythm-skip", "404.html")
            if "Executable doesn't exist" in result.stderr or "BrowserType.launch" in result.stderr:
                self.skipTest("no browser")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("answered 404 and were skipped: /fr/404.html", result.stdout)
            self.assertIn("0 problem(s)", result.stdout)
            self.assertNotIn("Traceback", result.stderr)
            # Sample's header has a pill: with --no-cta it is the thing reported.
            result = self.run_tool(str(out), "", "--no-cta")
            self.assertEqual(result.returncode, 1)
            self.assertIn("a pill, on a site without one", result.stdout)


if __name__ == "__main__":
    unittest.main()
