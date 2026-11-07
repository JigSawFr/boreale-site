#!/usr/bin/env python3
"""The links out of a built site, followed: which of them lead nowhere now.

    python3 library/boreale-site/tools/check_links.py <site-dir> [--skip-host HOST]… [--timeout SECONDS]

Reads every page of the built folder, takes each `<a href>` to another site (http or https), asks for it once each (HEAD,
then GET where a server refuses HEAD, redirects followed) and says which are broken: a 404 or 410, another 4xx or 5xx
that stays after a second try, an address that does not resolve, a certificate that does not hold. A server that turns a
program away (401, 403, 429, 999) is not called broken: it answers, and its page may be fine in a browser. Placeholder
addresses (example.org, localhost, private networks) are left out. The exit code is 1 when a link is broken.

It reaches the network, so it is not a build check (check.pages() is): the sites run it weekly (workflows/links.yml).
Standard library only.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import ipaddress
import socket
import ssl
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urldefrag, urlparse

SOFT = {401, 403, 429, 999}  # a server that turns a program away
PLACEHOLDERS = ("example.org", "example.com", "example.net", "localhost")
AGENT = "Mozilla/5.0 (compatible; boreale-site link check; +https://boreale.dev/)"


class Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.found: list[str] = []

    def handle_starttag(self, tag: str, attrs: list) -> None:
        if tag == "a":
            href = dict(attrs).get("href") or ""
            if href.startswith(("http://", "https://")):
                self.found.append(urldefrag(href)[0])


def skipped(url: str, hosts: tuple) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if not host or host in hosts or any(host == p or host.endswith("." + p) for p in PLACEHOLDERS + hosts):
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_private or address.is_loopback or address.is_link_local


def collect(site: Path, hosts: tuple = ()) -> dict:
    """The addresses out of the site's pages, each with the pages that hold it."""
    out: dict[str, list[str]] = {}
    for page in sorted(site.rglob("*.html")):
        parser = Links()
        parser.feed(page.read_text(encoding="utf-8"))
        for url in parser.found:
            if not skipped(url, hosts):
                holders = out.setdefault(url, [])
                name = page.relative_to(site).as_posix()
                if name not in holders:
                    holders.append(name)
    return out


def ask(url: str, method: str, timeout: float) -> int:
    request = urllib.request.Request(url, method=method, headers={"User-Agent": AGENT, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 (http and https only)
            return response.status
    except urllib.error.HTTPError as error:
        return error.code


def verdict(url: str, timeout: float = 15.0) -> tuple[str, str]:
    """("ok" | "soft" | "broken", what was seen) for one address; two tries before it says broken."""
    seen = ""
    for attempt in range(2):
        try:
            status = ask(url, "HEAD", timeout)
            if status >= 400:
                status = ask(url, "GET", timeout)  # some servers refuse HEAD, with any error
            if status < 400:
                return "ok", str(status)
            if status in SOFT:
                return "soft", str(status)
            seen = str(status)
            if status in (404, 410):
                return "broken", seen
        except (urllib.error.URLError, ssl.SSLError, socket.timeout, ConnectionError, OSError) as error:
            reason = getattr(error, "reason", error)
            seen = type(reason).__name__ + ": " + str(reason)[:80]
    return "broken", seen


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("site", type=Path)
    parser.add_argument("--skip-host", action="append", default=[], help="a host not asked (and its subdomains)")
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args(argv)
    links = collect(args.site, tuple(h.lower() for h in args.skip_host))
    if not links:
        print(f"check_links: no link out in {args.site}, nothing to follow")
        return 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = dict(zip(links, pool.map(lambda u: verdict(u, args.timeout), links)))
    broken = {u: r for u, r in results.items() if r[0] == "broken"}
    soft = [u for u, r in results.items() if r[0] == "soft"]
    for url, (_, seen) in broken.items():
        print(f"broken: {url} ({seen}), on {', '.join(links[url][:3])}" + (" …" if len(links[url]) > 3 else ""))
    for url in soft:
        print(f"turned the program away, not counted: {url} ({results[url][1]})")
    print(f"check_links: {len(links)} addresses, {len(broken)} broken, {len(soft)} that turn programs away")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
