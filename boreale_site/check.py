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
- the data in pages (JSON, by type) reads.
"""
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

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
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


def pages(out: Path, site: Site, skip: tuple = ("assets",), apart: tuple = (), tracker: bool = True,
          base: str = None) -> tuple:
    """Every page of the built site `out` checked: (errors, how many pages).
    `skip`: folders not walked (assets, a site's data), wherever they are.
    `apart`: folders of the site's root built apart (simulator, demo): not
    walked, and a link into one is not followed. `tracker`: False for a
    preview, counted by no one (SITE_NOINDEX=1). `base`: the path the root's
    404.html is served under, wherever the address not found is (a site's
    SITE_BASE, /PlayGuard/): its links start from there; the site's own
    address' path by default."""
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
