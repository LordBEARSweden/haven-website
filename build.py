#!/usr/bin/env python3
"""Haven Nordic Health 2.0 - Static site builder."""

from pathlib import Path
from html import escape
from html.parser import HTMLParser
from datetime import date
from urllib.parse import quote, unquote, urljoin, urlsplit, urlunsplit
import json
import re

ROOT = Path(__file__).resolve().parent
PAGES = ROOT / "src" / "pages"
PARTIALS = ROOT / "src" / "partials"
LAYOUT = ROOT / "src" / "layouts" / "base.html"
SITE_URL = "https://" + (ROOT / "CNAME").read_text(encoding="utf-8").strip()
SITE_NAME = "Haven Nordic Health"
# The public About page identifies the author of Havens articles.
ARTICLE_AUTHOR = "Björn Andersson"
ARTICLE_AUTHOR_URL = f"{SITE_URL}/om.html"
# Existing 512 x 512 brand icon. A dedicated sharing image can replace it later.
DEFAULT_SOCIAL_IMAGE = "images/android-chrome-512x512.png"

REQUIRED_PARTIALS = (
    "header",
    "footer",
    "analytics",
    "booking-widget",
)


def load_partials():
    return {
        name: (PARTIALS / f"{name}.html").read_text(encoding="utf-8")
        for name in REQUIRED_PARTIALS
    }


def parse_page(source_text):
    """Read metadata and content from a new page template."""

    match = re.match(
        r"^\s*<!--\s*HAVEN_PAGE\s*\n(.*?)\n-->\s*",
        source_text,
        flags=re.DOTALL,
    )

    if not match:
        raise ValueError("Missing HAVEN_PAGE metadata.")

    metadata = {}

    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            metadata[key.strip().lower()] = value.strip()

    for key in ("title", "description", "nav"):
        if not metadata.get(key):
            raise ValueError(f"Missing page metadata: {key}")

    content = source_text[match.end():]

    return metadata, content


class DocumentHeadParser(HTMLParser):
    """Read existing head metadata without relying on HTML attribute order."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_head = False
        self.in_title = False
        self.title_parts = []
        self.description = ""
        self.meta_keys = set()

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "head":
            self.in_head = True
        elif self.in_head and tag == "title":
            self.in_title = True
        elif self.in_head and tag == "meta":
            attrs = dict(attrs)
            kind = (attrs.get("property") or attrs.get("name") or "").lower()
            if kind:
                self.meta_keys.add(kind)
            if kind == "description":
                self.description = attrs.get("content") or ""

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag == "title":
            self.in_title = False
        elif tag == "head":
            self.in_head = False

    def handle_data(self, data):
        if self.in_title:
            self.title_parts.append(data)

    @property
    def title(self):
        return "".join(self.title_parts).strip()



class ArticleMediaParser(HTMLParser):
    """Read publication date and representative image from article markup.

    Photo credit lines remain in the article; image use does not imply that
    the article author or publisher owns the photograph.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.date_published = None
        self.image_src = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "time" and self.date_published is None:
            candidate = (attrs.get("datetime") or "").strip()
            try:
                # Preserve the source's date; do not fabricate a time of day.
                if len(candidate) == 10 and date.fromisoformat(candidate):
                    self.date_published = candidate
            except ValueError:
                pass
        elif tag == "img" and self.image_src is None:
            candidate = (attrs.get("src") or "").strip()
            if candidate and not candidate.startswith(("data:", "blob:", "#")):
                self.image_src = candidate


def article_media(source_text, canonical_url, root_prefix):
    """Convert the first article image to an absolute, URL-encoded URL."""
    parser = ArticleMediaParser()
    parser.feed(source_text)
    image_url = None
    if parser.image_src:
        src = parser.image_src.replace("{{root}}", root_prefix)
        url = urljoin(canonical_url, src)
        parsed = urlsplit(url)
        if parsed.scheme in ("http", "https") and parsed.netloc:
            # Names such as 'Höstfika vid den gyllene sjön-2.png' need encoding.
            image_url = urlunsplit((
                parsed.scheme, parsed.netloc,
                quote(unquote(parsed.path), safe="/-_.~"),
                parsed.query, parsed.fragment,
            ))
    return parser.date_published, image_url



