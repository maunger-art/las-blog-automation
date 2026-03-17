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
SITE_DIR = ROOT / "docs"

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
    cluster = post_data.get("cluster", "").replace("-", " ").title()

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
  <script type="application/ld+json">
  {{{{
    "@context": "https://schema.org",
    "@type": "BlogPosting",
    "headline": "{title}",
    "description": "{meta_desc}",
    "author": {{{{"@type": "Person", "name": "{author}"}}}},
    "publisher": {{{{"@type": "Organization", "name": "{brand}"}}}},
    "datePublished": "{pub_iso}",
    "url": "https://{domain}/posts/{slug}"
  }}}}
  </script>
</head>
<body>
  <header class="site-header">
    <a href="https://layeradvisory.com" class="logo">Layer Advisory</a>
    <nav>
      <a href="/posts">All Posts</a>
      <a href="https://layeradvisory.com">Main Site</a>
      <a href="https://calendly.com/erica-layeradvisory/30min" class="btn-nav">Let's Talk</a>
    </nav>
  </header>

  <article class="post-article">
    <div class="post-header">
      <div class="post-header-inner">
        <div class="post-meta">
          {pub_date} <span>·</span> {read_time} min read <span>·</span> {cluster}
        </div>
        <h1 class="post-title">{title}</h1>
        <p class="post-excerpt">{post_data.get('excerpt', meta_desc)}</p>
      </div>
    </div>

    <div class="post-body">
      <div class="post-body-inner">
        {body_html}
      </div>
    </div>

    <footer class="post-footer">
      <div class="post-footer-inner">
        <div class="post-tags">{tags_html}</div>
        <div class="author-card">
          <div class="author-name">{author}</div>
          <div class="author-bio">Fractional COO and Strategic Operating Partner. I help founders of growing organizations build the structure, systems, and clarity they need to lead with confidence — without the weight of a full-time hire.</div>
          <a href="https://calendly.com/erica-layeradvisory/30min" class="cta-link">Book a 30-minute call</a>
        </div>
      </div>
    </footer>
  </article>

  <section class="related-cta">
    <div class="cta-card">
      <div class="cta-eyebrow">Not sure where to start?</div>
      <h2 class="cta-title">Get a free operational diagnostic</h2>
      <p class="cta-body">Answer 9 questions and get a personalized report on where your biggest operational gaps are — and what to do about them.</p>
      <a href="https://layeradvisory.com/#diagnostic" class="btn-primary">Take the assessment</a>
    </div>
  </section>

  <footer class="site-footer">
    <div class="container">
      <div class="footer-brand">Layer Advisory Services</div>
      <div class="footer-tagline">Structure. Systems. Space to Lead.</div>
      <div class="footer-links">
        <a href="/posts">Blog</a>
        <a href="https://layeradvisory.com">Main Site</a>
        <a href="https://linkedin.com/in/ericalayer">LinkedIn</a>
      </div>
    </div>
  </footer>
</body>
</html>"""

    return html

# ── CSS Generator ────────────────────────────────────────────────────────────
def write_blog_css():
    return """@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400;1,500&family=Montserrat:wght@300;400;500;600;700&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300;1,400&display=swap');

:root {
  --slate-dark:    #253545;
  --slate:         #344a5a;
  --slate-mid:     #4B637A;
  --gold:          #C4A97D;
  --gold-light:    #d4be9a;
  --taupe:         #B6A999;
  --taupe-light:   #d4c9bf;
  --sand:          #F5F2ED;
  --sand-dark:     #E8E3DB;
  --charcoal:      #1a1a1a;
  --charcoal-mid:  #2F2F2F;
  --charcoal-soft: #555;
  --white:         #ffffff;
}

*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
html { font-size: 16px; -webkit-font-smoothing: antialiased; }
body { font-family: 'DM Sans', sans-serif; background: var(--white); color: var(--charcoal-mid); line-height: 1.7; }
h1, h2, h3 { font-family: 'Cormorant Garamond', serif; font-weight: 400; line-height: 1.15; letter-spacing: -0.01em; }

/* HEADER */
.site-header { background: var(--slate-dark); padding: 0 48px; height: 68px; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 100; border-bottom: 1px solid rgba(196,169,125,0.15); }
.logo { font-family: 'Montserrat', sans-serif; font-size: 12px; font-weight: 600; letter-spacing: 0.18em; text-transform: uppercase; color: var(--white); text-decoration: none; opacity: 0.9; transition: opacity 0.2s; }
.logo:hover { opacity: 1; }
nav { display: flex; align-items: center; gap: 32px; }
nav a { font-family: 'Montserrat', sans-serif; font-size: 11px; font-weight: 500; letter-spacing: 0.1em; text-transform: uppercase; color: rgba(255,255,255,0.6); text-decoration: none; transition: color 0.2s; }
nav a:hover { color: var(--gold); }
.btn-nav { color: var(--gold) !important; border: 1px solid rgba(196,169,125,0.4); padding: 8px 20px; border-radius: 2px; transition: all 0.2s !important; }
.btn-nav:hover { background: var(--gold) !important; color: var(--slate-dark) !important; }

