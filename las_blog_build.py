#!/usr/bin/env python3
"""
Layer Advisory Services — Blog Builder
Generates SEO-optimized blog posts in Erica Layer's voice using Claude API.

Usage:
  python las_blog_build.py --from-queue --count 5
  python las_blog_build.py --build-pillar --cluster founder-dependency
  python las_blog_build.py --rebuild-all
  python las_blog_build.py --single --keyword "how to delegate as a founder" --cluster founder-dependency
"""

import os
import json
import argparse
import re
import hashlib
from datetime import datetime, timezone
from pathlib import Path
import anthropic

# ── Config ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent
POSTS_DIR = ROOT / "posts"
MANIFEST_FILE = ROOT / "posts_manifest.json"
QUEUE_FILE = ROOT / "aqe_queue.json"
TAXONOMY_FILE = ROOT / "taxonomy.json"
SKILL_FILE = ROOT / "SKILL.md"
SITE_DIR = ROOT / "site"

POSTS_DIR.mkdir(exist_ok=True)
SITE_DIR.mkdir(exist_ok=True)

# ── Load Files ───────────────────────────────────────────────────────────────
def load_json(path):
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return {}

def load_text(path):
    if path.exists():
        return path.read_text()
    return ""

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)

# ── Brand Voice System Prompt ────────────────────────────────────────────────
def build_system_prompt(skill_text, taxonomy):
    brand = taxonomy.get("brand", "Layer Advisory Services")
    author = taxonomy.get("author", "Erica Layer")
    domain = taxonomy.get("domain", "blog.layeradvisory.com")

    return f"""You are the content engine for {brand}, writing blog posts in the authentic voice of {author}.

{skill_text}

---

## Output Format

You MUST return a valid JSON object with exactly this structure. No preamble, no markdown fences, just raw JSON:

{{
  "title": "The post headline",
  "slug": "url-friendly-slug",
  "meta_description": "150-160 character description in Erica's voice",
  "primary_keyword": "the target keyword",
  "semantic_keywords": ["variant 1", "variant 2", "variant 3"],
  "cluster": "cluster-id",
  "estimated_read_time": 5,
  "excerpt": "2-3 sentence excerpt for the post card on the blog index",
  "tags": ["FractionalCOO", "Leadership", "OperationalExcellence"],
  "body_html": "<p>Full HTML body of the post...</p>",
  "word_count": 850
}}

## HTML Body Rules
- Use <p> tags for all paragraphs
- Use <h2> for major section breaks (2-3 max, not required for shorter posts)
- Use <strong> sparingly for single key phrases that earn emphasis
- Use <em> for book titles, org names, or light emphasis
- Use <ul> or <ol> only when a list genuinely serves the content — not as a default structure
- NO <h1> (that's the title), NO <div>, NO <span>, NO classes
- Every paragraph should be 1-4 sentences. Short paragraphs are preferred.
- The post should feel like reading a thoughtful LinkedIn article, not a how-to guide

## Tone Checklist (verify before returning)
✓ Opens with a specific moment, observation, or concrete truth — not a question or statistic
✓ Draws on personal experience (CEO at D-tree, current client work)
✓ Uses plain language — no jargon, no framework names without explanation
✓ Short paragraphs with strategic white space
✓ Closes with a question, reframe, or quiet call to reflection — not a sales pitch
✓ Reads like a practitioner, not a consultant
✓ Primary keyword appears in headline, first 100 words, and 2-3 times in body — naturally
"""