def collect_blog_articles():
    """Read and sort blog articles by publication date."""
    articles = []

    for source in (PAGES / "blog").glob("*.html"):
        if source.name == "index.html":
            continue

        metadata, content = parse_page(
            source.read_text(encoding="utf-8")
        )

        parser = ArticleMediaParser()
        parser.feed(content)

        if not parser.date_published:
            raise ValueError(
                f"Missing publication date: {source.name}"
            )

        if not parser.image_src:
            raise ValueError(
                f"Missing article image: {source.name}"
            )

        articles.append({
            "title": metadata["title"].removesuffix(
                f" | {SITE_NAME}"
            ),
            "description": (
                metadata.get("excerpt")
                or metadata["description"]
            ),
            "date": date.fromisoformat(parser.date_published),
            "image": parser.image_src,
            "url": f"{{{{root}}}}blog/{source.name}",
        })

    articles.sort(
        key=lambda article: article["date"],
        reverse=True
    )

    return articles

def render_blog_sections():
    """Generate featured article and archive cards."""
    articles = collect_blog_articles()

    if not articles:
        raise ValueError("No blog articles found.")

    months = (
        "januari", "februari", "mars", "april",
        "maj", "juni", "juli", "augusti",
        "september", "oktober", "november", "december"
    )

    def format_date(value):
        return f"{value.day} {months[value.month - 1]} {value.year}"

    latest = articles[0]

    feature = f'''
      <a class="v2-blog-feature"
         href="{escape(latest["url"], quote=True)}"
         aria-label="Läs: {escape(latest["title"], quote=True)}">
        <div class="v2-blog-feature-visual" aria-hidden="true">
          <img class="v2-blog-feature-image"
               src="{escape(latest["image"], quote=True)}"
               alt="" decoding="async">
          <span class="v2-blog-art-word">HAVEN JOURNAL</span>
        </div>
        <div class="v2-blog-feature-copy">
          <span class="v2-blog-overline">SENASTE ARTIKELN
            <span aria-hidden="true">/</span>
            <time datetime="{latest["date"].isoformat()}">{format_date(latest["date"])}</time>
          </span>
          <h2>{escape(latest["title"])}</h2>
          <p>{escape(latest["description"])}</p>
          <span class="v2-blog-read">Läs artikeln <span aria-hidden="true">↗</span></span>
        </div>
      </a>'''

    cards = []

    for index, article in enumerate(articles[1:], start=1):
        cards.append(f'''
        <a class="v2-blog-card"
           href="{escape(article["url"], quote=True)}"
           aria-label="Läs: {escape(article["title"], quote=True)}">
          <div class="v2-blog-card-top">
            <span class="v2-blog-card-index">{index:02d}</span>
            <time datetime="{article["date"].isoformat()}">{format_date(article["date"])}</time>
          </div>
          <h3>{escape(article["title"])}</h3>
          <p>{escape(article["description"])}</p>
          <span class="v2-blog-card-link">Läs mer <span aria-hidden="true">↗</span></span>
        </a>''')

    return feature, "\n".join(cards)

def create_social_tags(title, description, canonical_url, relative, image_path):
    """Create Open Graph and Twitter summary tags for one published URL."""
    image_path = image_path.lstrip("/")
    image_url = f"{SITE_URL}/{quote(image_path, safe='/')}"
    is_article = len(relative.parts) > 1 and relative.name != "index.html"
    og_type = "article" if is_article else "website"
    fields = [
        ("property", "og:locale", "sv_SE"),
        ("property", "og:type", og_type),
        ("property", "og:site_name", SITE_NAME),
        ("property", "og:title", title),
        ("property", "og:description", description),
        ("property", "og:url", canonical_url),
        ("property", "og:image", image_url),
        ("property", "og:image:type", "image/png" if image_path.lower().endswith(".png") else "image/jpeg"),
        ("property", "og:image:alt", SITE_NAME),
        ("name", "twitter:card", "summary"),
        ("name", "twitter:title", title),
        ("name", "twitter:description", description),
        ("name", "twitter:image", image_url),
    ]
    return fields


def render_missing_social_tags(fields, existing_keys):
    lines = []
    for attribute, key, value in fields:
        if key.lower() in existing_keys or not value:
            continue
        lines.append(
            f'  <meta {attribute}="{key}" content="{escape(value, quote=True)}">'
        )
    return "\n".join(lines)



