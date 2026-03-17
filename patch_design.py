#!/usr/bin/env python3
"""
Patch script — updates las_blog_build.py with new design matching layeradvisory.com
Run from inside ~/Desktop/las-blog-automation/
"""

import re
from pathlib import Path

BUILDER = Path("las_blog_build.py")

if not BUILDER.exists():
    print("ERROR: las_blog_build.py not found. Make sure you're in ~/Desktop/las-blog-automation/")
    exit(1)

# ── New write_post_html function ──────────────────────────────────────────────
NEW_POST_HTML = '''# ── HTML Post Writer ─────────────────────────────────────────────────────────
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
    tags_html = " ".join(f\'<span class="tag">#{t}</span>\' for t in tags)
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
      <a href="https://calendly.com/erica-layeradvisory/30min" class="btn-nav">Let\'s Talk</a>
    </nav>
  </header>

  <article class="post-article">
    <div class="post-header">
      <div class="post-header-inner">
        <div class="post-meta">
          {pub_date} <span>·</span> {read_time} min read <span>·</span> {cluster}
        </div>
        <h1 class="post-title">{title}</h1>
        <p class="post-excerpt">{post_data.get(\'excerpt\', meta_desc)}</p>
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

'''

# ── New write_blog_css function ───────────────────────────────────────────────
NEW_CSS = '''# ── CSS Generator ────────────────────────────────────────────────────────────
def write_blog_css():
    return """@import url(\'https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400;1,500&family=Montserrat:wght@300;400;500;600;700&family=DM+Sans:ital,wght@0,300;0,400;0,500;1,300;1,400&display=swap\');

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
body { font-family: \'DM Sans\', sans-serif; background: var(--white); color: var(--charcoal-mid); line-height: 1.7; }
h1, h2, h3 { font-family: \'Cormorant Garamond\', serif; font-weight: 400; line-height: 1.15; letter-spacing: -0.01em; }

/* HEADER */
.site-header { background: var(--slate-dark); padding: 0 48px; height: 68px; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 100; border-bottom: 1px solid rgba(196,169,125,0.15); }
.logo { font-family: \'Montserrat\', sans-serif; font-size: 12px; font-weight: 600; letter-spacing: 0.18em; text-transform: uppercase; color: var(--white); text-decoration: none; opacity: 0.9; transition: opacity 0.2s; }
.logo:hover { opacity: 1; }
nav { display: flex; align-items: center; gap: 32px; }
nav a { font-family: \'Montserrat\', sans-serif; font-size: 11px; font-weight: 500; letter-spacing: 0.1em; text-transform: uppercase; color: rgba(255,255,255,0.6); text-decoration: none; transition: color 0.2s; }
nav a:hover { color: var(--gold); }
.btn-nav { color: var(--gold) !important; border: 1px solid rgba(196,169,125,0.4); padding: 8px 20px; border-radius: 2px; transition: all 0.2s !important; }
.btn-nav:hover { background: var(--gold) !important; color: var(--slate-dark) !important; }

/* BLOG HERO */
.blog-hero { background: var(--slate-dark); padding: 80px 48px 72px; position: relative; overflow: hidden; }
.blog-hero::before { content: \'\'; position: absolute; inset: 0; background: radial-gradient(ellipse at 80% 50%, rgba(196,169,125,0.06) 0%, transparent 60%); pointer-events: none; }
.blog-hero-inner { max-width: 1100px; margin: 0 auto; position: relative; }
.blog-hero-eyebrow { font-family: \'Montserrat\', sans-serif; font-size: 10px; font-weight: 600; letter-spacing: 0.2em; text-transform: uppercase; color: var(--gold); margin-bottom: 16px; display: flex; align-items: center; gap: 12px; }
.blog-hero-eyebrow::before { content: \'\'; display: block; width: 32px; height: 1px; background: var(--gold); opacity: 0.6; }
.blog-hero-title { font-family: \'Cormorant Garamond\', serif; font-size: clamp(42px, 6vw, 68px); font-weight: 300; color: var(--white); line-height: 1.08; margin-bottom: 20px; letter-spacing: -0.02em; }
.blog-hero-title em { font-style: italic; color: var(--gold); }
.blog-hero-sub { font-family: \'DM Sans\', sans-serif; font-size: 16px; font-weight: 300; color: rgba(255,255,255,0.5); max-width: 480px; line-height: 1.65; }

/* POST GRID */
.blog-main { background: var(--sand); padding: 72px 48px; }
.blog-main-inner { max-width: 1100px; margin: 0 auto; }
.post-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 28px; }
.post-card:first-child { grid-column: 1 / -1; display: grid; grid-template-columns: 1fr 1fr; gap: 0; }
.post-card:first-child .post-card-body { padding: 44px 48px; }
.post-card:first-child .post-card-title { font-size: clamp(26px, 3vw, 36px); }
.post-card:first-child .post-card-footer { padding: 20px 48px; }
.post-card:first-child .post-card-accent { display: block; background: var(--slate-dark); min-height: 260px; position: relative; overflow: hidden; }
.post-card:first-child .post-card-accent::after { content: \'\'; position: absolute; inset: 0; background: radial-gradient(ellipse at 30% 70%, rgba(196,169,125,0.15) 0%, transparent 60%); }
.post-card { background: var(--white); border-radius: 2px; overflow: hidden; text-decoration: none; display: flex; flex-direction: column; transition: transform 0.25s ease, box-shadow 0.25s ease; border: 1px solid var(--sand-dark); }
.post-card:hover { transform: translateY(-3px); box-shadow: 0 16px 48px rgba(37,53,69,0.1); }
.post-card-accent { display: none; }
.post-card-body { padding: 28px 28px 20px; flex: 1; display: flex; flex-direction: column; }
.post-card-meta { font-family: \'Montserrat\', sans-serif; font-size: 9.5px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--taupe); margin-bottom: 14px; display: flex; align-items: center; gap: 8px; }
.post-card-meta::before { content: \'\'; display: block; width: 20px; height: 1px; background: var(--gold); opacity: 0.7; }
.post-card-title { font-family: \'Cormorant Garamond\', serif; font-size: 22px; font-weight: 400; color: var(--slate-dark); line-height: 1.2; margin-bottom: 12px; flex: 1; transition: color 0.2s; }
.post-card:hover .post-card-title { color: var(--slate-mid); }
.post-card-excerpt { font-family: \'DM Sans\', sans-serif; font-size: 13.5px; font-weight: 300; color: var(--charcoal-soft); line-height: 1.65; opacity: 0.8; }
.post-card-footer { padding: 16px 28px 24px; display: flex; align-items: center; justify-content: space-between; border-top: 1px solid var(--sand-dark); margin-top: 20px; }
.post-card-read { font-family: \'Montserrat\', sans-serif; font-size: 10px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--gold); display: flex; align-items: center; gap: 8px; transition: gap 0.2s; }
.post-card:hover .post-card-read { gap: 14px; }
.post-card-read::after { content: \'→\'; font-size: 12px; }
.post-card-cluster { font-family: \'Montserrat\', sans-serif; font-size: 9px; font-weight: 500; letter-spacing: 0.08em; text-transform: uppercase; color: var(--taupe); opacity: 0.6; }

/* POST ARTICLE */
.post-header { background: var(--slate-dark); padding: 80px 48px 72px; position: relative; overflow: hidden; }
.post-header::before { content: \'\'; position: absolute; inset: 0; background: radial-gradient(ellipse at 80% 50%, rgba(196,169,125,0.07) 0%, transparent 60%); pointer-events: none; }
.post-header-inner { max-width: 720px; margin: 0 auto; position: relative; }
.post-meta { font-family: \'Montserrat\', sans-serif; font-size: 10px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--gold); margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
.post-meta span { color: rgba(255,255,255,0.3); }
.post-title { font-family: \'Cormorant Garamond\', serif; font-size: clamp(36px, 5vw, 58px); font-weight: 300; color: var(--white); line-height: 1.08; margin-bottom: 24px; letter-spacing: -0.02em; }
.post-excerpt { font-family: \'DM Sans\', sans-serif; font-size: 17px; font-weight: 300; color: rgba(255,255,255,0.5); line-height: 1.65; max-width: 560px; }

/* POST BODY */
.post-body { padding: 72px 48px; background: var(--white); }
.post-body-inner { max-width: 680px; margin: 0 auto; }
.post-body p { font-family: \'DM Sans\', sans-serif; font-size: 17px; font-weight: 300; color: var(--charcoal-mid); line-height: 1.75; margin-bottom: 26px; }
.post-body h2 { font-family: \'Cormorant Garamond\', serif; font-size: 30px; font-weight: 400; color: var(--slate-dark); margin: 52px 0 20px; }
.post-body strong { font-weight: 600; color: var(--charcoal); }
.post-body em { font-style: italic; }
.post-body ul, .post-body ol { padding-left: 0; margin-bottom: 26px; list-style: none; }
.post-body li { font-family: \'DM Sans\', sans-serif; font-size: 17px; font-weight: 300; color: var(--charcoal-mid); line-height: 1.7; margin-bottom: 12px; padding-left: 20px; position: relative; }
.post-body li::before { content: \'—\'; position: absolute; left: 0; color: var(--gold); }

/* POST FOOTER */
.post-footer { background: var(--sand); padding: 52px 48px; border-top: 1px solid var(--sand-dark); }
.post-footer-inner { max-width: 680px; margin: 0 auto; }
.post-tags { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 40px; }
.tag { font-family: \'Montserrat\', sans-serif; font-size: 9px; font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; color: var(--slate-mid); background: rgba(75,99,122,0.07); border: 1px solid rgba(75,99,122,0.12); padding: 5px 12px; border-radius: 1px; }
.author-card { background: var(--slate-dark); padding: 36px 40px; border-radius: 2px; display: flex; flex-direction: column; gap: 12px; }
.author-name { font-family: \'Montserrat\', sans-serif; font-size: 11px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--gold); }
.author-bio { font-family: \'DM Sans\', sans-serif; font-size: 14px; font-weight: 300; color: rgba(255,255,255,0.55); line-height: 1.65; }
.cta-link { font-family: \'Montserrat\', sans-serif; font-size: 10.5px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: var(--gold); text-decoration: none; display: inline-flex; align-items: center; gap: 8px; transition: gap 0.2s; margin-top: 4px; }
.cta-link::after { content: \'→\'; }
.cta-link:hover { gap: 14px; }

/* CTA SECTION */
.related-cta { background: var(--white); padding: 72px 48px; border-top: 1px solid var(--sand-dark); }
.cta-card { max-width: 680px; margin: 0 auto; background: var(--slate-dark); padding: 52px 56px; border-radius: 2px; position: relative; overflow: hidden; }
.cta-card::before { content: \'\'; position: absolute; inset: 0; background: radial-gradient(ellipse at 80% 20%, rgba(196,169,125,0.08) 0%, transparent 60%); }
.cta-eyebrow { font-family: \'Montserrat\', sans-serif; font-size: 9.5px; font-weight: 600; letter-spacing: 0.2em; text-transform: uppercase; color: var(--gold); margin-bottom: 16px; display: flex; align-items: center; gap: 12px; position: relative; }
.cta-eyebrow::before { content: \'\'; width: 24px; height: 1px; background: var(--gold); opacity: 0.6; }
.cta-title { font-family: \'Cormorant Garamond\', serif; font-size: 36px; font-weight: 300; color: var(--white); line-height: 1.15; margin-bottom: 16px; position: relative; }
.cta-body { font-family: \'DM Sans\', sans-serif; font-size: 15px; font-weight: 300; color: rgba(255,255,255,0.5); line-height: 1.65; margin-bottom: 28px; max-width: 420px; position: relative; }
.btn-primary { display: inline-flex; align-items: center; gap: 10px; font-family: \'Montserrat\', sans-serif; font-size: 10.5px; font-weight: 600; letter-spacing: 0.14em; text-transform: uppercase; color: var(--slate-dark); background: var(--gold); padding: 14px 28px; border-radius: 2px; text-decoration: none; transition: all 0.2s; position: relative; }
.btn-primary:hover { background: var(--gold-light); transform: translateY(-1px); }

/* SITE FOOTER */
.site-footer { background: var(--slate-dark); padding: 40px 48px; border-top: 1px solid rgba(196,169,125,0.15); }
.site-footer .container { max-width: 1100px; margin: 0 auto; display: flex; align-items: center; justify-content: space-between; }
.footer-brand { font-family: \'Montserrat\', sans-serif; font-size: 11px; font-weight: 600; letter-spacing: 0.15em; text-transform: uppercase; color: rgba(255,255,255,0.5); }
.footer-tagline { font-family: \'Cormorant Garamond\', serif; font-size: 14px; font-style: italic; color: var(--gold); opacity: 0.7; }
.footer-links { display: flex; gap: 28px; }
.footer-links a { font-family: \'Montserrat\', sans-serif; font-size: 10px; font-weight: 500; letter-spacing: 0.1em; text-transform: uppercase; color: rgba(255,255,255,0.35); text-decoration: none; transition: color 0.2s; }
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

'''

# ── New build_index function ──────────────────────────────────────────────────
NEW_INDEX = '''# ── Index Builder ────────────────────────────────────────────────────────────
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
      <a href="https://calendly.com/erica-layeradvisory/30min" class="btn-nav">Let\'s Talk</a>
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

'''

# ── Apply patches ─────────────────────────────────────────────────────────────
content = BUILDER.read_text()

# Replace write_post_html
content = re.sub(
    r'# ── HTML Post Writer.*?return html\n\n',
    NEW_POST_HTML,
    content,
    flags=re.DOTALL
)

# Replace write_blog_css
content = re.sub(
    r'# ── CSS Generator.*?"""\n\n',
    NEW_CSS,
    content,
    flags=re.DOTALL
)

# Replace build_index
content = re.sub(
    r'# ── Index Builder.*?return f""".*?"""\n\n',
    NEW_INDEX,
    content,
    flags=re.DOTALL
)

BUILDER.write_text(content)
print("✓ las_blog_build.py patched with new design")
print("")
print("Now run:")
print("  python3 las_blog_build.py --rebuild-all")
print("  git add -A")
print('  git commit -m "Redesign: match layeradvisory.com aesthetic"')
print("  git push origin main")
