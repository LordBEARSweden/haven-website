#!/usr/bin/env python3
"""Haven 2.0: build static HTML from reusable partials. Only Python stdlib.

Run from project root:
    py -3 build.py
or:
    python build.py

This script writes ONLY paths matching src/pages/**/*.html.
If src/pages/index.html exists, generated index.html at the project root is updated.
Other Haven 1.0 pages are not modified until deliberately migrated.
"""

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent
PAGES = ROOT / 'src' / 'pages'
PARTIALS = ROOT / 'src' / 'partials'

REQUIRED_PARTIALS = ('header', 'footer', 'analytics', 'booking-widget')
fragments = {
    key: (PARTIALS / (key + '.html')).read_text(encoding='utf-8')
    for key in REQUIRED_PARTIALS
}


def build_page(source: Path) -> Path:
    relative = source.relative_to(PAGES)
    destination = ROOT / relative
    root_prefix = '../' * (len(relative.parts) - 1)
    page_key = relative.stem  # index -> home; future pages can set a key below
    nav_key = 'home' if relative == Path('index.html') else page_key

    template = source.read_text(encoding='utf-8')
    for fragment_key, fragment in fragments.items():
        template = template.replace('{{' + fragment_key.replace('-', '_') + '}}', fragment)

    # On all pages, template-based navigation can mark only its active link.
    template = re.sub(
        r'\{\{active:([a-z0-9_-]+)\}\}',
        lambda m: ' aria-current="page"' if m.group(1) == nav_key else '',
        template
    )
    template = template.replace('{{root}}', root_prefix)

    unresolved = re.findall(r'\{\{[^{}]+\}\}', template)
    if unresolved:
        raise ValueError(f'Unknown template placeholder(s) in {relative}: {unresolved}')

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(template, encoding='utf-8')
    return destination


if __name__ == '__main__':
    sources = sorted(PAGES.rglob('*.html'))
    if not sources:
        raise SystemExit('No source HTML pages found in src/pages/')
    for source in sources:
        destination = build_page(source)
        print(f'Built {destination.relative_to(ROOT)}')