def create_structured_data(title, description, canonical_url, relative, article_date, article_image):
    """Build JSON-LD from confirmed page metadata and article source markup."""
    homepage_url = f"{SITE_URL}/"
    organization_id = f"{homepage_url}#organization"
    website_id = f"{homepage_url}#website"
    webpage_id = f"{canonical_url}#webpage"

    graph = []

    if relative == Path("index.html"):
        graph.extend([
            {
                "@type": "Organization",
                "@id": organization_id,
                "name": SITE_NAME,
                "url": homepage_url,
                "logo": f"{SITE_URL}/{DEFAULT_SOCIAL_IMAGE}",
            },
            {
                "@type": "WebSite",
                "@id": website_id,
                "url": homepage_url,
                "name": SITE_NAME,
                "inLanguage": "sv-SE",
                "publisher": {"@id": organization_id},
            },
        ])

    webpage = {
        "@type": "WebPage",
        "@id": webpage_id,
        "url": canonical_url,
        "name": title,
        "inLanguage": "sv-SE",
        "isPartOf": {"@id": website_id},
    }
    if description:
        webpage["description"] = description
    graph.append(webpage)

    if len(relative.parts) == 2 and relative.suffix == ".html":
        category = relative.parts[0]
        if category in ("blog", "kunskap") and relative.name != "index.html":
            article_id = f"{canonical_url}#article"
            webpage["mainEntity"] = {"@id": article_id}
            headline = title.removesuffix(f" | {SITE_NAME}").strip()
            article = {
                "@type": "BlogPosting" if category == "blog" else "Article",
                "@id": article_id,
                "headline": headline,
                "inLanguage": "sv-SE",
                "mainEntityOfPage": {"@id": webpage_id},
                "publisher": {"@id": organization_id},
            }
            if description:
                article["description"] = description
            article["author"] = {
                "@type": "Person",
                "name": ARTICLE_AUTHOR,
                "url": ARTICLE_AUTHOR_URL,
            }
            if article_date:
                article["datePublished"] = article_date
            if article_image:
                article["image"] = article_image
            graph.append(article)

    payload = json.dumps(
        {"@context": "https://schema.org", "@graph": graph},
        ensure_ascii=False,
        indent=2,
    )
    # JSON-LD is embedded inside HTML; neutralize special HTML characters so
    # even a title containing '</script>' cannot terminate the script tag.
    return (payload.replace("<", "\\u003c")
                   .replace(">", "\\u003e")
                   .replace("&", "\\u0026"))


def append_structured_data(document, title, description, canonical_url, relative, article_date, article_image):
    """Insert one JSON-LD graph into <head> without duplicating legacy data."""
    head = re.search(r"<head\b[^>]*>.*?</head\s*>", document,
                     re.IGNORECASE | re.DOTALL)
    if not head:
        return document

    # Preserve any structured data already maintained by a standalone page.
    if re.search(r'<script\b(?=[^>]*\btype\s*=\s*["\']application/ld\+json["\'])[^>]*>',
                 head.group(0), re.IGNORECASE):
        return document

    payload = create_structured_data(title, description, canonical_url, relative, article_date, article_image)
    script = '  <script type="application/ld+json">\n' + payload + '\n  </script>'
    return re.sub(r"</head\s*>", lambda m: script + "\n" + m.group(0),
                  document, count=1, flags=re.IGNORECASE)


