const fs = require("fs");
const path = require("path");

const POSTS_DIR = path.join(__dirname, "../blog");
const OUTPUT_FILE = path.join(__dirname, "../rss.xml");

const siteUrl = "https://www.havennordichealth.se";

/* -----------------------------
   Extract metadata
------------------------------ */
function extractMeta(content) {
  const match = content.match(
    /<script type="application\/json" class="post-meta">([\s\S]*?)<\/script>/
  );
  if (!match) return null;

  try {
    return JSON.parse(match[1]);
  } catch (e) {
    return null;
  }
}

/* -----------------------------
   Extract first paragraph as fallback excerpt
------------------------------ */
function extractExcerpt(html) {
  const match = html.match(/<p>(.*?)<\/p>/i);
  if (!match) return "";

  return match[1].replace(/<[^>]*>/g, "").trim();
}

/* -----------------------------
   XML safety (VIKTIG)
------------------------------ */
function escapeXML(str = "") {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

/* -----------------------------
   Read blog posts
------------------------------ */
function getPosts() {
  const files = fs.readdirSync(POSTS_DIR);

  return files
    .filter(file => file.endsWith(".html") && file !== "index.html")
    .map(file => {
      const content = fs.readFileSync(path.join(POSTS_DIR, file), "utf8");
      const meta = extractMeta(content);

      if (!meta) return null;

      return {
        title: meta.title,
        date: meta.date,
        description: meta.description || extractExcerpt(content),
        slug: file.replace(".html", "")
      };
    })
    .filter(Boolean)
    .sort((a, b) => new Date(b.date) - new Date(a.date));
}

/* -----------------------------
   Build RSS XML
------------------------------ */
function buildRSS(posts) {
  const items = posts
    .map(post => `
    <item>
      <title>${escapeXML(post.title)}</title>
      <link>${siteUrl}/blogg/${post.slug}.html</link>
      <pubDate>${new Date(post.date).toUTCString()}</pubDate>
      <description>${escapeXML(post.description)}</description>
    </item>
    `)
    .join("");

  return `<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>Haven Nordic Health</title>
  <link>${siteUrl}/blogg</link>
  <description>Reflektioner om återhämtning, närvaro och inre balans</description>
  ${items}
</channel>
</rss>`;
}

/* -----------------------------
   Generate RSS
------------------------------ */
const posts = getPosts();
const rss = buildRSS(posts);

fs.writeFileSync(OUTPUT_FILE, rss);

console.log("RSS generated");

