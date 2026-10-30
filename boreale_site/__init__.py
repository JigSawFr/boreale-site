"""What Boréale's websites share (README.md): their fifteen languages, the
header's menus, the rules for links out and the audience's UTM tags, the
texts and assets common to all of them.

A site's tools/build_site.py imports it from the submodule:

    sys.path.insert(0, str(ROOT / "library" / "boreale-site"))
    import boreale_site as boreale

    site = boreale.Site("atlas", os.environ.get("SITE_URL"))

Python's standard library only.
"""
import hashlib
import html
import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlsplit, urlunsplit

LIBRARY = Path(__file__).resolve().parent.parent
ASSETS = LIBRARY / "assets"

# Boréale's sites' languages, the consoles': the catalog's code
# (i18n/<code>.json), the site's folder ('' for the root, the first one), the
# name in its own words, the html lang.
LANGUAGES = [
    ("en", "", "English", "en"),
    ("fr", "fr", "Français", "fr"),
    ("fr-CA", "fr-ca", "Français (Canada)", "fr-CA"),
    ("de", "de", "Deutsch", "de"),
    ("es", "es", "Español", "es"),
    ("es-419", "es-419", "Español (Latinoamérica)", "es-419"),
    ("it", "it", "Italiano", "it"),
    ("nl", "nl", "Nederlands", "nl"),
    ("pt", "pt", "Português", "pt-PT"),
    ("pt-BR", "pt-br", "Português (Brasil)", "pt-BR"),
    ("ru", "ru", "Русский", "ru"),
    ("ja", "ja", "日本語", "ja"),
    ("ko", "ko", "한국어", "ko"),
    ("zh-Hans", "zh-hans", "简体中文", "zh-Hans"),
    ("zh-Hant", "zh-hant", "繁體中文", "zh-Hant"),
]
CODES = [code for code, _, _, _ in LANGUAGES]
# Each language's flag in the language menu (fonts/twemoji-flags.woff2 draws
# them the same everywhere, Windows included): the country of the console's
# language, Mexico for Latin America's Spanish, Taiwan for Traditional Chinese.
FLAGS = {"en": "US", "fr": "FR", "fr-CA": "CA", "de": "DE", "es": "ES", "es-419": "MX", "it": "IT", "nl": "NL",
         "pt": "PT", "pt-BR": "BR", "ru": "RU", "ja": "JP", "ko": "KR", "zh-Hans": "CN", "zh-Hant": "TW"}
# Open Graph's name of each language.
OG_LOCALES = {"en": "en_US", "fr": "fr_FR", "fr-CA": "fr_CA", "de": "de_DE", "es": "es_ES", "es-419": "es_LA",
              "it": "it_IT", "nl": "nl_NL", "pt": "pt_PT", "pt-BR": "pt_BR", "ru": "ru_RU", "ja": "ja_JP",
              "ko": "ko_KR", "zh-Hans": "zh_CN", "zh-Hant": "zh_TW"}

# A date as each language writes it, short: its months, and where the day,
# the month and the year go ({d} {m} {y}; the month first in English, the
# flag's American; by number in Chinese, Japanese and Korean).
_FR = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]
_ES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic"]
_PT = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
MONTHS = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "fr": _FR, "fr-CA": _FR,
    "de": ["Jan.", "Feb.", "März", "Apr.", "Mai", "Juni", "Juli", "Aug.", "Sept.", "Okt.", "Nov.", "Dez."],
    "es": _ES, "es-419": _ES,
    "it": ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"],
    "nl": ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"],
    "pt": _PT, "pt-BR": _PT,
    "ru": ["янв.", "февр.", "мар.", "апр.", "мая", "июн.", "июл.", "авг.", "сент.", "окт.", "нояб.", "дек."],
}
DATES = {"en": "{m} {d}, {y}", "de": "{d}. {m} {y}", "ja": "{y}年{n}月{d}日", "zh-Hans": "{y}年{n}月{d}日",
         "zh-Hant": "{y}年{n}月{d}日", "ko": "{y}. {n}. {d}."}  # else "{d} {m} {y}"

