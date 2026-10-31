"""The checks every built site of Boréale passes (README.md), for a site's
tools/check_site.py:

    errors = boreale_check.pages(Path("build"), site)

- no {{key}} left in a page;
- every link and image to the site leads to a file, its absolute links to
  its own address included, and every #anchor to an id of the page it names
  (a #fragment holding a "/" is a view of a page's script, not an id); the
  folders built apart (`apart`: a simulator, a demo) are neither walked nor
  followed;
- links out by the rule "liens sortants anonymes": every page sends no
  referrer, a link to a third party has rel="noreferrer", one to
  *.boreale.dev or github.com/JigSawFr has referrerpolicy="strict-origin";
  one to another of our sites has the site's utm_source and a utm_medium, no
  other link has utm_ parameters;
- nothing the Content-Security-Policy blocks: no inline script (but data, by
  its type), no <style>, no style="" or on*="" (event handler) attribute,
  nothing loaded from another site; the policy's connect-src is the site's
  own and Umami's alone, whose tracker (assets/umami.js) every page carries
  (not a preview's, `tracker=False`); a page that only sends its visitor on
  (<meta http-equiv="refresh">) runs nothing and needs neither, but sends no
  referrer either;
- no real e-mail address: contact goes through the repositories' issues;
- the data in pages (JSON, by type) reads;
- with `chrome=True` (a site on v4's header and footer, assets/chrome.css):
  the header of Site.header() on every page, with its name and menu of
  Boréale's sites, its row of links, its pill, its languages, at most one
  link marked aria-current in the row, one site and one language marked in
  the menus (the language of <html lang>); the footer of Site.footer(), which
  links to every other site of sites.json; chrome.css and chrome.js loaded; no
  canvas#sky outside a home's sky. A site can no longer drift from the rest.
"""
import fnmatch
import json
import os
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlparse

from . import UMAMI_GATEWAY, Site, ours, own_site

EMAIL = re.compile(r"[\w.+-]+@(?:[\w-]+\.)+[a-z]{2,}", re.IGNORECASE)
RESERVED = re.compile(r"@(?:[\w-]+\.)*(?:example\.(?:org|com|net)|[\w-]+\.example)$", re.IGNORECASE)
# The data a page may carry in a <script> (it runs nothing).
DATA_TYPES = ("application/ld+json", "application/json")


def emails(text: str) -> list:
    return [m.group(0) for m in EMAIL.finditer(text) if not RESERVED.search(m.group(0))]


def link_problem(attrs: dict, site: Site) -> str:
    """What a link out does wrong, or ''."""
    href = attrs.get("href") or ""
    u = urlparse(href)
    if u.scheme not in ("http", "https"):
        return ""
    rel = (attrs.get("rel") or "").split()
    if own_site(href):
        if "noreferrer" in rel or attrs.get("referrerpolicy") != "strict-origin":
            return f'link to {href} needs referrerpolicy="strict-origin" and no noreferrer'
    elif "noreferrer" not in rel:
        return f'link to {href} without rel="noreferrer"'
    query = dict(parse_qsl(u.query))
    if ours(href) and (u.hostname or "").lower() != site.host:
        if query.get("utm_source") != site.utm_source or not query.get("utm_medium"):
            return f"link to {href} without utm_source={site.utm_source} and a utm_medium"
    elif any(k.startswith("utm_") for k in query):
        return f"link to {href} with utm_ parameters: only a link to another of our sites has them"
    return ""


def policy_problem(content: str) -> str:
    """What is wrong with a page's Content-Security-Policy's connect-src: it
    may reach the site itself and Umami's gateway, nothing else."""
    for part in content.split(";"):
        words = part.split()
        if words and words[0] == "connect-src":
            sources = set(words[1:])
            if UMAMI_GATEWAY not in sources or sources - {"'self'", UMAMI_GATEWAY}:
                return f"its policy's connect-src is {' '.join(words[1:])}, not 'self' and Umami's alone"
            return ""
    return "its policy has no connect-src for Umami"


VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Page(HTMLParser):
    def __init__(self, site: Site):
        super().__init__()
        self.site = site
        self.ids, self.links, self.problems, self.data = set(), [], [], []
        self.in_data = False
        self.no_referrer = False
        self.redirect = False
        self.policy = None
        self.tracker = False
        # v4's chrome: what the header, the footer and the sky are made of.
        self.stack = []
        self.lang = None
        self.headers = 0
        self.header = {"switch": False, "sites": False, "nav": 0, "nav_label": False, "nav_links": [],
                       "sites_current": 0, "langs": False, "lang_button": False, "langs_current": [], "parts": []}
        self.footers = 0
        self.footer_links = []
        self.sky_home = False
        self.canvas = False
        self.chrome_css = False
        self.chrome_js = False

    def context(self, tag, a):
        """What an element is in the chrome's markup, or ''."""
        classes = (a.get("class") or "").split()
        if tag == "header" and "top" in classes:
            return "header"
        if tag == "footer" and "footer" in classes:
            return "footer"
        if "header" in {c for _, c in self.stack}:
            if a.get("id") == "sites":
                return "sites"
            if a.get("id") == "languages":
                return "langs"
            if tag == "div" and "switcher" in classes:
                return "switcher"
            if tag == "nav" and "nav" in classes:
                return "nav"
            if tag == "div" and "settings" in classes:
                return "settings"
        return ""

    def chrome(self, tag, a, kind):
        inside = {c for _, c in self.stack}
        h = self.header
        if kind == "header":
            self.headers += 1
        elif kind == "footer":
            self.footers += 1
        elif kind == "nav":
            h["nav"] += 1
            h["nav_label"] = bool((a.get("aria-label") or "").strip())
        elif kind in ("switcher", "settings"):
            h["parts"].append(kind)
        elif kind == "sites":
            h["sites"] = "popover" in a
        elif kind == "langs":
            h["langs"] = "popover" in a
        if "header" in inside:
            classes = (a.get("class") or "").split()
            if tag == "button" and "switch" in classes and "brand" in classes:
                h["switch"] = True
            if tag == "button" and "lang-button" in classes:
                h["lang_button"] = True
            if tag == "a" and "nav" in inside:
                h["nav_links"].append((classes, "aria-current" in a))
            if tag == "a" and "sites" in inside and "aria-current" in a:
                h["sites_current"] += 1
            if tag == "a" and "langs" in inside and "aria-current" in a:
                h["langs_current"].append(a.get("lang"))
        if tag == "a" and "footer" in inside and a.get("href"):
            self.footer_links.append(a["href"])
        if "sky-home" in (a.get("class") or "").split():
            self.sky_home = True
        if tag == "canvas" and a.get("id") == "sky":
            self.canvas = True
        if tag == "link" and a.get("rel") == "stylesheet" and (a.get("href") or "").endswith("assets/chrome.css"):
            self.chrome_css = True
        if tag == "script" and (a.get("src") or "").endswith("assets/chrome.js"):
            self.chrome_js = True

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "html":
            self.lang = a.get("lang")
        kind = self.context(tag, a)
        self.chrome(tag, a, kind)
        if tag not in VOID:
            self.stack.append((tag, kind))
        if tag == "meta" and a.get("name") == "referrer" and a.get("content") == "no-referrer":
            self.no_referrer = True
        if tag == "meta" and (a.get("http-equiv") or "").lower() == "content-security-policy":
            self.policy = a.get("content") or ""
        if tag == "meta" and (a.get("http-equiv") or "").lower() == "refresh":
            self.redirect = True
        if tag == "a":
            problem = link_problem(a, self.site)
            if problem:
                self.problems.append(problem)
        if "id" in a:
            self.ids.add(a["id"])
        if "style" in a:
            self.problems.append(f"style attribute on <{tag}>")
        self.problems += [f"{k} attribute on <{tag}> (the Content-Security-Policy blocks it)"
                          for k in a if k.startswith("on")]
        if tag == "style":
            self.problems.append("<style> element")
        if tag == "script":
            if a.get("type") in DATA_TYPES:
                self.in_data = True
                self.data.append("")
                return
            if not a.get("src"):
                self.problems.append("inline <script>")
            elif (a.get("src") or "").endswith("assets/umami.js"):
                self.tracker = True
        for name in ("href", "src", "poster"):
            if name in a:
                self.links.append((name, a[name]))

    def handle_data(self, data):
        if self.in_data:
            self.data[-1] += data

    def handle_endtag(self, tag):
        if tag == "script":
            self.in_data = False
        # Back to the element that opens it, whatever was left unclosed (<li>, <p>).
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


