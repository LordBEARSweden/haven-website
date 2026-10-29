#!/usr/bin/env python3
# Haven Nordic Health – migrering av de åtta äldre bloggartiklarna.
# Python-standardbiblioteket enbart. Ingen ändring utan --write.
import argparse
from dataclasses import dataclass, field
from datetime import date
from html import escape, unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote
import json
import re
import shutil
import sys

FILES = (
    'granser-utan-skuld.html',
    'slappa-kontrollen.html',
    'narvaro-och-aterhamtning-i-vardagen.html',
    'nervsystem-och-balans.html',
    'somn-och-aterhamtning.html',
    'vanskap-och-enegi.html',  # Behåll den ursprungliga stavningen i URL:en.
    'fokus-i-vardagen.html',
    'stress-i-vardagen.html',
)
MONTHS = ('', 'JANUARI', 'FEBRUARI', 'MARS', 'APRIL', 'MAJ', 'JUNI',
          'JULI', 'AUGUSTI', 'SEPTEMBER', 'OKTOBER', 'NOVEMBER', 'DECEMBER')
VOID_TAGS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link',
             'meta', 'param', 'source', 'track', 'wbr'}

@dataclass
class Node:
    tag: str
    attrs: dict
    start: int
    open_end: int
    end: int | None = None
    children: list = field(default_factory=list)

    def has(self, cls):
        return cls in self.attrs.get('class', '').split()