# The audience, counted by Umami Cloud (workbench's "Mesure d'audience"): its
# tracker, assets/umami.js, served by each site, sends each page seen to
# gateway.umami.is, without cookie, and only from the site's own host. One
# Umami site for all of Boréale's: its Hostname filter tells them apart.
UMAMI_WEBSITE = "6410ffdd-ae2e-4ddb-8e18-0a77e9fa374e"
UMAMI_GATEWAY = "https://gateway.umami.is"

# sites.json's schema (README.md): one it does not know reads as no list.
SITES_SCHEMA = 1


def folder(language: str) -> str:
    """A language's folder: none for the first one, at the root."""
    d = next(d for c, d, _, _ in LANGUAGES if c == language)
    return f"{d}/" if d else ""


def html_lang(language: str) -> str:
    """A language's code for html's lang and hreflang (pt-PT for pt)."""
    return next(hl for c, _, _, hl in LANGUAGES if c == language)


def flag(language: str) -> str:
    """A language's flag, two regional indicator letters, for the eyes only."""
    emoji = "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in FLAGS[language])
    return f'<span class="flag" aria-hidden="true">{emoji}</span>'


def day(when: date, language: str) -> str:
    """A date as the language writes it, short."""
    month = MONTHS[language][when.month - 1] if language in MONTHS else ""
    return DATES.get(language, "{d} {m} {y}").format(d=when.day, m=month, n=when.month, y=when.year)


KEY = re.compile(r"\{\{([a-z0-9_]+)\}\}")


def fill(text: str, values: dict) -> str:
    """Each {{key}} of `text` by its value; a key without one stops the build."""
    def one(match):
        key = match.group(1)
        if key not in values:
            sys.exit(f"build_site: no text for {{{{{key}}}}}")
        return values[key]
    # Twice: a text may hold a key ({{root}} in a catalog's links).
    return KEY.sub(one, KEY.sub(one, text))


def attribute(text: str) -> str:
    """A text for a double-quoted attribute (the apostrophes left as they are)."""
    return html.escape(text, quote=False).replace('"', "&quot;")


# ---- Texts: the common ones (i18n/) and a site's own.

def common_catalogs() -> dict:
    return {code: json.loads((LIBRARY / "i18n" / f"{code}.json").read_text(encoding="utf-8")) for code in CODES}


def catalogs(own: Path) -> dict:
    """Each language's texts: the site's own (`own`/<code>.json) and the
    common ones. A text lives in one place: a site's catalog that has a
    common key stops the build."""
    common = common_catalogs()
    merged = {}
    for code in CODES:
        mine = json.loads((own / f"{code}.json").read_text(encoding="utf-8"))
        twice = sorted(set(mine) & set(common[code]))
        if twice:
            sys.exit(f"build_site: {own.name}/{code}.json has {', '.join(twice)}, boreale-site's (i18n/)")
        merged[code] = {**mine, **common[code]}
    return merged