def chrome_problems(page: Page, site: Site, cta: bool = True) -> list:
    """What a page's header, footer and sky have wrong against v4's chrome
    (Site.header(), Site.footer(), Site.sky()), or []."""
    problems = []
    h = page.header
    if not page.chrome_css:
        problems.append("assets/chrome.css is not loaded")
    if not page.chrome_js:
        problems.append("assets/chrome.js is not loaded")
    if page.headers != 1:
        problems.append(f'{page.headers} <header class="top">, one wanted (Site.header())')
    else:
        if not h["switch"] or not h["sites"]:
            problems.append("header: no name button with the menu of Boréale's sites (popover #sites)")
        if h["nav"] != 1:
            problems.append(f'header: {h["nav"]} <nav class="nav">, one wanted (the row of links)')
        elif not h["nav_label"]:
            problems.append("header: its nav has no aria-label")
        if not h["lang_button"] or not h["langs"]:
            problems.append("header: no language button with its menu (popover #languages)")
        if h["parts"] != ["switcher", "settings"]:
            problems.append("header: the name's menu comes first, the languages' last")
        links = h["nav_links"]
        pills = [i for i, (classes, _) in enumerate(links) if "nav-cta" in classes]
        if len(pills) > 1 or (cta and not pills):
            problems.append(f"header: {len(pills)} call to action (a.nav-cta), " + ("one" if cta else "at most one") + " wanted")
        github = [i for i, (classes, _) in enumerate(links) if "nav-gh" in classes]
        if len(github) > 1:
            problems.append("header: more than one GitHub link (a.nav-gh)")
        if pills and github and github[0] < pills[0]:
            problems.append("header: GitHub comes before the call to action")
        if pills and pills[0] != max(i for i, (c, _) in enumerate(links) if "nav-gh" not in c):
            problems.append("header: the call to action comes after the page's links, GitHub last")
        if sum(1 for _, current in links if current) > 1:
            problems.append("header: more than one link of the row is aria-current")
        if h["sites_current"] != 1:
            problems.append(f"header: {h['sites_current']} sites marked aria-current in the menu of Boréale's sites, one wanted")
        if len(h["langs_current"]) != 1:
            problems.append(f"header: {len(h['langs_current'])} languages marked aria-current, one wanted")
        elif page.lang and h["langs_current"][0] != page.lang:
            problems.append(f"header: the language marked is {h['langs_current'][0]}, the page's <html lang> is {page.lang}")
    if page.footers != 1:
        problems.append(f'{page.footers} <footer class="footer">, one wanted (Site.footer())')
    else:
        for _, group in site.groups:
            for other in group:
                if other["key"] != site.key and not any(link.startswith(other["url"]) for link in page.footer_links):
                    problems.append(f"footer: no link to {other['name']} ({other['url']}), sites.json's")
    if page.canvas and not page.sky_home:
        problems.append("canvas#sky outside a home's sky (Site.sky(home=True))")
    return problems


