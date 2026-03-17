#!/usr/bin/env python3
"""
las_linkedin_engine.py
Generates LinkedIn post drafts from published blog posts in Erica Layer's voice.
Optionally auto-posts via LinkedIn API.

Usage:
  python3 las_linkedin_engine.py --generate          # Draft posts for any unpublished blog posts
  python3 las_linkedin_engine.py --post --id <id>    # Post a specific draft to LinkedIn
  python3 las_linkedin_engine.py --post --all        # Post all approved drafts
  python3 las_linkedin_engine.py --status            # Show queue status
"""

import os, json, re, argparse, urllib.request, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
import anthropic

ROOT = Path(__file__).parent
MANIFEST = ROOT / "posts_manifest.json"
SKILL = ROOT / "SKILL.md"
LI_QUEUE = ROOT / "linkedin_queue.json"

def load(path):
    return json.loads(path.read_text()) if path.exists() else {}

def save(path, data):
    path.write_text(json.dumps(data, indent=2))

# ── VOICE RULES ───────────────────────────────────────────────────────────────
LINKEDIN_VOICE_RULES = """
LinkedIn post rules for Erica Layer:

STRUCTURE:
- Line 1: Short declarative statement that surfaces a tension or counterintuitive truth. No question. No "I".
- Lines 2-8: Very short paragraphs (1-3 sentences). Each paragraph = one idea.
- Line 9+: A genuine question that invites reflection or response.
- Optional: 3-5 hashtags on the final line, no emojis in prose.

VOICE:
- Grounded, warm, quietly confident
- Draws on lived experience as CEO at D-tree or current fractional COO work
- Never generic — always specific
- No buzzwords: no "synergy", "leverage", "game-changer", "unlock"
- No hype, no performative vulnerability
- Reads like a practitioner, not a consultant

WHAT TO AVOID:
- Do not start with "I"
- No bullet point lists
- No headers or bold text
- No emojis except optionally in the hashtag line
- Do not pitch or sell — open conversations, never close them
- Do not summarize the blog post — extract one insight and build from lived experience

LENGTH: 150-280 words maximum.

EXAMPLES OF GOOD OPENING LINES:
- "Slack time isn't wasted time. It's leadership time."
- "Most founders don't have a people problem. They have a systems problem."
- "The moment growth starts to feel chaotic, the instinct is to work harder. That's usually the wrong move."
- "He needed the business to keep growing. But growth was the one thing he no longer had the capacity to manage."
"""

def generate_post(blog_post, skill_text):
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    
    title = blog_post.get("title", "")
    excerpt = blog_post.get("excerpt", "")
    cluster = blog_post.get("cluster", "").replace("-", " ")
    keyword = blog_post.get("primary_keyword", "")
    slug = blog_post.get("slug", "")
    
    # Read the full post HTML if available
    post_file = ROOT / "posts" / f"{slug}.json"
    body_text = ""
    if post_file.exists():
        post_data = load(post_file)
        body_html = post_data.get("body_html", "")
        body_text = re.sub(r'<[^>]+>', ' ', body_html)
        body_text = re.sub(r'\s+', ' ', body_text).strip()[:1500]

    prompt = f"""You are writing a LinkedIn post for Erica Layer, Fractional COO at Layer Advisory Services.

{LINKEDIN_VOICE_RULES}

Blog post to draw from:
Title: {title}
Topic: {cluster}
Excerpt: {excerpt}
Content summary: {body_text}

Write ONE LinkedIn post. Extract the single most resonant insight from this post and build a short, grounded piece from Erica's lived experience. Do not summarize the blog post. Make it feel personal and real.

Return ONLY the post text. No preamble, no quotes, no explanation."""

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=600,
        system=skill_text if skill_text else "You write in Erica Layer's authentic voice.",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return resp.content[0].text.strip()