def check_catalogs(own: Path, optional: dict = None) -> list:
    """What is wrong with a site's catalogs (`own`) and the common ones: each
    with en.json's keys, none empty, the same {placeholders} and <em> as
    English's, no common key in a site's. `optional` gives, by language, the
    keys it may leave out (fr.json's legal_translation on boreale.dev)."""
    optional = optional or {}
    errors = []
    for where, folder_ in (("boreale-site/i18n", LIBRARY / "i18n"), (f"{own.name}", own)):
        found = {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted(folder_.glob("*.json"))}
        if sorted(found) != sorted(CODES):
            errors.append(f"{where}: catalogs {sorted(found)}, not the fifteen languages'")
        english = found.get("en", {})
        for code, catalog in found.items():
            for key in sorted(set(english) - set(catalog) - set(optional.get(code, ()))):
                errors.append(f"{where}/{code}.json: no {key}")
            for key in sorted(set(catalog) - set(english)):
                errors.append(f"{where}/{code}.json: {key} is not in en.json")
            for key, text in catalog.items():
                if not str(text).strip():
                    errors.append(f"{where}/{code}.json: {key} is empty")
                elif key in english:
                    if sorted(re.findall(r"\{[a-z_]+\}", english[key])) != sorted(re.findall(r"\{[a-z_]+\}", text)):
                        errors.append(f"{where}/{code}.json: {key}'s placeholders differ from English's")
                    if ("<em>" in english[key]) != ("<em>" in text):
                        errors.append(f"{where}/{code}.json: {key}'s <em> differs from English's")
    common = common_catalogs()
    for p in sorted(own.glob("*.json")):
        mine = json.loads(p.read_text(encoding="utf-8"))
        errors += [f"{own.name}/{p.name}: {key} is boreale-site's (i18n/)"
                   for key in sorted(set(mine) & set(common.get(p.stem, {})))]
    return errors


# ---- Boréale's sites (sites.json).