/* BLOG HERO */
.blog-hero { background: var(--slate-dark); padding: 80px 48px 72px; position: relative; overflow: hidden; }
.blog-hero::before { content: ''; position: absolute; inset: 0; background: radial-gradient(ellipse at 80% 50%, rgba(196,169,125,0.06) 0%, transparent 60%); pointer-events: none; }
.blog-hero-inner { max-width: 1100px; margin: 0 auto; position: relative; }
.blog-hero-eyebrow { font-family: 'Montserrat', sans-serif; font-size: 10px; font-weight: 600; letter-spacing: 0.2em; text-transform: uppercase; color: var(--gold); margin-bottom: 16px; display: flex; align-items: center; gap: 12px; }
.blog-hero-eyebrow::before { content: ''; display: block; width: 32px; height: 1px; background: var(--gold); opacity: 0.6; }
.blog-hero-title { font-family: 'Cormorant Garamond', serif; font-size: clamp(42px, 6vw, 68px); font-weight: 300; color: var(--white); line-height: 1.08; margin-bottom: 20px; letter-spacing: -0.02em; }
.blog-hero-title em { font-style: italic; color: var(--gold); }
.blog-hero-sub { font-family: 'DM Sans', sans-serif; font-size: 16px; font-weight: 300; color: rgba(255,255,255,0.5); max-width: 480px; line-height: 1.65; }

/* POST GRID */
.blog-main { background: var(--sand); padding: 72px 48px; }
.blog-main-inner { max-width: 1100px; margin: 0 auto; }
.post-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 28px; }
.post-card:first-child { grid-column: 1 / -1; display: grid; grid-template-columns: 1fr 1fr; gap: 0; }
.post-card:first-child .post-card-body { padding: 44px 48px; }
.post-card:first-child .post-card-title { font-size: clamp(26px, 3vw, 36px); }
.post-card:first-child .post-card-footer { padding: 20px 48px; }
.post-card:first-child .post-card-accent { display: block; background: var(--slate-dark); min-height: 260px; position: relative; overflow: hidden; }
.post-card:first-child .post-card-accent::after { content: ''; position: absolute; inset: 0; background: radial-gradient(ellipse at 30% 70%, rgba(196,169,125,0.15) 0%, transparent 60%); }
.post-card { background: var(--white); border-radius: 2px; overflow: hidden; text-decoration: none; display: flex; flex-direction: column; transition: transform 0.25s ease, box-shadow 0.25s ease; border: 1px solid var(--sand-dark); }
.post-card:hover { transform: translateY(-3px); box-shadow: 0 16px 48px rgba(37,53,69,0.1); }
.post-card-accent { display: none; }
.post-card-body { padding: 28px 28px 20px; flex: 1; display: flex; flex-direction: column; }
.post-card-meta { font-family: 'Montserrat', sans-serif; font-size: 9.5px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--taupe); margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }
.post-card-meta::before { content: ''; display: block; width: 20px; height: 1px; background: var(--gold); opacity: 0.7; }
.post-card-title { font-family: 'Cormorant Garamond', serif; font-size: 22px; font-weight: 400; color: var(--slate-dark); line-height: 1.2; margin-bottom: 12px; flex: 1; transition: color 0.2s; }
.post-card:hover .post-card-title { color: var(--slate-mid); }
.post-card-excerpt { font-family: 'DM Sans', sans-serif; font-size: 13.5px; font-weight: 300; color: var(--charcoal-soft); line-height: 1.65; opacity: 0.8; }
.post-card-footer { padding: 16px 28px 24px; display: flex; align-items: center; justify-content: space-between; border-top: 1px solid var(--sand-dark); margin-top: 20px; }
.post-card-read { font-family: 'Montserrat', sans-serif; font-size: 10px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--gold); display: flex; align-items: center; gap: 8px; transition: gap 0.2s; }
.post-card:hover .post-card-read { gap: 14px; }
.post-card-read::after { content: '→'; font-size: 12px; }
.post-card-cluster { font-family: 'Montserrat', sans-serif; font-size: 9px; font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase; color: var(--taupe); opacity: 0.6; }

