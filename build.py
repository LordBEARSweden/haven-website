
#!/usr/bin/env python3
"""Haven Nordic Health 2.0 - Static site builder."""

from pathlib import Path
from html import escape
import re

ROOT = Path(__file__).resolve().parent
PAGES = ROOT / "src" / "pages"
PARTIALS = ROOT / "src" / "partials"
LAYOUT = ROOT / "src" / "layouts" / "base.html"

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


def build_page(source, partials, layout):
    relative = source.relative_to(PAGES)
    destination = ROOT / relative

    root_prefix = "../" * (len(relative.parts) - 1)
    source_text = source.read_text(encoding="utf-8")

    # Existing full HTML documents remain supported.
    if re.match(r"^\s*<!doctype html", source_text, re.IGNORECASE):
        result = source_text
        nav_key = "home" if relative == Path("index.html") else relative.stem

    else:
        metadata, content = parse_page(source_text)

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
