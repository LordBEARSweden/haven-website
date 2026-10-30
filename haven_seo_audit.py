#!/usr/bin/env python3
"""Read-only technical SEO audit for Haven Nordic Health 2.0.

Run from project root: python haven_seo_audit.py
Uses only Python's standard library. Does not change project files.
"""

from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit, quote
import json
import posixpath
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "src" / "pages"
DOMAIN_FILE = ROOT / "CNAME"


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.links = []
        self.assets = []
        self.headings = []
        self.mains = 0
        self.titles = []
        self.description = []
        self.canonical = []
        self.og_url = []
        self.json_ld = []
        self._title = False
        self._json_script = False
        self._json_buffer = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get('id'):
            self.ids.append(a['id'])
        if tag == 'a' and a.get('name'):
            self.ids.append(a['name'])
        if tag == 'a' and 'href' in a:
            self.links.append(a['href'] or '')
        if tag == 'img':
            self.assets.append((a.get('src', ''), 'image'))
            if 'alt' not in a:
                self.assets.append(('', 'missing-alt'))
        if tag in ('script', 'source', 'iframe', 'video') and a.get('src'):
            self.assets.append((a['src'], tag))
        if tag == 'video' and a.get('poster'):
            self.assets.append((a['poster'], 'poster'))
        if tag == 'link':
            rel = (a.get('rel') or '').lower().split()
            if any(x in rel for x in ('stylesheet', 'icon', 'manifest', 'apple-touch-icon')) and a.get('href'):
                self.assets.append((a['href'], 'link asset'))
            if 'canonical' in rel:
                self.canonical.append(a.get('href', ''))
        if tag == 'meta':
            if (a.get('name') or '').lower() == 'description':
                self.description.append(a.get('content', ''))
            prop = (a.get('property') or '').lower()
            if prop == 'og:url':
                self.og_url.append(a.get('content', ''))
            if prop == 'og:image':
                self.assets.append((a.get('content', ''), 'og:image'))
        if tag == 'title':
            self._title = True
        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            self.headings.append(int(tag[1]))
        if tag == 'main':
            self.mains += 1
        if tag == 'script' and (a.get('type') or '').lower() == 'application/ld+json':
            self._json_script = True
            self._json_buffer = []

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == 'title':
            self._title = False
        if tag == 'script' and self._json_script:
            self.json_ld.append(''.join(self._json_buffer))
            self._json_script = False
            self._json_buffer = []

    def handle_data(self, data):
        if self._title:
            self.titles.append(data)
        if self._json_script:
            self._json_buffer.append(data)


def check_target(value, current, host):
    """Return (relative file path, fragment), or None for external/special URLs."""
    value = value.strip()
    if not value:
        return None
    parts = urlsplit(value)
    if parts.scheme and parts.scheme.lower() not in ('http', 'https'):
        return None
    if parts.hostname and parts.hostname.lower() not in (host, host.removeprefix('www.'), 'www.' + host.removeprefix('www.')):
        return None
    if not parts.path:
        return current, unquote(parts.fragment)

    raw = unquote(parts.path)
    base = '' if raw.startswith('/') else current.parent.as_posix()
    if base == '.':
        base = ''
    relative = posixpath.normpath(posixpath.join(base, raw.lstrip('/')))
    if relative == '..' or relative.startswith('../'):
        return 'OUTSIDE_ROOT', unquote(parts.fragment)
    if raw.endswith('/') or relative == '.':
        relative = posixpath.join(relative if relative != '.' else '', 'index.html')
    candidate = ROOT / relative
    if candidate.is_dir():
        relative = posixpath.join(relative, 'index.html')
    return Path(relative), unquote(parts.fragment)