/* POST ARTICLE */
.post-header { background: var(--slate-dark); padding: 80px 48px 72px; position: relative; overflow: hidden; }
.post-header::before { content: ''; position: absolute; inset: 0; background: radial-gradient(ellipse at 80% 50%, rgba(196,169,125,0.07) 0%, transparent 60%); pointer-events: none; }
.post-header-inner { max-width: 720px; margin: 0 auto; position: relative; }
.post-meta { font-family: 'Montserrat', sans-serif; font-size: 10px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--gold); margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
.post-meta span { color: rgba(255,255,255,0.3); }
.post-title { font-family: 'Cormorant Garamond', serif; font-size: clamp(36px, 5vw, 58px); font-weight: 300; color: var(--white); line-height: 1.08; margin-bottom: 24px; letter-spacing: -0.02em; }
.post-excerpt { font-family: 'DM Sans', sans-serif; font-size: 17px; font-weight: 300; color: rgba(255,255,255,0.5); line-height: 1.65; max-width: 560px; }

/* POST BODY */
.post-body { padding: 72px 48px; background: var(--white); }
.post-body-inner { max-width: 680px; margin: 0 auto; }
.post-body p { font-family: 'DM Sans', sans-serif; font-size: 17px; font-weight: 300; color: var(--charcoal-mid); line-height: 1.75; margin-bottom: 26px; }
.post-body h2 { font-family: 'Cormorant Garamond', serif; font-size: 30px; font-weight: 400; color: var(--slate-dark); margin: 52px 0 20px; }
.post-body strong { font-weight: 600; color: var(--charcoal); }
.post-body em { font-style: italic; }
.post-body ul, .post-body ol { padding-left: 0; margin-bottom: 26px; list-style: none; }
.post-body li { font-family: 'DM Sans', sans-serif; font-size: 17px; font-weight: 300; color: var(--charcoal-mid); line-height: 1.7; margin-bottom: 12px; padding-left: 20px; position: relative; }
.post-body li::before { content: '—'; position: absolute; left: 0; color: var(--gold); }

/* POST FOOTER */
.post-footer { background: var(--sand); padding: 52px 48px; border-top: 1px solid var(--sand-dark); }
.post-footer-inner { max-width: 680px; margin: 0 auto; }
.post-tags { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 40px; }
.tag { font-family: 'Montserrat', sans-serif; font-size: 9px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: var(--slate-mid); background: rgba(75,99,122,0.07); border: 1px solid rgba(75,99,122,0.12); padding: 5px 12px; border-radius: 1px; }
.author-card { background: var(--slate-dark); padding: 36px 40px; border-radius: 2px; display: flex; flex-direction: column; gap: 12px; }
.author-name { font-family: 'Montserrat', sans-serif; font-size: 11px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--gold); }
.author-bio { font-family: 'DM Sans', sans-serif; font-size: 14px; font-weight: 300; color: rgba(255,255,255,0.55); line-height: 1.65; }
.cta-link { font-family: 'Montserrat', sans-serif; font-size: 10.5px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--gold); text-decoration: none; display: inline-flex; align-items: center; gap: 8px; transition: gap 0.2s; margin-top: 4px; }
.cta-link::after { content: '→'; }
.cta-link:hover { gap: 14px; }

/* CTA SECTION */
.related-cta { background: var(--white); padding: 72px 48px; border-top: 1px solid var(--sand-dark); }
.cta-card { max-width: 680px; margin: 0 auto; background: var(--slate-dark); padding: 52px 56px; border-radius: 2px; position: relative; overflow: hidden; }
.cta-card::before { content: ''; position: absolute; inset: 0; background: radial-gradient(ellipse at 80% 20%, rgba(196,169,125,0.08) 0%, transparent 60%); }
.cta-eyebrow { font-family: 'Montserrat', sans-serif; font-size: 9.5px; font-weight: 600; letter-spacing: 0.2em; text-transform: uppercase; color: var(--gold); margin-bottom: 16px; display: flex; align-items: center; gap: 12px; position: relative; }
.cta-eyebrow::before { content: ''; width: 24px; height: 1px; background: var(--gold); opacity: 0.6; }
.cta-title { font-family: 'Cormorant Garamond', serif; font-size: 36px; font-weight: 300; color: var(--white); line-height: 1.15; margin-bottom: 16px; position: relative; }
.cta-body { font-family: 'DM Sans', sans-serif; font-size: 15px; font-weight: 300; color: rgba(255,255,255,0.5); line-height: 1.65; margin-bottom: 28px; max-width: 420px; position: relative; }
.btn-primary { display: inline-flex; align-items: center; gap: 10px; font-family: 'Montserrat', sans-serif; font-size: 10.5px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--slate-dark); background: var(--gold); padding: 14px 28px; border-radius: 2px; text-decoration: none; transition: all 0.2s; position: relative; }
.btn-primary:hover { background: var(--gold-light); transform: translateY(-1px); }