def build_page(source, partials, layout):
    relative = source.relative_to(PAGES)
    destination = ROOT / relative

    # Canonical URLs use the public domain and preserve nested page paths.
    url_path = relative.as_posix()
    if relative.name == "index.html":
        url_path = url_path[:-len("index.html")]
    canonical_url = f"{SITE_URL}/{quote(url_path)}"

    root_prefix = "../" * (len(relative.parts) - 1)
    source_text = source.read_text(encoding="utf-8")

    # Existing full HTML documents remain supported.
    if re.match(r"^\s*<!doctype html", source_text, re.IGNORECASE):
        result = source_text
        nav_key = "home" if relative == Path("index.html") else relative.stem
        head = DocumentHeadParser()
        head.feed(result)
        page_title = head.title or SITE_NAME
        page_description = head.description
        image_path = DEFAULT_SOCIAL_IMAGE

    else:
        metadata, content = parse_page(source_text)

        if relative == Path("blog/index.html"):
            feature, cards = render_blog_sections()

            sections = (
                ("BLOG_FEATURE", feature),
                (
                    "BLOG_ARTICLES",
                    f'<div class="v2-blog-grid">\n{cards}\n</div>'
                ),
            )

            for name, generated_html in sections:
                pattern = rf'(<!-- {name}_START -->).*?(<!-- {name}_END -->)'

                content, count = re.subn(
                    pattern,
                    lambda match: (
                        f"{match.group(1)}\n"
                        f"{generated_html}\n"
                        f"{match.group(2)}"
                    ),
                    content,
                    flags=re.DOTALL,
                )

                if count != 1:
                    raise ValueError(
                        f"Expected one {name} block in blog/index.html, found {count}"
                    )

        page_title = metadata["title"]
        page_description = metadata["description"]
        image_path = metadata.get("social_image", DEFAULT_SOCIAL_IMAGE)

        nav_key = metadata["nav"]

        styles = [
            item.strip()
            for item in metadata.get("styles", "").split(",")
            if item.strip()
        ]

        style_tags = "\n".join(
            f'  <link rel="stylesheet" href="{{{{root}}}}{escape(style, quote=True)}">'
            for style in styles
        )

        result = layout

        result = result.replace(
            "{{page_title}}",
            escape(metadata["title"])
        )
        result = result.replace(
            "{{page_description}}",
            escape(metadata["description"], quote=True)
        )
        result = result.replace("{{page_styles}}", style_tags)
        result = result.replace("{{page_content}}", content)

    # Insert shared components.
    for name, fragment in partials.items():
        placeholder = "{{" + name.replace("-", "_") + "}}"
        result = result.replace(placeholder, fragment)

    # Canonical placeholder can occur in the layout, content, or partials.
    # Resolve it after all fragments have been assembled, for every page type.
    canonical_tag = f'<link rel="canonical" href="{escape(canonical_url, quote=True)}">'
    if "{{page_canonical}}" in result:
        result = result.replace("{{page_canonical}}", escape(canonical_url, quote=True))
    elif not re.search(r'<link\b[^>]*\brel\s*=\s*["\']canonical["\']', result, re.IGNORECASE):
        # A legacy full HTML document may have no layout placeholder.
        result = re.sub(r'<head\b[^>]*>', lambda m: m.group(0) + "\n  " + canonical_tag, result,
                        count=1, flags=re.IGNORECASE)

    # Add social sharing tags. Existing tags in a standalone page are retained.
    social_fields = create_social_tags(
        page_title, page_description, canonical_url, relative, image_path
    )
    if "{{social_meta}}" in result:
        result = result.replace(
            "{{social_meta}}", render_missing_social_tags(social_fields, set())
        )
    else:
        head_match = re.search(r"<head\b[^>]*>.*?</head\s*>", result, re.IGNORECASE | re.DOTALL)
        if head_match:
            head_parser = DocumentHeadParser()
            head_parser.feed(head_match.group(0))
            additions = render_missing_social_tags(social_fields, head_parser.meta_keys)
            if additions:
                result = re.sub(
                    r"</head\s*>",
                    lambda match: additions + "\n" + match.group(0),
                    result,
                    count=1,
                    flags=re.IGNORECASE,
                )

    # Read article dates and images from the original page source.
    article_date = article_image = None
    if len(relative.parts) == 2 and relative.parts[0] in ("blog", "kunskap") and relative.name != "index.html":
        article_date, article_image = article_media(source_text, canonical_url, root_prefix)

    # Add Schema.org JSON-LD to the document head.
    result = append_structured_data(
        result, page_title, page_description, canonical_url, relative,
        article_date, article_image
    )

    # Mark the active navigation link.
    result = re.sub(
        r"\{\{active:([a-z0-9_-]+)\}\}",
        lambda match: (
            ' aria-current="page"'
            if match.group(1) == nav_key
            else ""
        ),
        result,
    )

    # Resolve relative asset and page paths.
    result = result.replace("{{root}}", root_prefix)

    # Discover the homepage LCP background in HTML before CSS is parsed.
    if relative == Path("index.html"):
        hero_preload = (
            '  <link rel="preload" as="image" '
            'href="/images/haven-hero-original.webp" fetchpriority="high">'
        )
        result = re.sub(
            r"<head\b[^>]*>",
            lambda match: match.group(0) + "\n" + hero_preload,
            result,
            count=1,
            flags=re.IGNORECASE,
        )

    # Detect unresolved placeholders.
    unresolved = re.findall(r"\{\{[^{}]+\}\}", result)

    if unresolved:
        raise ValueError(
            f"Unresolved placeholders in {relative}: {unresolved}"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(result, encoding="utf-8")

    return destination


def main():
    partials = load_partials()
    layout = LAYOUT.read_text(encoding="utf-8")

    sources = sorted(PAGES.rglob("*.html"))

    if not sources:
        raise SystemExit("No source pages found.")

    for source in sources:
        destination = build_page(source, partials, layout)
        print(f"Built {destination.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
