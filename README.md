# Layer Advisory Services — SEO Blog Engine

A fully automated, voice-consistent content engine that publishes SEO-optimized blog posts in Erica Layer's authentic voice twice a week, with zero ongoing manual effort.

---

## What This Does

- Generates 2 blog posts per week (Tuesday + Friday, 7am UTC) using Claude
- All content written in Erica's specific brand voice using the `SKILL.md` skill file
- Posts target pre-defined keyword clusters across 7 topic areas
- Each post is a complete HTML page with structured data, meta tags, OG image support, and internal linking
- Blog index and sitemap auto-rebuild on every run
- Keyword queue auto-refills every Sunday

## Repository Structure

```
las-blog-automation/
├── SKILL.md                   # Brand voice skill — the heart of the engine
├── taxonomy.json              # Topic clusters, keywords, site config
├── las_blog_build.py          # Main blog builder script
├── las_aqe_pipeline.py        # Keyword queue generator
├── posts_manifest.json        # Master content database (auto-generated)
├── aqe_queue.json             # Prioritized keyword queue (auto-generated)
├── posts/                     # Raw JSON for each post
├── site/
│   ├── posts/
│   │   ├── index.html         # Blog index page
│   │   └── [slug]/index.html  # Individual post pages
│   ├── assets/blog.css        # All styles
│   └── sitemap.xml            # Auto-generated sitemap
└── .github/workflows/
    ├── blog_build.yml         # Publishes posts Tue + Fri
    └── aqe_pipeline.yml       # Refreshes keyword queue Sundays
```

---

## Setup (One Time)

### 1. Create the GitHub repository

```bash
gh repo create las-blog-automation --private
cd las-blog-automation
git init
```

### 2. Add your files

Copy all files from this package into the repository root:
- `SKILL.md`
- `taxonomy.json`
- `las_blog_build.py`
- `las_aqe_pipeline.py`

Create the workflows directory:
```bash
mkdir -p .github/workflows
cp blog_build.yml .github/workflows/
cp aqe_pipeline.yml .github/workflows/
```

### 3. Set up GitHub Secrets

In your repository: **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|--------|-------|
| `ANTHROPIC_API_KEY` | Your Claude API key |

### 4. Enable GitHub Pages

- Go to **Settings → Pages**
- Source: **Deploy from a branch**
- Branch: `main`, folder: `/site`
- Save

Your blog will be live at: `https://[username].github.io/las-blog-automation/`

### 5. Set up custom domain (optional)

Point `blog.layeradvisory.com` to GitHub Pages:

In your DNS (Cloudflare recommended):
```
CNAME  blog  [username].github.io
```

Add `CNAME` file to `/site` directory:
```
blog.layeradvisory.com
```

### 6. Initialize the first queue

Run manually once to populate the keyword queue:

```bash
ANTHROPIC_API_KEY=your-key python3 las_aqe_pipeline.py --generate --count 30
```

### 7. Generate your first batch of posts

```bash
ANTHROPIC_API_KEY=your-key python3 las_blog_build.py --from-queue --count 10
```

Review the posts in `site/posts/`. Adjust `SKILL.md` if any tone adjustments are needed.

### 8. Submit to Google Search Console

1. Go to [search.google.com/search-console](https://search.google.com/search-console)
2. Add property: `https://blog.layeradvisory.com`
3. Submit sitemap: `https://blog.layeradvisory.com/sitemap.xml`

### 9. Enable the workflows

Push everything to GitHub. The workflows will now run automatically.

---

## Manual Commands

```bash
# Generate 5 posts from queue
python3 las_blog_build.py --from-queue --count 5

# Generate a single post on a specific keyword
python3 las_blog_build.py --single --keyword "how to delegate as a founder" --cluster founder-dependency

# Build a cluster pillar page
python3 las_blog_build.py --build-pillar --cluster fractional-leadership

# Check queue status
python3 las_aqe_pipeline.py --status

# Refill queue
python3 las_aqe_pipeline.py --generate --count 20
```

---

## Topic Clusters

| Cluster ID | Topic | Pillar Keyword |
|------------|-------|---------------|
| `founder-dependency` | Founder Dependency | how to stop being the bottleneck as a founder |
| `operational-clarity` | Operational Clarity | operational clarity for growing startups |
| `team-alignment` | Team Alignment | team alignment for scaling organizations |
| `fractional-leadership` | Fractional Leadership | what is a fractional COO |
| `sustainable-growth` | Sustainable Growth | sustainable business growth strategy |
| `hiring-and-roles` | Hiring & Roles | hiring for growing startups |
| `leadership-mindset` | Leadership Mindset | leadership mindset for founders |

---

## Adjusting Brand Voice

All voice configuration is in `SKILL.md`. If a generated post doesn't sound quite right:

1. Open the offending post JSON in `posts/[slug].json`
2. Note what felt off — too formal, wrong structure, wrong vocabulary
3. Update the relevant section in `SKILL.md`
4. Re-run with `--single` on the same keyword to test

The engine improves as you refine `SKILL.md`. It's a living document.

---

## Replicating for a New Client

To deploy this engine for a fractional leader client:

1. Fork or copy this repository, rename it `[client]-blog-automation`
2. Replace `SKILL.md` with their brand voice skill
3. Rebuild `taxonomy.json`: define 5–7 clusters, 30–50 seed keywords
4. Update `domain`, `brand`, `author` fields in `taxonomy.json`
5. Update CTA links in `las_blog_build.py` (Calendly, site URL)
6. Run the initialization sequence above
7. Set their `ANTHROPIC_API_KEY` secret in the new repository

Time estimate: 2–3 hours per client for initial setup, then fully automated.

---

## Estimated API Costs

| Activity | Frequency | Est. Cost |
|----------|-----------|-----------|
| AQE queue generation | Weekly | ~$0.10 |
| Blog post generation (2/week) | Weekly | ~$0.40 |
| **Monthly total** | | **~$2.00** |

*Costs based on Claude Sonnet 4 pricing at ~850 words per post.*

---

Built for Layer Advisory Services · Fractional Back Office platform