/* SITE FOOTER */
.site-footer { background: var(--slate-dark); padding: 40px 48px; border-top: 1px solid rgba(196,169,125,0.15); }
.site-footer .container { max-width: 1100px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; }
.footer-brand { font-family: 'Montserrat', sans-serif; font-size: 11px; font-weight: 600; letter-spacing: 0.15em; text-transform: uppercase; color: rgba(255,255,255,0.5); }
.footer-tagline { font-family: 'Cormorant Garamond', serif; font-size: 14px; font-style: italic; color: var(--gold); opacity: 0.7; }
.footer-links { display: flex; gap: 28px; }
.footer-links a { font-family: 'Montserrat', sans-serif; font-size: 10px; font-weight: 500; letter-spacing: 0.1em; text-transform: uppercase; color: rgba(255,255,255,0.35); text-decoration: none; transition: color 0.2s; }
.footer-links a:hover { color: var(--gold); }

/* ANIMATIONS */
@keyframes fadeUp { from { opacity: 0; transform: translateY(20px); } to { opacity: 1; transform: translateY(0); } }
.blog-hero-inner { animation: fadeUp 0.6s ease both; }
.post-grid { animation: fadeUp 0.6s ease 0.1s both; }
.post-header-inner { animation: fadeUp 0.6s ease both; }
.post-body-inner { animation: fadeUp 0.5s ease 0.1s both; }

/* RESPONSIVE */
@media (max-width: 900px) {
  .post-grid { grid-template-columns: 1fr 1fr; }
  .post-card:first-child { grid-column: 1 / -1; grid-template-columns: 1fr; }
  .post-card:first-child .post-card-accent { display: none; }
}
@media (max-width: 640px) {
  .site-header { padding: 0 24px; }
  nav { display: none; }
  .blog-hero, .blog-main, .post-header, .post-body, .post-footer, .related-cta { padding-left: 24px; padding-right: 24px; }
  .post-grid { grid-template-columns: 1fr; }
  .cta-card { padding: 36px 28px; }
  .site-footer .container { flex-direction: column; gap: 16px; text-align: center; }
}
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--sand); }
::-webkit-scrollbar-thumb { background: var(--taupe); border-radius: 2px; }
"""

# ── Index Builder ────────────────────────────────────────────────────────────
def build_index(manifest, taxonomy):
    brand = taxonomy.get("brand", "Layer Advisory Services")
    author = taxonomy.get("author", "Erica Layer")
    domain = taxonomy.get("domain", "blog.layeradvisory.com")

    posts = sorted(manifest.get("posts", []), key=lambda p: p.get("published_at", ""), reverse=True)

    cards_html = ""
    for i, post in enumerate(posts):
        slug = post.get("slug", "")
        title = post.get("title", "")
        excerpt = post.get("excerpt", "")
        date = post.get("published_at", "")[:10] if post.get("published_at") else ""
        read_time = post.get("estimated_read_time", 5)
        cluster = post.get("cluster", "").replace("-", " ").title()

        cards_html += f"""
    <a href="/posts/{slug}" class="post-card">
      <div class="post-card-accent"></div>
      <div class="post-card-body">
        <div class="post-card-meta">{date} · {read_time} min read</div>
        <div class="post-card-title">{title}</div>
        <div class="post-card-excerpt">{excerpt}</div>
      </div>
      <div class="post-card-footer">
        <span class="post-card-read">Read more</span>
        <span class="post-card-cluster">{cluster}</span>
      </div>
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
</head>
<body>
  <header class="site-header">
    <a href="https://layeradvisory.com" class="logo">Layer Advisory</a>
    <nav>
      <a href="/posts" class="active">Blog</a>
      <a href="https://layeradvisory.com">Main Site</a>
      <a href="https://calendly.com/erica-layeradvisory/30min" class="btn-nav">Let's Talk</a>
    </nav>
  </header>

  <section class="blog-hero">
    <div class="blog-hero-inner">
      <div class="blog-hero-eyebrow">Insights</div>
      <h1 class="blog-hero-title">The Layer Advisory <em>Blog</em></h1>
      <p class="blog-hero-sub">Practical thinking on operations, leadership, and building organizations that work without founder dependency.</p>
    </div>
  </section>

  <main class="blog-main">
    <div class="blog-main-inner">
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
        <a href="https://layeradvisory.com">Main Site</a>
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