# ── Post Generator ───────────────────────────────────────────────────────────
def generate_post(keyword, cluster_id, taxonomy, skill_text, extra_context=""):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    system_prompt = build_system_prompt(skill_text, taxonomy)

    cluster = next((c for c in taxonomy["clusters"] if c["id"] == cluster_id), {})
    cluster_name = cluster.get("name", cluster_id)
    question_examples = "\n".join(f"- {q}" for q in cluster.get("question_types", [])[:3])

    user_prompt = f"""Write a blog post for Layer Advisory Services targeting this keyword:

Primary keyword: {keyword}
Topic cluster: {cluster_name}
Target reader: Founders, CEOs, and leaders of growing startups, nonprofits, and small businesses

Reader questions this post should answer:
{question_examples}

{f'Additional context: {extra_context}' if extra_context else ''}

Target word count: 850 words (600 minimum, 1100 maximum)

Draw on Erica's experience as CEO of D-tree International and her current work as a Fractional COO. 
Be specific. Be honest. Write like someone who has lived through this, not someone who has read about it.

Return only the JSON object. Nothing else."""

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )

    raw = response.content[0].text.strip()
    # Strip any accidental markdown fences
    raw = re.sub(r'^```json\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)

    post_data = json.loads(raw)
    return post_data

# ── HTML Post Writer ─────────────────────────────────────────────────────────
def write_post_html(post_data, taxonomy):
    brand = taxonomy.get("brand", "Layer Advisory Services")
    author = taxonomy.get("author", "Erica Layer")
    domain = taxonomy.get("domain", "blog.layeradvisory.com")

    pub_date = datetime.now(timezone.utc).strftime("%B %d, %Y")
    pub_iso = datetime.now(timezone.utc).isoformat()
    read_time = post_data.get("estimated_read_time", 5)
    title = post_data["title"]
    meta_desc = post_data["meta_description"]
    slug = post_data["slug"]
    body_html = post_data["body_html"]
    tags = post_data.get("tags", [])
    tags_html = " ".join(f'<span class="tag">#{t}</span>' for t in tags)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} | {brand}</title>
  <meta name="description" content="{meta_desc}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{meta_desc}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="https://{domain}/posts/{slug}">
  <meta property="og:image" content="https://{domain}/og/{slug}.png">
  <meta name="twitter:card" content="summary_large_image">
  <link rel="canonical" href="https://{domain}/posts/{slug}">
  <link rel="stylesheet" href="/assets/blog.css">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&family=Open+Sans:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet">
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    "headline": "{title}",
    "description": "{meta_desc}",
    "author": {{"@type": "Person", "name": "{author}"}},
    "publisher": {{"@type": "Organization", "name": "{brand}"}},
    "datePublished": "{pub_iso}",
    "url": "https://{domain}/posts/{slug}"
  }}
  </script>
</head>
<body>
  <header class="site-header">
    <div class="container">
      <a href="/" class="logo">Layer Advisory</a>
      <nav>
        <a href="/posts">All Posts</a>
        <a href="https://layer-advisory-services.lovable.app" class="btn-primary">Book a Call</a>
      </nav>
    </div>
  </header>

  <article class="post-article">
    <div class="post-header">
      <div class="container narrow">
        <div class="post-meta">
          <span class="author">By {author}</span>
          <span class="sep">·</span>
          <time datetime="{pub_iso}">{pub_date}</time>
          <span class="sep">·</span>
          <span>{read_time} min read</span>
        </div>
        <h1 class="post-title">{title}</h1>
        <p class="post-excerpt">{post_data.get('excerpt', meta_desc)}</p>
      </div>
    </div>

    <div class="post-body">
      <div class="container narrow">
        {body_html}
      </div>
    </div>

    <footer class="post-footer">
      <div class="container narrow">
        <div class="post-tags">{tags_html}</div>
        <div class="author-card">
          <div class="author-card-body">
            <div class="author-name">{author}</div>
            <div class="author-bio">Fractional COO and Strategic Operating Partner. I help founders of growing organizations build the structure, systems, and clarity they need to lead with confidence — without the weight of a full-time hire.</div>
            <a href="https://calendly.com/erica-layeradvisory/30min" class="cta-link">Book a 30-minute call →</a>
          </div>
        </div>
      </div>
    </footer>
  </article>

  <section class="related-cta">
    <div class="container narrow">
      <div class="cta-card">
        <div class="cta-eyebrow">Not sure where to start?</div>
        <h2 class="cta-title">Get a free operational diagnostic</h2>
        <p class="cta-body">Answer 9 questions and get a personalized report on where your biggest operational gaps are — and what to do about them.</p>
        <a href="/#diagnostic" class="btn-primary">Take the assessment →</a>
      </div>
    </div>
  </section>

  <footer class="site-footer">
    <div class="container">
      <div class="footer-brand">Layer Advisory Services</div>
      <div class="footer-tagline">Structure. Systems. Space to Lead.</div>
      <div class="footer-links">
        <a href="/posts">Blog</a>
        <a href="https://layer-advisory-services.lovable.app">Main Site</a>
        <a href="https://linkedin.com/in/ericalayer">LinkedIn</a>
      </div>
    </div>
  </footer>