def main():
    errors, warnings = [], []
    if not SOURCE.is_dir() or not DOMAIN_FILE.is_file():
        print('ERROR: Place haven_seo_audit.py in the V2 project root (beside build.py and CNAME).')
        return 2

    host = DOMAIN_FILE.read_text(encoding='utf-8').strip().lower()
    if not host:
        print('ERROR: CNAME is empty.')
        return 2
    base_url = 'https://' + host
    expected_sources = sorted(SOURCE.rglob('*.html'))
    parsed = {}
    link_refs = []
    asset_refs = []
    expected_urls = set()
    titles = {}

    for source in expected_sources:
        relative = source.relative_to(SOURCE)
        output = ROOT / relative
        relstr = relative.as_posix()
        canonical_path = relstr[:-10] if relative.name == 'index.html' else relstr
        canonical = base_url + '/' + quote(canonical_path, safe='/')
        expected_urls.add(canonical)
        if not output.is_file():
            errors.append(f'{relstr}: generated HTML is missing (run python build.py).')
            continue
        doc = PageParser()
        try:
            doc.feed(output.read_text(encoding='utf-8'))
            doc.close()
        except Exception as exc:
            errors.append(f'{relstr}: cannot parse HTML: {exc}')
            continue
        parsed[relative] = doc

        title = ''.join(doc.titles).strip()
        if not title:
            errors.append(f'{relstr}: missing <title>.')
        else:
            titles.setdefault(title, []).append(relstr)
        if len(doc.description) != 1 or not doc.description[0].strip():
            warnings.append(f'{relstr}: missing, empty or duplicate meta description.')
        if doc.canonical != [canonical]:
            errors.append(f'{relstr}: canonical mismatch: {doc.canonical!r} (expected {canonical}).')
        if doc.og_url and doc.og_url != [canonical]:
            warnings.append(f'{relstr}: og:url does not match canonical.')
        if doc.headings.count(1) != 1:
            warnings.append(f'{relstr}: {doc.headings.count(1)} H1 headings (expected 1).')
        if doc.mains != 1:
            warnings.append(f'{relstr}: {doc.mains} <main> elements (expected 1).')
        for identity, count in Counter(doc.ids).items():
            if count > 1:
                errors.append(f'{relstr}: duplicate id #{identity} ({count} occurrences).')
        for raw_link in doc.links:
            link_refs.append((relative, raw_link))
        for raw_asset, kind in doc.assets:
            if kind == 'missing-alt':
                warnings.append(f'{relstr}: image without alt attribute (decorative images should use alt="").')
            elif raw_asset:
                asset_refs.append((relative, raw_asset, kind))
            else:
                warnings.append(f'{relstr}: empty {kind} source.')
        for i, block in enumerate(doc.json_ld, start=1):
            try:
                json.loads(block)
            except json.JSONDecodeError as exc:
                errors.append(f'{relstr}: invalid JSON-LD block {i}: {exc.msg}.')

    for title, paths in titles.items():
        if len(paths) > 1:
            warnings.append(f'duplicate page title {title!r}: {", ".join(paths)}.')

    for current, raw_link in link_refs:
        target = check_target(raw_link, current, host)
        if target is None:
            if raw_link.strip().lower().startswith('javascript:'):
                warnings.append(f'{current.as_posix()}: javascript: link ({raw_link}).')
            continue
        dest, anchor = target
        if dest == 'OUTSIDE_ROOT':
            errors.append(f'{current.as_posix()}: link escapes website root: {raw_link}.')
            continue
        if not (ROOT / dest).is_file():
            errors.append(f'{current.as_posix()}: broken internal link {raw_link} (resolved {dest.as_posix()}).')
        elif anchor and dest in parsed and anchor not in parsed[dest].ids:
            warnings.append(f'{current.as_posix()}: anchor #{anchor} missing in {dest.as_posix()}.')

    for current, raw_asset, kind in asset_refs:
        target = check_target(raw_asset, current, host)
        if target is None:
            continue
        dest, _ = target
        if dest == 'OUTSIDE_ROOT' or not (ROOT / dest).is_file():
            errors.append(f'{current.as_posix()}: missing {kind}: {raw_asset}.')

    sitemap_file = ROOT / 'sitemap.xml'
    if not sitemap_file.is_file():
        warnings.append('Missing sitemap.xml.')
    else:
        try:
            xml = ET.parse(sitemap_file)
            found = [el.text.strip() for el in xml.iter() if el.tag.endswith('}loc') and el.text]
            if not found:
                found = [el.text.strip() for el in xml.iter('loc') if el.text]
            if len(found) != len(set(found)):
                warnings.append('sitemap.xml contains duplicate URLs.')
            missing = expected_urls.difference(found)
            extras = set(found).difference(expected_urls)
            for url in sorted(missing):
                warnings.append(f'sitemap.xml missing page: {url}')
            for url in sorted(extras):
                warnings.append(f'sitemap.xml contains URL outside current source pages: {url}')
        except (ET.ParseError, OSError) as exc:
            errors.append(f'sitemap.xml invalid or unreadable: {exc}')

    if not (ROOT / 'robots.txt').is_file():
        warnings.append('Missing robots.txt.')

    print('HAVEN 2.0 — TECHNICAL SEO AUDIT')
    print(f'Source pages: {len(expected_sources)} | Generated pages checked: {len(parsed)}')
    print(f'Internal links inspected: {len(link_refs)} | File/image references: {len(asset_refs)}')
    print(f'Errors: {len(errors)} | Warnings: {len(warnings)}')
    if errors:
        print('\nERRORS (fix before launch)')
        for issue in sorted(set(errors)):
            print('  - ' + issue)
    if warnings:
        print('\nWARNINGS (review individually; may be intentional)')
        for issue in sorted(set(warnings)):
            print('  - ' + issue)
    if not errors and not warnings:
        print('\nNo issues detected in the checks performed.')
    print('\nScope: local HTML links, link anchors, image/script/CSS files, H1/main structure,')
    print('title/description/canonical, JSON-LD syntax, and sitemap contents.')
    print('Not checked: external URLs, CSS background images, runtime JavaScript, accessibility')
    print('contrast, actual Google indexing, or server-side redirects.')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
