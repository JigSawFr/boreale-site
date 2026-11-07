"""tools/check_links.py: the addresses it takes from a built site and the verdict it gives each, against a server of
this machine's own."""

import http.server
import importlib.util
import tempfile
import threading
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location("check_links", Path(__file__).resolve().parent.parent / "tools" / "check_links.py")
links = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(links)


class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, head: bool):
        path = self.path
        if path == "/moved":
            self.send_response(301)
            self.send_header("Location", "/ok")
            self.end_headers()
            return
        if path == "/nohead" and head:
            self.send_response(405)
            self.end_headers()
            return
        code = {"/ok": 200, "/nohead": 200, "/missing": 404, "/gone": 410, "/forbidden": 403, "/error": 500}.get(path, 404)
        self.send_response(code)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_HEAD(self):
        self.reply(True)

    def do_GET(self):
        self.reply(False)


class Links(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.base = f"http://127.0.0.1:{cls.server.server_port}"
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def test_verdicts(self):
        for path, expected in {"/ok": "ok", "/moved": "ok", "/nohead": "ok", "/missing": "broken", "/gone": "broken",
                               "/forbidden": "soft", "/error": "broken"}.items():
            self.assertEqual(links.verdict(self.base + path, 5)[0], expected, path)

    def test_nobody_there(self):
        self.assertEqual(links.verdict("http://127.0.0.1:9/", 2)[0], "broken")

    def test_collect(self):
        with tempfile.TemporaryDirectory() as d:
            site = Path(d)
            (site / "fr").mkdir()
            page = ('<a href="https://boreale.dev/x#top">a</a><a href="/local">b</a><a href="#here">c</a>'
                    '<a href="https://example.org/">d</a><a href="http://192.168.1.20:8465/">e</a>'
                    '<a href="https://skipme.test/p">f</a><link href="https://boreale.dev/css">')
            (site / "index.html").write_text(page, encoding="utf-8")
            (site / "fr" / "index.html").write_text('<a href="https://boreale.dev/x">a</a>', encoding="utf-8")
            self.assertEqual(links.collect(site, ("skipme.test",)), {"https://boreale.dev/x": ["fr/index.html", "index.html"]})


if __name__ == "__main__":
    unittest.main()