class Parser(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.src = source
        self.line_offsets = [0]
        for ln in source.splitlines(keepends=True):
            self.line_offsets.append(self.line_offsets[-1] + len(ln))
        self.stack = []
        self.nodes = []
        self.feed(source)
        self.close()

    def location_offset(self):
        line, col = self.getpos()
        return self.line_offsets[line - 1] + col

    def handle_starttag(self, tag, attrs):
        offset = self.location_offset()
        node = Node(tag, dict(attrs), offset, offset + len(self.get_starttag_text()))
        if self.stack:
            self.stack[-1].children.append(node)
        self.nodes.append(node)
        if tag in VOID_TAGS:
            node.end = node.open_end
        else:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if self.stack and self.stack[-1].tag == tag:
            self.stack[-1].end = self.stack[-1].open_end
            self.stack.pop()

    def handle_endtag(self, tag):
        matches = [i for i,n in enumerate(self.stack) if n.tag == tag]
        if not matches:
            return
        idx = matches[-1]
        pos = self.location_offset()
        end = self.src.find('>', pos) + 1
        for n in self.stack[idx+1:]:
            n.end = pos
        self.stack[idx].end = end
        self.stack = self.stack[:idx]

    def one(self, tag=None, cls=None):
        return next((n for n in self.nodes if (tag is None or n.tag == tag)
                     and (cls is None or n.has(cls)) and n.end is not None), None)

    def raw(self, node):
        return self.src[node.start:node.end]


def text_from_html(src):
    class Text(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.out = []
        def handle_data(self, data):
            self.out.append(data)
        def handle_entityref(self, name):
            self.out.append(unescape('&'+name+';'))
    p = Text(); p.feed(src)
    return ' '.join(' '.join(p.out).split())


def descendants(node):
    for child in node.children:
        yield child
        yield from descendants(child)


def get_meta(parser, name):
    for node in parser.nodes:
        if node.tag == 'meta' and (node.attrs.get('property') == name or node.attrs.get('name') == name):
            return unescape(node.attrs.get('content', '').strip())
    return ''


def format_date(raw):
    parsed = date.fromisoformat(raw)
    return f'{parsed.day} {MONTHS[parsed.month]} {parsed.year}'


def convert(original, filename):
    p = Parser(original)
    main = p.one('main', 'article-content')
    intro = p.one('section', 'blog-intro')
    if not main or not intro:
        raise ValueError('Hittade inte <main class="article-content"> och <section class="blog-intro">')
    if not (main.start < intro.start < intro.end <= main.end):
        raise ValueError('Artikelns inledning ligger inte inne i huvudtexten')
    h1 = next((n for n in descendants(intro) if n.tag == 'h1'), None)
    date_node = next((n for n in descendants(intro) if n.has('article-date')), None)
    if not h1 or not date_node:
        raise ValueError('Artikeln saknar h1 eller publiceringsdatum i inledningen')
    heading = text_from_html(p.raw(h1))
    raw_date = text_from_html(p.raw(date_node))
    try:
        pretty_date = format_date(raw_date)
    except ValueError as e:
        raise ValueError(f'Publiceringsdatum är inte ISO-formaterat: {raw_date}') from e

    meta_node = next((n for n in main.children if n.tag == 'script' and n.has('post-meta')), None)
    post_meta = {}
    if meta_node:
        try:
            post_meta = json.loads(original[meta_node.open_end:meta_node.end].split('</script', 1)[0])
        except (ValueError, TypeError):
            raise ValueError('Ogiltig post-meta JSON')
    seo_title = get_meta(p, 'og:title') or str(post_meta.get('title','')) or heading
    desc = str(post_meta.get('description','')) or get_meta(p, 'og:description')
    if not desc:
        raise ValueError('Artikeln saknar beskrivning i post-meta och og:description')
    desc = ' '.join(desc.split())
    if any(c in seo_title + desc for c in ('\r', '\n')):
        raise ValueError('Metadata innehåller oväntade radbrytningar')

    kept = []
    first_picture = True
    for child in main.children:
        if child is intro or child is meta_node:
            continue
        raw = p.raw(child)
        if child.tag == 'figure':
            klass = ' v2-journal-image-wrap--cover' if first_picture else ''
            first_picture = False
            kept.append(f'    <div class="v2-journal-image-wrap{klass}">\n{raw}\n    </div>')
        elif child.has('call-to-action'):
            kept.append(f'    <div class="v2-journal-reflection">\n{raw}\n    </div>')
        else:
            kept.append(f'    <div class="v2-journal-copy">\n{raw}\n    </div>')
    if not kept:
        raise ValueError('Ingen artikeltext att migrera')

    # Upptäck om det finns direkt artikeltext utanför barn-taggarna.
    pieces = sorted(main.children, key=lambda n:n.start)
    prev = main.open_end
    for n in pieces:
        gap = original[prev:n.start]
        # Maskera kommentarer men behåll teckenpositioner för korrekta radnummer.
        gap = re.sub(r'<!--.*?-->', lambda m: ' ' * len(m.group()), gap, flags=re.S)
        if gap.strip():
            pos = prev + len(gap) - len(gap.lstrip())
            line = original.count('\n', 0, pos) + 1
            excerpt = ' '.join(gap.strip().split())[:160]
            raise ValueError(f'Rad {line} i originalfilen: innehåll mellan HTML-avsnitt: {excerpt!r}')
        prev = n.end
    trailing = original[prev:main.end]
    trailing = re.sub(r'</main\s*>\s*$', '', trailing, flags=re.I)
    trailing = re.sub(r'<!--.*?-->', lambda m: ' ' * len(m.group()), trailing, flags=re.S)
    if trailing.strip():
        pos = prev + len(trailing) - len(trailing.lstrip())
        line = original.count('\n', 0, pos) + 1
        excerpt = ' '.join(trailing.strip().split())[:160]
        raise ValueError(f'Rad {line} i originalfilen: oväntat innehåll efter sista avsnittet: {excerpt!r}')

    imgs = [n.attrs.get('src', '') for n in descendants(main) if n.tag == 'img' and n.attrs.get('src')]
    out_imgs = []
    for el in kept:
        for m in re.finditer(r'<img\s+[^>]*src=["\']([^"\']+)', el, re.I):
            out_imgs.append(unescape(m.group(1)))
    if len(imgs) != len(out_imgs) or sorted(map(unescape, imgs)) != sorted(out_imgs):
        raise ValueError('Bildreferenserna matchar inte originalet')

    share = p.one('div', 'share-buttons')
    share_markup = p.raw(share) if share else ''
    raw_share_script = ('https://static.addtoany.com/menu/page.js' in original)
    intro_markup = ('      <p class="v2-journal-intro">'+escape(desc)+'</p>')
    share_html = ('      <div class="v2-journal-share">\n'+share_markup+'\n      </div>\n') if share_markup else ''
    add_to_any_script = ('<script async src="https://static.addtoany.com/menu/page.js"></script>\n' if share_markup and raw_share_script else '')
    header_title = seo_title if 'Haven Nordic Health' in seo_title else f'{seo_title} | Haven Nordic Health'
    if '-->' in header_title + desc:
        raise ValueError('Ogiltigt tecken i sidans metadata')
    target = f'''<!-- HAVEN_PAGE
title: {header_title}
description: {desc}
nav: blogg
styles: css/pages/blog-article.css
-->

<article class="v2-journal-article">
  <header class="v2-journal-hero v2-section">
    <div class="v2-journal-hero-inner">
      <nav class="v2-journal-breadcrumb" aria-label="Brödsmulor">
        <a href="{{{{root}}}}blog/index.html">Blogg</a><span aria-hidden="true">/</span><span>Artikel</span>
      </nav>
      <p class="v2-kicker">HAVEN JOURNAL <span aria-hidden="true">/</span> <time datetime="{raw_date}">{pretty_date}</time></p>
      <h1>{escape(heading)}</h1>
{intro_markup}
    </div>
  </header>

  <div class="v2-journal-content v2-section">
{chr(10).join(kept)}
  </div>

  <footer class="v2-journal-footer v2-section">
    <div class="v2-journal-footer-inner">
{share_html}      <a class="v2-journal-back" href="{{{{root}}}}blog/index.html"><span aria-hidden="true">←</span> Tillbaka till bloggen</a>
    </div>
  </footer>
</article>

{add_to_any_script}'''
    # Säkerställ att originalets alla artikelsektioner/figurer verkligen finns med.
    for original_child in main.children:
        if original_child not in (intro, meta_node) and p.raw(original_child) not in target:
            raise ValueError('Ett avsnitt saknas eller har förändrats')
    images = [unescape(s) for s in imgs]
    return target, heading, raw_date, images, len(kept)


def main():
    arg = argparse.ArgumentParser(description='Migrera Haven Blogg: förhandsgranska som standard; --write för att skapa nya filer.')
    arg.add_argument('--write', action='store_true', help='Skapa de nya källfilerna efter kontroll')
    args = arg.parse_args()
    v2 = Path(__file__).resolve().parent.parent
    old = v2.parent/'haven-website'
    if not (v2/'build.py').exists():
        sys.exit('FEL: Verktyget måste ligga i haven-website-v2/tools/ (build.py saknas).')
    if not (old/'blog').exists():
        sys.exit(f'FEL: Gamla arbetskopian hittades inte: {old}')
    if not (v2/'css/pages/blog-article.css').exists():
        sys.exit('FEL: Den godkända artikel-CSS-filen saknas. Installera den först.')

    todo = []
    missing_images = []
    errors = []
    for filename in FILES:
        src = old/'blog'/filename
        dst = v2/'src/pages/blog'/filename
        if not src.is_file():
            errors.append(f'{filename}: originalfil saknas i main-arbetskopian')
            continue
        if dst.exists():
            errors.append(f'{filename}: källfilen finns redan, vill inte skriva över')
            continue
        try:
            converted, heading, published, images, blocks = convert(src.read_text(encoding='utf-8-sig'), filename)
            imgs_to_copy = []
            for img in images:
                if img.startswith('../images/'):
                    rel = Path(unquote(img[3:]))
                    target_img = v2 / rel
                    old_img = old / rel
                    if not target_img.exists():
                        if old_img.is_file():
                            imgs_to_copy.append((old_img, target_img))
                        else:
                            missing_images.append(f'{filename}: bild saknas i båda arbetskopiorna: {img}')
                elif img.startswith(('http://','https://','data:')):
                    continue
                else:
                    missing_images.append(f'{filename}: oväntad bildadress: {img}')
            todo.append((filename, dst, converted, imgs_to_copy, heading, published, images, blocks))
        except Exception as exc:
            errors.append(f'{filename}: {exc}')
    if missing_images or errors:
        print('AVBRUTET – inga filer har ändrats. Åtgärda följande först:')
        for error in errors+missing_images:
            print(' •', error)
        return 1

    print(f'Kontroll OK: {len(todo)} artiklar. Ingen befintlig fil kommer att skrivas över.')
    for filename, dst, content, imgs_to_copy, heading, published, images, blocks in todo:
        print(f' • {filename} | {published} | {blocks} innehållsblock | {len(images)} bilder | {len(imgs_to_copy)} bilder att kopiera')
    if not args.write:
        print('\nINGA ÄNDRINGAR GJORDA. Kör samma kommando med --write efter att du granskat listan.')
        return 0
    for filename, dst, converted, imgs_to_copy, *_ in todo:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(converted, encoding='utf-8', newline='\n')
        for original_image, target_image in imgs_to_copy:
            target_image.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(original_image, target_image)
    print(f'\nKLART: {len(todo)} nya källfiler skapade. Kör python build.py, granska på mobil och dator, och gör INGEN commit innan granskning.')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
