<!--
The title is a conventional commit with a scope (feat(menu): …, fix(links): …).
-->

## What this changes, and why

<!-- The diff says what; this says what it is for. -->

## How it was verified

<!-- Beyond CI: a site built with it, its pages looked at. -->

## Checklist

- [ ] `python3 -m unittest discover -s tests` passes
- [ ] A text added is in all 15 catalogs (`i18n/`), translated
- [ ] A site added: `sites.json`, its mark in `assets/marks/`, `sites_<key>` in the catalogs