</body>
</html>"""

    return html

# ── CSS Generator ────────────────────────────────────────────────────────────
def write_blog_css():
    return """/* Layer Advisory Blog Styles */
:root {
  --slate: #4B637A;
  --taupe: #B6A999;
  --sage: #C8D3C0;
  --terracotta: #C57A64;
  --sand: #F5F2ED;
  --sand-dark: #e8e3db;
  --charcoal: #2F2F2F;
  --charcoal-light: #666;
  --white: #fff;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: 'Open Sans', sans-serif;
  background: var(--white);
  color: var(--charcoal);
  font-size: 17px;
  line-height: 1.7;
}

.container { max-width: 1100px; margin: 0 auto; padding: 0 24px; }
.container.narrow { max-width: 720px; }

/* Header */
.site-header {
  background: var(--white);
  border-bottom: 1px solid var(--sand-dark);
  padding: 16px 0;
  position: sticky; top: 0; z-index: 100;
}

.site-header .container {
  display: flex; align-items: center; justify-content: space-between;
}

.logo {
  font-family: 'Montserrat', sans-serif;
  font-size: 14px; font-weight: 700;
  color: var(--charcoal);
  text-decoration: none;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

nav { display: flex; align-items: center; gap: 24px; }

nav a {
  font-family: 'Montserrat', sans-serif;
  font-size: 12px; font-weight: 500;
  color: var(--charcoal-light);
  text-decoration: none;
  transition: color 0.15s;
}

nav a:hover { color: var(--slate); }

.btn-primary {
  background: var(--slate);
  color: white !important;
  padding: 9px 18px;
  border-radius: 8px;
  font-weight: 600 !important;
  transition: background 0.15s !important;
}

.btn-primary:hover { background: #344a5a !important; }

/* Post Header */
.post-header {
  background: var(--sand);
  padding: 60px 0 48px;
  border-bottom: 1px solid var(--sand-dark);
}

.post-meta {
  display: flex; align-items: center; gap: 8px;
  font-family: 'Montserrat', sans-serif;
  font-size: 11px; font-weight: 500;
  color: var(--charcoal-light);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin-bottom: 20px;
}

.sep { opacity: 0.4; }

.post-title {
  font-family: 'Montserrat', sans-serif;
  font-size: clamp(26px, 4vw, 38px);
  font-weight: 700;
  color: var(--charcoal);
  line-height: 1.25;
  margin-bottom: 16px;
}

.post-excerpt {
  font-size: 18px;
  color: var(--charcoal-light);
  line-height: 1.6;
  font-style: italic;
}

/* Post Body */
.post-body { padding: 56px 0; }

.post-body p {
  margin-bottom: 22px;
  color: var(--charcoal);
}

.post-body h2 {
  font-family: 'Montserrat', sans-serif;
  font-size: 20px; font-weight: 700;
  color: var(--charcoal);
  margin: 40px 0 16px;
}

.post-body strong { font-weight: 600; }
.post-body em { font-style: italic; }

.post-body ul, .post-body ol {
  padding-left: 20px;
  margin-bottom: 22px;
}

.post-body li { margin-bottom: 10px; }

/* Post Footer */
.post-footer {
  background: var(--sand);
  padding: 40px 0;
  border-top: 1px solid var(--sand-dark);
}

.post-tags {
  display: flex; flex-wrap: wrap; gap: 8px;
  margin-bottom: 32px;
}

.tag {
  font-family: 'Montserrat', sans-serif;
  font-size: 10px; font-weight: 600;
  letter-spacing: 0.06em;
  color: var(--slate);
  background: rgba(75,99,122,0.08);
  padding: 4px 10px;
  border-radius: 20px;
}

.author-card {
  background: white;
  border-radius: 12px;
  border: 1px solid var(--sand-dark);
  padding: 24px 28px;
}

.author-name {
  font-family: 'Montserrat', sans-serif;
  font-size: 14px; font-weight: 700;
  color: var(--charcoal);
  margin-bottom: 8px;
}

.author-bio {
  font-size: 14px;
  color: var(--charcoal-light);
  line-height: 1.6;
  margin-bottom: 14px;
}

.cta-link {
  font-family: 'Montserrat', sans-serif;
  font-size: 12px; font-weight: 600;
  color: var(--terracotta);
  text-decoration: none;
}

.cta-link:hover { text-decoration: underline; }

/* CTA Section */
.related-cta { padding: 56px 0; }

.cta-card {
  background: var(--slate);
  border-radius: 16px;
  padding: 40px 48px;
  color: white;
}

.cta-eyebrow {
  font-family: 'Montserrat', sans-serif;
  font-size: 10px; font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(255,255,255,0.6);
  margin-bottom: 10px;
}

.cta-title {
  font-family: 'Montserrat', sans-serif;
  font-size: 24px; font-weight: 700;
  color: white;
  margin-bottom: 12px;
  line-height: 1.3;
}

.cta-body {
  font-size: 15px;
  color: rgba(255,255,255,0.75);
  margin-bottom: 24px;
  line-height: 1.6;
  max-width: 480px;
}

.cta-card .btn-primary {
  background: var(--terracotta) !important;
  display: inline-block;
}

.cta-card .btn-primary:hover { background: #b56a54 !important; }

/* Site Footer */
.site-footer {
  background: #253545;
  padding: 32px 0;
  text-align: center;
}

.footer-brand {
  font-family: 'Montserrat', sans-serif;
  font-size: 12px; font-weight: 700;
  letter-spacing: 0.1em; text-transform: uppercase;
  color: white; margin-bottom: 4px;
}

.footer-tagline {
  font-family: 'Montserrat', sans-serif;
  font-size: 10px;
  color: var(--taupe);
  letter-spacing: 0.08em;
  margin-bottom: 16px;
}

.footer-links {
  display: flex; justify-content: center; gap: 24px;
}

.footer-links a {
  font-family: 'Montserrat', sans-serif;
  font-size: 11px; font-weight: 500;
  color: rgba(255,255,255,0.5);
  text-decoration: none;
  transition: color 0.15s;
}

.footer-links a:hover { color: white; }

/* Blog Index */
.blog-hero {
  background: var(--sand);
  padding: 60px 0 40px;
  border-bottom: 1px solid var(--sand-dark);
}

.blog-hero-eyebrow {
  font-family: 'Montserrat', sans-serif;
  font-size: 10px; font-weight: 700;
  letter-spacing: 0.14em; text-transform: uppercase;
  color: var(--terracotta); margin-bottom: 10px;
}

.blog-hero-title {
  font-family: 'Montserrat', sans-serif;
  font-size: clamp(28px, 4vw, 42px); font-weight: 700;
  color: var(--charcoal); margin-bottom: 12px;
}

.blog-hero-sub {
  font-size: 17px;
  color: var(--charcoal-light);
  max-width: 500px;
}

.post-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 24px;
  padding: 48px 0;
}

.post-card {
  background: white;
  border-radius: 12px;
  border: 1px solid var(--sand-dark);
  overflow: hidden;
  cursor: pointer;
  transition: all 0.2s;
  text-decoration: none;
  display: block;
}

.post-card:hover {
  box-shadow: 0 8px 28px rgba(75,99,122,0.1);
  transform: translateY(-2px);
}

.post-card-body { padding: 22px 24px; }

.post-card-meta {
  font-family: 'Montserrat', sans-serif;
  font-size: 9.5px; font-weight: 700;
  letter-spacing: 0.1em; text-transform: uppercase;
  color: var(--charcoal-light); opacity: 0.6;
  margin-bottom: 10px;
}

.post-card-title {
  font-family: 'Montserrat', sans-serif;
  font-size: 16px; font-weight: 700;
  color: var(--charcoal);
  line-height: 1.35;
  margin-bottom: 10px;
}

.post-card-excerpt {
  font-size: 13px;
  color: var(--charcoal-light);
  line-height: 1.55;
}

.post-card-footer {
  padding: 12px 24px;
  background: var(--sand);
  border-top: 1px solid var(--sand-dark);
  font-family: 'Montserrat', sans-serif;
  font-size: 10.5px; font-weight: 600;
  color: var(--slate);
}

@media (max-width: 640px) {
  .post-grid { grid-template-columns: 1fr; }
  .cta-card { padding: 28px 24px; }
  .post-header { padding: 40px 0 32px; }
}
"""

# ── Index Builder ────────────────────────────────────────────────────────────
def build_index(manifest, taxonomy):
    brand = taxonomy.get("brand", "Layer Advisory Services")
    author = taxonomy.get("author", "Erica Layer")
    domain = taxonomy.get("domain", "blog.layeradvisory.com")

    posts = sorted(manifest.get("posts", []), key=lambda p: p.get("published_at", ""), reverse=True)

    cards_html = ""
    for post in posts:
        slug = post.get("slug", "")
        title = post.get("title", "")
        excerpt = post.get("excerpt", "")
        date = post.get("published_at", "")[:10] if post.get("published_at") else ""
        read_time = post.get("estimated_read_time", 5)

        cards_html += f"""
    <a href="/posts/{slug}" class="post-card">
      <div class="post-card-body">
        <div class="post-card-meta">{date} · {read_time} min read</div>
        <div class="post-card-title">{title}</div>
        <div class="post-card-excerpt">{excerpt}</div>
      </div>
      <div class="post-card-footer">Read more →</div>
    </a>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Blog | {brand}</title>
  <meta name="description" content="Practical insights on operational clarity, sustainable growth, and the space to lead — from a Fractional COO who has been there.">
  <link rel="canonical" href="https://{domain}/posts">
  <link rel="stylesheet" href="/assets/blog.css">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;600;700&family=Open+Sans:ital,wght@0,400;0,500;1,400&display=swap" rel="stylesheet">
</head>
<body>
  <header class="site-header">
    <div class="container">
      <a href="/" class="logo">Layer Advisory</a>
      <nav>
        <a href="/posts">All Posts</a>
        <a href="https://layer-advisory-services.lovable.app" class="btn-primary">Book a Call</a>
      </nav>
    </div>
  </header>

  <section class="blog-hero">
    <div class="container">
      <div class="blog-hero-eyebrow">Insights</div>
      <h1 class="blog-hero-title">The Layer Advisory Blog</h1>
      <p class="blog-hero-sub">Practical thinking on operations, leadership, and building organizations that work without founder dependency.</p>
    </div>
  </section>

  <main>
    <div class="container">
      <div class="post-grid">{cards_html}
      </div>
    </div>
  </main>

  <footer class="site-footer">
    <div class="container">
      <div class="footer-brand">Layer Advisory Services</div>
      <div class="footer-tagline">Structure. Systems. Space to Lead.</div>
      <div class="footer-links">
        <a href="/posts">Blog</a>
        <a href="https://layer-advisory-services.lovable.app">Main Site</a>
        <a href="https://linkedin.com/in/ericalayer">LinkedIn</a>
      </div>
    </div>
  </footer>
</body>
</html>"""

# ── Sitemap Builder ───────────────────────────────────────────────────────────
def build_sitemap(manifest, taxonomy):
    domain = taxonomy.get("domain", "blog.layeradvisory.com")
    posts = manifest.get("posts", [])
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    urls = [f"""  <url>
    <loc>https://{domain}/posts</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>"""]

    for post in posts:
        slug = post.get("slug", "")
        pub = post.get("published_at", today)[:10]
        urls.append(f"""  <url>
    <loc>https://{domain}/posts/{slug}</loc>
    <lastmod>{pub}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>"""

# ── Main Builder ─────────────────────────────────────────────────────────────
def build_post(keyword, cluster_id, taxonomy, skill_text):
    print(f"  Generating: {keyword} [{cluster_id}]")
    post_data = generate_post(keyword, cluster_id, taxonomy, skill_text)

    slug = post_data["slug"]
    pub_time = datetime.now(timezone.utc).isoformat()
    post_data["published_at"] = pub_time

    # Write HTML
    post_dir = SITE_DIR / "posts" / slug
    post_dir.mkdir(parents=True, exist_ok=True)
    html = write_post_html(post_data, taxonomy)
    (post_dir / "index.html").write_text(html)
    print(f"  ✓ Written: site/posts/{slug}/index.html")

    # Save raw JSON
    (POSTS_DIR / f"{slug}.json").write_text(json.dumps(post_data, indent=2))

    return post_data

def run(args):
    taxonomy = load_json(TAXONOMY_FILE)
    skill_text = load_text(SKILL_FILE)
    manifest = load_json(MANIFEST_FILE) or {"posts": []}
    queue = load_json(QUEUE_FILE) or {"queue": []}

    if not taxonomy:
        print("ERROR: taxonomy.json not found")
        return
    if not skill_text:
        print("WARNING: SKILL.md not found — output quality will be reduced")

    # Write CSS
    assets_dir = SITE_DIR / "assets"
    assets_dir.mkdir(exist_ok=True)
    (assets_dir / "blog.css").write_text(write_blog_css())

    new_posts = []

    if args.from_queue:
        count = args.count or 5
        items = queue.get("queue", [])[:count]
        if not items:
            print("Queue is empty. Run the AQE pipeline first.")
            return
        for item in items:
            post = build_post(item["keyword"], item["cluster"], taxonomy, skill_text)
            new_posts.append(post)
        # Remove used items from queue
        queue["queue"] = queue["queue"][count:]
        save_json(QUEUE_FILE, queue)

    elif args.single:
        if not args.keyword or not args.cluster:
            print("--single requires --keyword and --cluster")
            return
        post = build_post(args.keyword, args.cluster, taxonomy, skill_text)
        new_posts.append(post)

    elif args.build_pillar:
        cluster_id = args.cluster
        cluster = next((c for c in taxonomy["clusters"] if c["id"] == cluster_id), None)
        if not cluster:
            print(f"Cluster not found: {cluster_id}")
            return
        keyword = cluster["pillar_keyword"]
        post = build_post(keyword, cluster_id, taxonomy, skill_text)
        new_posts.append(post)

    # Update manifest
    existing_slugs = {p["slug"] for p in manifest["posts"]}
    for post in new_posts:
        if post["slug"] not in existing_slugs:
            manifest["posts"].append({
                "slug": post["slug"],
                "title": post["title"],
                "excerpt": post.get("excerpt", ""),
                "cluster": post.get("cluster", ""),
                "primary_keyword": post.get("primary_keyword", ""),
                "published_at": post.get("published_at", ""),
                "estimated_read_time": post.get("estimated_read_time", 5),
                "tags": post.get("tags", []),
                "word_count": post.get("word_count", 0)
            })

    save_json(MANIFEST_FILE, manifest)

    # Rebuild index and sitemap
    (SITE_DIR / "posts" / "index.html").write_text(build_index(manifest, taxonomy))
    (SITE_DIR / "sitemap.xml").write_text(build_sitemap(manifest, taxonomy))

    print(f"\n✓ Done. {len(new_posts)} post(s) generated.")
    print(f"✓ Manifest updated: {len(manifest['posts'])} total posts")
    print(f"✓ Index and sitemap rebuilt")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Layer Advisory Blog Builder")
    parser.add_argument("--from-queue", action="store_true")
    parser.add_argument("--single", action="store_true")
    parser.add_argument("--build-pillar", action="store_true")
    parser.add_argument("--rebuild-all", action="store_true")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--keyword", type=str)
    parser.add_argument("--cluster", type=str)
    args = parser.parse_args()
    run(args)
