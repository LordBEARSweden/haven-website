/* Haven 2.0 – Haven Journal. No external dependencies.
   The newest article in the overview automatically takes the featured position.
   Its cover comes from the first editorial image in the article itself.
   A new post only needs to be added to the normal archive cards with a <time datetime="YYYY-MM-DD">.
*/
(() => {
  'use strict';

  function parseCard(card) {
    const time = card.querySelector('time[datetime]');
    const title = card.querySelector('h3');
    const summary = card.querySelector('p');
    if (!time || !title || !summary) return null;
    const date = time.getAttribute('datetime');
    if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) return null;
    return {
      date,
      dateLabel: time.textContent.trim(),
      title: title.textContent.trim(),
      summary: summary.textContent.trim(),
      href: card.getAttribute('href')
    };
  }

  function readFeature(feature) {
    const time = feature.querySelector('time[datetime]');
    return {
      date: time.getAttribute('datetime'),
      dateLabel: time.textContent.trim(),
      title: feature.querySelector('h2').textContent.trim(),
      summary: feature.querySelector('.v2-blog-feature-copy > p').textContent.trim(),
      href: feature.getAttribute('href')
    };
  }

  function makeArchiveCard(post) {
    const card = document.createElement('a');
    card.className = 'v2-blog-card';
    card.href = post.href;
    card.setAttribute('aria-label', `Läs: ${post.title}`);

    const top = document.createElement('div');
    top.className = 'v2-blog-card-top';
    const number = document.createElement('span');
    number.className = 'v2-blog-card-index';
    const time = document.createElement('time');
    time.dateTime = post.date;
    time.textContent = post.dateLabel;
    top.append(number, time);

    const h3 = document.createElement('h3');
    h3.textContent = post.title;
    const text = document.createElement('p');
    text.textContent = post.summary;
    const more = document.createElement('span');
    more.className = 'v2-blog-card-link';
    more.textContent = 'Läs mer ';
    const arrow = document.createElement('span');
    arrow.setAttribute('aria-hidden', 'true');
    arrow.textContent = '↗';
    more.appendChild(arrow);
    card.append(top, h3, text, more);
    return card;
  }

  function setFeature(feature, post) {
    feature.setAttribute('href', post.href);
    feature.setAttribute('aria-label', `Läs: ${post.title}`);
    const time = feature.querySelector('time');
    time.dateTime = post.date;
    time.textContent = post.dateLabel;
    feature.querySelector('h2').textContent = post.title;
    feature.querySelector('.v2-blog-feature-copy > p').textContent = post.summary;
  }

  async function showFirstArticleImage(feature) {
    const image = feature.querySelector('.v2-blog-feature-image');
    if (!image) return;
    image.addEventListener('error', () => { image.hidden = true; });
    const articleURL = new URL(feature.getAttribute('href'), window.location.href);
    if (articleURL.origin !== window.location.origin) return;

    try {
      const response = await fetch(articleURL.href, { credentials: 'same-origin' });
      if (!response.ok) return;
      const article = new DOMParser().parseFromString(await response.text(), 'text/html');
      const first = article.querySelector('main figure.article-image img, main .article-image img, main figure img, main article img, main img');
      const src = first?.getAttribute('src');
      if (!src) return;
      const photoURL = new URL(src, articleURL.href);
      if (!['http:', 'https:'].includes(photoURL.protocol)) return;
      image.hidden = false;
      image.src = photoURL.href;
    } catch (_) {
      // Keep the neutral background if an article isn't available locally yet.
    }
  }

  function start() {
    const page = document.querySelector('.v2-blog-page');
    if (!page) return;
    const feature = page.querySelector('.v2-blog-feature');
    const grid = page.querySelector('.v2-blog-grid');
    if (!feature || !grid) return;

    const selected = readFeature(feature);
    const candidates = Array.from(grid.querySelectorAll(':scope > .v2-blog-card'))
      .map(card => ({ card, post: parseCard(card) }))
      .filter(item => item.post && item.post.date > selected.date)
      .sort((a, b) => b.post.date.localeCompare(a.post.date));
    if (candidates.length) {
      const newest = candidates[0];
      newest.card.remove();
      grid.appendChild(makeArchiveCard(selected));
      setFeature(feature, newest.post);
      const sorted = Array.from(grid.querySelectorAll(':scope > .v2-blog-card'))
        .sort((a, b) => (parseCard(b)?.date || '').localeCompare(parseCard(a)?.date || ''));
      grid.replaceChildren(...sorted);
    }
    Array.from(grid.querySelectorAll(':scope > .v2-blog-card .v2-blog-card-index'))
      .forEach((el, i) => { el.textContent = String(i + 1).padStart(2, '0'); });

    showFirstArticleImage(feature);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start, { once: true });
  } else {
    start();
  }
})();