def pages(out: Path, site: Site, skip: tuple = ("assets",), apart: tuple = (), tracker: bool = True,
          base: str = None, chrome: bool = False, bare: tuple = (), cta: bool = True) -> tuple:
    """Every page of the built site `out` checked: (errors, how many pages).
    `skip`: folders not walked (assets, a site's data), wherever they are.
    `apart`: folders of the site's root built apart (simulator, demo): not
    walked, and a link into one is not followed. `tracker`: False for a
    preview, counted by no one (SITE_NOINDEX=1). `base`: the path the root's
    404.html is served under, wherever the address not found is (a site's
    SITE_BASE, /PlayGuard/): its links start from there; the site's own
    address' path by default. `chrome`: the site is on v4's header and footer
    (chrome_problems()), on every page but those of `bare` (globs on the
    page's path: a page without them); `cta`: False for a site whose header
    has no call to action."""
    errors = []
    apart = [Path(a).parts for a in apart]

    def built_apart(parts) -> bool:
        return any(tuple(parts[:len(a)]) == a for a in apart)

    found = [p for p in sorted(out.rglob("*.html"))
             if not set(p.relative_to(out).parts[:-1]) & set(skip) and not built_apart(p.relative_to(out).parts)]
    if not found:
        errors.append(f"no page in {out}")
    read = {}

    def parse(path: Path) -> Page:
        if path not in read:
            read[path] = Page(site)
            read[path].feed(path.read_text(encoding="utf-8"))
        return read[path]

    own = urlparse(site.url).path
    lost = base.rstrip("/") + "/" if base else own
    root = out.resolve()
    for path in found:
        name = path.relative_to(out).as_posix()
        text = path.read_text(encoding="utf-8")
        if "{{" in text:
            errors.append(f"{name}: a {{{{key}}}} is left")
        errors += [f"{name}: an e-mail address ({e}), contact goes through GitHub" for e in emails(text)]
        parsed = parse(path)
        errors += [f"{name}: {p}" for p in parsed.problems]
        if not parsed.no_referrer:
            errors.append(f'{name}: no <meta name="referrer" content="no-referrer">')
        if parsed.policy is None:
            if not parsed.redirect:
                errors.append(f"{name}: no Content-Security-Policy")
        elif policy_problem(parsed.policy):
            errors.append(f"{name}: {policy_problem(parsed.policy)}")
        if tracker and not parsed.tracker and not parsed.redirect:
            errors.append(f"{name}: no Umami tracker (assets/umami.js)")
        if chrome and not parsed.redirect and not any(fnmatch.fnmatchcase(name, g) for g in bare):
            errors += [f"{name}: {p}" for p in chrome_problems(parsed, site, cta)]
        for data in parsed.data:
            try:
                json.loads(data or "{}")
            except ValueError as error:
                errors.append(f"{name}: its data is not JSON ({error})")
        for attr, link in parsed.links:
            url = urlparse(link)
            if url.scheme in ("http", "https") and attr != "src" and link.startswith(site.url):
                # The site's own address (its canonical page, its languages):
                # the file it names.
                url = urlparse(link[len(site.url):])
                target = root / unquote(url.path)
            elif url.scheme in ("http", "https", "mailto", "data"):
                if attr == "src" and url.scheme != "data":
                    errors.append(f"{name}: loads {link} from another site")
                continue
            elif url.scheme or link.startswith("//"):
                continue
            elif url.path.startswith("/"):
                # From the site's root: its address' path, or where the
                # root's 404.html is served (`base`).
                prefix = lost if name == "404.html" else own
                if not url.path.startswith(prefix):
                    errors.append(f"{name}: {link} leads nowhere (not under {prefix})")
                    continue
                target = root / unquote(url.path[len(prefix):])
            else:
                target = path.resolve().parent / unquote(url.path) if url.path else path.resolve()
            target = Path(os.path.normpath(target))
            if target.is_relative_to(root) and built_apart(target.relative_to(root).parts):
                continue
            if target.is_dir():
                target = target / "index.html"
            if not target.exists():
                errors.append(f"{name}: {link} leads nowhere")
                continue
            fragment = unquote(url.fragment)
            if not fragment or "/" in fragment or target.suffix != ".html":
                continue
            if target == path.resolve():
                if fragment not in parsed.ids:
                    errors.append(f"{name}: #{fragment} is not on the page")
            elif fragment not in parse(target).ids:
                errors.append(f"{name}: {link}: #{fragment} is not on {target.relative_to(root).as_posix()}")
    return errors, len(found)