def generate_all():
    manifest = load(MANIFEST)
    skill_text = SKILL.read_text() if SKILL.exists() else ""
    queue = load(LI_QUEUE) or {"drafts": [], "posted": []}
    
    published_slugs = {p["slug"] for p in manifest.get("posts", [])}
    drafted_slugs = {d["slug"] for d in queue.get("drafts", [])}
    posted_slugs = {d["slug"] for d in queue.get("posted", [])}
    
    pending = [p for p in manifest.get("posts", [])
               if p["slug"] not in drafted_slugs and p["slug"] not in posted_slugs]
    
    if not pending:
        print("No new posts to draft LinkedIn content for.")
        return
    
    print(f"Generating LinkedIn drafts for {len(pending)} post(s)...")
    
    for post in pending:
        print(f"  Drafting: {post['title']}")
        draft_text = generate_post(post, skill_text)
        
        draft = {
            "id": post["slug"],
            "slug": post["slug"],
            "blog_title": post["title"],
            "blog_url": f"https://blog.layeradvisory.com/posts/{post['slug']}",
            "draft_text": draft_text,
            "status": "draft",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "cluster": post.get("cluster", ""),
        }
        
        queue["drafts"].append(draft)
        print(f"  ✓ Draft ready ({len(draft_text.split())} words)")
    
    save(LI_QUEUE, queue)
    print(f"\n✓ {len(pending)} draft(s) saved to linkedin_queue.json")
    print("  Review drafts, then run: python3 las_linkedin_engine.py --post --all")

def post_to_linkedin(draft):
    access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
    person_id = os.environ.get("LINKEDIN_PERSON_ID", "")
    
    if not access_token or not person_id:
        print("  Missing LINKEDIN_ACCESS_TOKEN or LINKEDIN_PERSON_ID env vars.")
        print("  Set these up first: see README section 'LinkedIn API Setup'")
        return False
    
    post_text = draft["draft_text"]
    blog_url = draft.get("blog_url", "")
    
    # LinkedIn UGC Post API
    payload = {
        "author": f"urn:li:person:{person_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": post_text},
                "shareMediaCategory": "ARTICLE",
                "media": [{
                    "status": "READY",
                    "originalUrl": blog_url,
                    "title": {"text": draft.get("blog_title", "")},
                }]
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }
    
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://api.linkedin.com/v2/ugcPosts",
        data=data,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }
    )
    
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            result = json.loads(r.read())
        print(f"  ✓ Posted to LinkedIn: {result.get('id','')}")
        return True
    except Exception as e:
        print(f"  ✗ LinkedIn API error: {e}")
        return False

def post_drafts(post_id=None, post_all=False):
    queue = load(LI_QUEUE) or {"drafts": [], "posted": []}
    drafts = queue.get("drafts", [])
    
    if post_id:
        targets = [d for d in drafts if d["id"] == post_id]
    elif post_all:
        targets = [d for d in drafts if d["status"] == "draft"]
    else:
        print("Specify --id <slug> or --all")
        return
    
    if not targets:
        print("No matching drafts found.")
        return
    
    posted = []
    for draft in targets:
        print(f"  Posting: {draft['blog_title']}")
        success = post_to_linkedin(draft)
        if success:
            draft["status"] = "posted"
            draft["posted_at"] = datetime.now(timezone.utc).isoformat()
            queue["posted"].append(draft)
            posted.append(draft)
    
    # Remove posted from drafts
    posted_ids = {d["id"] for d in posted}
    queue["drafts"] = [d for d in drafts if d["id"] not in posted_ids]
    save(LI_QUEUE, queue)
    print(f"\n✓ {len(posted)} post(s) published to LinkedIn")

def show_status():
    queue = load(LI_QUEUE) or {"drafts": [], "posted": []}
    drafts = queue.get("drafts", [])
    posted = queue.get("posted", [])
    
    print(f"\nLinkedIn Queue Status")
    print(f"  Drafts pending: {len(drafts)}")
    print(f"  Posted: {len(posted)}")
    
    if drafts:
        print("\nPending drafts:")
        for d in drafts:
            print(f"  [{d['id']}] {d['blog_title']}")
            print(f"  Preview: {d['draft_text'][:120]}...")
            print()

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--generate", action="store_true")
    p.add_argument("--post", action="store_true")
    p.add_argument("--id", type=str)
    p.add_argument("--all", action="store_true", dest="post_all")
    p.add_argument("--status", action="store_true")
    args = p.parse_args()
    
    if args.generate: generate_all()
    elif args.post: post_drafts(post_id=args.id, post_all=args.post_all)
    elif args.status: show_status()
    else: p.print_help()