def read_sites(path: Path = LIBRARY / "sites.json") -> list:
    """sites.json's groups: [(title key or None, [{key, name, url, utm, soon}])].
    A file of another schema (or none) reads as no group; unknown fields are
    left aside."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    if not isinstance(data, dict) or data.get("schema") != SITES_SCHEMA:
        return []
    groups = []
    for group in data.get("groups", []):
        sites = [{"key": s["key"], "name": s["name"], "url": s["url"], "utm": s["utm"], "soon": bool(s.get("soon"))}
                 for s in group.get("sites", [])]
        groups.append((group.get("title"), sites))
    return groups


def ours(url: str) -> bool:
    """boreale.dev or one of its subdomains, over HTTPS."""
    u = urlparse(url)
    host = (u.hostname or "").lower()
    return u.scheme == "https" and (host == "boreale.dev" or host.endswith(".boreale.dev"))


def own_site(url: str) -> bool:
    """A link that keeps the page's origin (workbench's "liens sortants
    anonymes"): boreale.dev, its subdomains, and github.com/JigSawFr, the
    account and its repositories (that account's alone: another owner, a
    gist or GitHub's own pages are third parties)."""
    u = urlparse(url)
    path = u.path.lower()
    return ours(url) or (u.scheme == "https" and (u.hostname or "").lower() == "github.com" and
                         (path in ("/jigsawfr", "/jigsawfr/") or path.startswith("/jigsawfr/")))


LINK_OUT = re.compile(r'<a\b[^<>]*?\bhref="(https?://[^"]*)"[^<>]*>')
CHEVRON = ('<svg class="chevron" viewBox="0 0 16 16" aria-hidden="true"><path d="m4 6 4 4 4-4" fill="none" '
           'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>')


class Site:
    """One of Boréale's sites, by its key in sites.json, served at `url`
    (its sites.json address by default: a site's SITE_URL)."""

    def __init__(self, key: str, url: str = None, sites: list = None):
        self.groups = read_sites() if sites is None else sites
        entry = next((s for _, group in self.groups for s in group if s["key"] == key), None)
        if entry is None:
            sys.exit(f"build_site: {key} is not in boreale-site's sites.json")
        self.key, self.name, self.utm_source = key, entry["name"], entry["utm"]
        self.url = (url or entry["url"]).rstrip("/") + "/"
        self.host = (urlparse(self.url).hostname or "").lower()

    # -- Addresses.

    def address(self, language: str, path: str = "") -> str:
        """A page's address in a language (its home page without a path)."""
        return self.url + folder(language) + path

    def indexing(self, language: str, path: str, lost: bool = False) -> str:
        """The page's canonical address and the other languages' for search
        engines; a page that is not there (404.html) is kept out of their
        index instead."""
        if lost:
            return '<meta name="robots" content="noindex">'
        lines = [f'<link rel="canonical" href="{self.address(language, path)}">']
        lines += [f'<link rel="alternate" hreflang="{hl}" href="{self.address(code, path)}">'
                  for code, _, _, hl in LANGUAGES]
        lines.append(f'<link rel="alternate" hreflang="x-default" href="{self.address(CODES[0], path)}">')
        return "\n".join(lines)

    def sitemap(self, paths) -> str:
        """sitemap.xml: each page in each language, with every language's."""
        urls = ""
        for path in paths:
            alternates = "".join(f'    <xhtml:link rel="alternate" hreflang="{hl}" href="{self.address(code, path)}"/>\n'
                                 for code, _, _, hl in LANGUAGES)
            alternates += f'    <xhtml:link rel="alternate" hreflang="x-default" href="{self.address(CODES[0], path)}"/>\n'
            urls += "".join(f"  <url>\n    <loc>{self.address(code, path)}</loc>\n{alternates}  </url>\n"
                            for code in CODES)
        return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'
                f' xmlns:xhtml="http://www.w3.org/1999/xhtml">\n{urls}</urlset>\n')

    # -- Links out and the audience.

    def utm(self, url: str, medium: str) -> str:
        """`url` (as written in the page's HTML) tagged for Umami: a link to
        another of Boréale's sites says it comes from this one (utm_source)
        and where on the page it is (utm_medium: nav, footer, link); one to
        this site itself loses the tags it came with (a documentation page
        written for GitHub); one to anyone else stays as it is."""
        u = urlsplit(html.unescape(url))
        if not ours(u.geturl()):
            return url
        query = [(k, v) for k, v in parse_qsl(u.query, keep_blank_values=True) if not k.startswith("utm_")]
        if (u.hostname or "").lower() != self.host:
            query += [("utm_source", self.utm_source), ("utm_medium", medium)]
        tagged = urlunsplit(u._replace(query=urlencode(query)))
        return url if tagged == html.unescape(url) else html.escape(tagged, quote=True)

    @staticmethod
    def link_out(tag: str, url: str) -> str:
        """An <a> tag by the rule "liens sortants anonymes": rel="noreferrer"
        to a third party; referrerpolicy="strict-origin" and no noreferrer to
        our sites and github.com/JigSawFr."""
        tag = re.sub(r'\sreferrerpolicy="[^"]*"', "", tag)
        rel = re.search(r'\srel="([^"]*)"', tag)
        words = [w for w in (rel.group(1).split() if rel else []) if w != "noreferrer"]
        if rel:
            tag = tag[:rel.start()] + tag[rel.end():]
        if own_site(url):
            extra = ' referrerpolicy="strict-origin"'
        else:
            words.append("noreferrer")
            extra = ""
        if words:
            extra = f' rel="{" ".join(words)}"' + extra
        return tag[:-1] + extra + ">"

    def links_out(self, text: str) -> str:
        """A whole page's links out, tagged and with their referrer rule:
        before <main> the medium is "nav", in <footer> "footer", else "link"."""
        main, footer = text.find("<main"), text.find("<footer")

        def one(m):
            at = m.start()
            medium = "footer" if 0 <= footer <= at else "nav" if main < 0 or at < main else "link"
            url = self.utm(m.group(1), medium)
            tag = m.group(0).replace(f'href="{m.group(1)}"', f'href="{url}"', 1)
            return self.link_out(tag, url)

        return LINK_OUT.sub(one, text)

    def audience(self, root: str) -> str:
        """Umami's tracker, counting only from this site's own host."""
        return (f'<script src="{root}assets/umami.js" defer data-website-id="{UMAMI_WEBSITE}" '
                f'data-domains="{self.host}"></script>')

    # -- The header's menus.

    def switcher(self, language: str, catalog: dict, root: str, latest: dict = None) -> str:
        """The header's name, a button that opens the menu of Boréale's sites
        (boreale.css's and boreale.js's "site switcher"), this one marked and
        leading home, each with its latest release when `latest` has it. A
        popover: the browser closes it on Esc or a click elsewhere."""
        latest = latest or {}
        label = catalog["sites_label"]
        groups = []
        for title, sites in self.groups:
            items = []
            for s in sites:
                key = s["key"]
                here = key == self.key
                href = f"{root}{folder(language)}" if here else s["url"] + folder(language)
                soon = f'<em class="soon">{catalog["sites_soon"]}</em>' if s["soon"] else ""
                version = f' <span class="sites-version">{html.escape(latest[key])}</span>' if key in latest else ""
                current = ' aria-current="true"' if here else ""
                items.append(f'<li><a href="{href}"{current}>'
                             f'<img src="{root}assets/marks/{key}.svg" alt="" width="36" height="36">'
                             f'<span><strong>{s["name"]}{version}</strong><small>{catalog[f"sites_{key}"]}</small></span>'
                             f'{soon}</a></li>')
            heading = f'<p class="sites-title">{catalog[title]}</p>' if title else ""
            groups.append(f'        {heading}<ul>\n          ' + "\n          ".join(items) + '\n        </ul>')
        return (f'<div class="switcher">\n'
                f'      <button class="brand switch" type="button" popovertarget="sites" aria-label="{self.name} · {label}">'
                f'<img src="{root}assets/marks/{self.key}.svg" alt="" width="34" height="34">{self.name}{CHEVRON}</button>\n'
                f'      <div id="sites" class="sites" popover aria-label="{label}">\n'
                + "\n".join(groups) + '\n      </div>\n    </div>')

    @staticmethod
    def languages(language: str, catalog: dict, root: str, path: str) -> str:
        """The header's languages: a button with the page's, and under it their
        menu (a popover, as the menu of Boréale's sites), this page in each,
        its own marked. Choosing one keeps it (assets/lang.js)."""
        name = next(n for c, _, n, _ in LANGUAGES if c == language)
        options = "\n".join(
            f'        <li><a href="{root}{folder(c)}{path}" data-lang="{d or c}" lang="{hl}" hreflang="{hl}"'
            f'{" aria-current=\"true\"" if c == language else ""}>{flag(c)}{html.escape(n)}</a></li>'
            for c, d, n, hl in LANGUAGES)
        label = catalog["language"]
        return (f'<div class="settings">\n'
                f'      <button class="lang-button" type="button" popovertarget="languages" aria-label="{label} · {html.escape(name)}">'
                f'{flag(language)}<span class="lang-name">{html.escape(name)}</span>'
                f'<span class="lang-code">{language.split("-")[0].upper()}</span>{CHEVRON}</button>\n'
                f'      <ul id="languages" class="langs" popover aria-label="{label}">\n{options}\n      </ul>\n    </div>')


# ---- The built site.

def copy_assets(out: Path) -> None:
    """The common assets into <out>/assets/ (the site's own copied there
    already): fonts, marks, the tracker, lang.js, boreale.css and boreale.js.
    A site that has one of them too stops the build: it lives here."""
    target = out / "assets"
    for source in sorted(p for p in ASSETS.rglob("*") if p.is_file()):
        to = target / source.relative_to(ASSETS)
        if to.exists():
            sys.exit(f"build_site: assets/{source.relative_to(ASSETS).as_posix()} is boreale-site's")
        to.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, to)


def digest(out: Path) -> str:
    """A hash of everything built, for a scheduled build to tell whether it
    has anything new to publish."""
    sha = hashlib.sha256()
    for path in sorted(p for p in out.rglob("*") if p.is_file() and p.name != "build.sha256"):
        sha.update(path.relative_to(out).as_posix().encode() + b"\0" + path.read_bytes())
    return sha.hexdigest()
