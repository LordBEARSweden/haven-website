const fs = require("fs");
const path = require("path");

const POSTS_DIR = path.join(__dirname, "../blog");
const OUTPUT_FILE = path.join(__dirname, "../rss.xml");

const siteUrl = "https://www.havennordichealth.se";

function extractMeta(content) {
  const match = content.match(/<script type="application\/json" class="post-meta">([\s\S]*?)<\/script>/);
  if (!match) return null;
  return JSON.parse(match[1]);
}

function getPosts() {
  const files = fs.readdirSync(POSTS_DIR);

  return files
    .filter(file => file.endsWith(".html") && file !== "index.html")
    .map(file => {
      const content = fs.readFileSync(path.join(POSTS_DIR, file), "utf8");
      const meta = extractMeta(content);

      if (!meta) return null;

      return {
        ...meta,
        slug: file.replace(".html", "")
      };
    })
    .filter(Boolean)
    .sort((a, b) => new Date(b.date) - new Date(a.date));
}

function buildRSS(posts) {
  let items = "";

  posts.forEach(post => {
    items += `
    <item>
      <title>${post.title}</title>
      <link>${siteUrl}/blogg/posts/${post.slug}.html</link>
      <pubDate>${new Date(post.date).toUTCString()}</pubDate>
      <description>${post.description}</description>
    </item>`;
  });

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

const posts = getPosts();
const rss = buildRSS(posts);

fs.writeFileSync(OUTPUT_FILE, rss);

console.log("RSS generated");