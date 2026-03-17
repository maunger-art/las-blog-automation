#!/usr/bin/env python3
"""
las_linkedin_engine.py
Generates, reviews, approves, and posts LinkedIn content from blog posts.

WORKFLOW (nothing posts without your approval):
  1. Generate drafts:  python3 las_linkedin_engine.py --generate
  2. Review drafts:    python3 las_linkedin_engine.py --review
  3. Approve one:      python3 las_linkedin_engine.py --approve --id <slug>
  4. Approve all:      python3 las_linkedin_engine.py --approve --all
  5. Post approved:    python3 las_linkedin_engine.py --post --all
  6. Full status:      python3 las_linkedin_engine.py --status

SAFETY RULES:
  - --post will ONLY publish drafts with status "approved"
  - drafts with status "draft" can NEVER be posted
  - You must explicitly run --approve before anything goes live
"""

import os, json, re, argparse, urllib.request, urllib.parse
from datetime import datetime, timezone
from pathlib import Path
import anthropic

ROOT = Path(__file__).parent
MANIFEST = ROOT / "posts_manifest.json"
SKILL = ROOT / "SKILL.md"
LI_QUEUE = ROOT / "linkedin_queue.json"

STATUSES = {
    "draft":    "Generated — not yet reviewed",
    "approved": "Reviewed and approved — ready to post",
    "posted":   "Published to LinkedIn",
    "rejected": "Reviewed and rejected — will not post",
}

def load(path):
    return json.loads(path.read_text()) if path.exists() else {}

def save(path, data):
    path.write_text(json.dumps(data, indent=2))

def get_queue():
    return load(LI_QUEUE) or {"drafts": [], "posted": []}

LINKEDIN_VOICE_RULES = """
LinkedIn post rules for Erica Layer:

STRUCTURE:
- Line 1: Short declarative statement that surfaces a tension or counterintuitive truth. No question. Does not start with "I".
- Lines 2-8: Very short paragraphs (1-3 sentences). Each paragraph = one idea.
- Final lines: A genuine question that invites reflection or response.
- Optional: 3-5 hashtags on the final line. No emojis in prose.

VOICE:
- Grounded, warm, quietly confident
- Draws on lived experience as CEO at D-tree or current fractional COO work
- Never generic — always specific
- No buzzwords: no synergy, leverage, game-changer, unlock
- No hype, no performative vulnerability
- Reads like a practitioner, not a consultant

AVOID:
- Do not start with "I"
- No bullet point lists
- No headers or bold text
- No emojis except optionally in the hashtag line
- Do not pitch or sell
- Do not summarize the blog post — extract ONE insight and build from lived experience

LENGTH: 150-280 words.
"""

def generate_all():
    manifest = load(MANIFEST)
    skill_text = SKILL.read_text() if SKILL.exists() else ""
    queue = get_queue()

    published_slugs = {p["slug"] for p in manifest.get("posts", [])}
    drafted_slugs = {d["slug"] for d in queue.get("drafts", [])}
    posted_slugs = {d["slug"] for d in queue.get("posted", [])}

    pending = [p for p in manifest.get("posts", [])
               if p["slug"] not in drafted_slugs and p["slug"] not in posted_slugs]

    if not pending:
        print("No new posts to draft. All published posts have drafts.")
        print("Run: python3 las_linkedin_engine.py --review")
        return

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    print(f"Generating LinkedIn drafts for {len(pending)} post(s)...")

    for post in pending:
        print(f"  Drafting: {post['title']}")
        slug = post.get("slug", "")
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
Title: {post.get('title', '')}
Topic: {post.get('cluster', '').replace('-', ' ')}
Excerpt: {post.get('excerpt', '')}
Content: {body_text}

Write ONE LinkedIn post. Extract the single most resonant insight and build from Erica's lived experience. Do not summarize. Make it feel personal and real.

Return ONLY the post text."""

        resp = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=600,
            system=skill_text or "Write in Erica Layer's authentic voice.",
            messages=[{"role": "user", "content": prompt}]
        )

        draft_text = resp.content[0].text.strip()
        draft = {
            "id": slug,
            "slug": slug,
            "blog_title": post["title"],
            "blog_url": f"https://blog.layeradvisory.com/posts/{slug}",
            "draft_text": draft_text,
            "status": "draft",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "cluster": post.get("cluster", ""),
        }
        queue["drafts"].append(draft)
        print(f"  ✓ Draft ready ({len(draft_text.split())} words) — status: DRAFT (needs approval)")

    save(LI_QUEUE, queue)
    print(f"\n✓ {len(pending)} draft(s) saved.")
    print("\nNext step: review and approve before anything can post.")
    print("  python3 las_linkedin_engine.py --review")

def review_drafts():
    queue = get_queue()
    drafts = [d for d in queue.get("drafts", []) if d["status"] == "draft"]

    if not drafts:
        print("No drafts pending review.")
        approved = [d for d in queue.get("drafts", []) if d["status"] == "approved"]
        if approved:
            print(f"{len(approved)} draft(s) already approved and ready to post.")
            print("  python3 las_linkedin_engine.py --post --all")
        return

    print(f"\n{'='*60}")
    print(f"DRAFTS PENDING REVIEW ({len(drafts)})")
    print(f"{'='*60}")
    print("Nothing will post until you run --approve\n")

    for i, d in enumerate(drafts, 1):
        print(f"\n[{i}/{len(drafts)}] {d['blog_title']}")
        print(f"Blog: {d['blog_url']}")
        print(f"Status: {d['status'].upper()}")
        print(f"{'─'*60}")
        print(d["draft_text"])
        print(f"{'─'*60}")
        print(f"Word count: {len(d['draft_text'].split())}")
        print(f"\nTo approve: python3 las_linkedin_engine.py --approve --id {d['id']}")
        print(f"To reject:  python3 las_linkedin_engine.py --reject --id {d['id']}")
        print()

    print(f"To approve all at once: python3 las_linkedin_engine.py --approve --all")

def approve_drafts(draft_id=None, approve_all=False):
    queue = get_queue()
    drafts = queue.get("drafts", [])
    updated = 0

    for d in drafts:
        if d["status"] != "draft":
            continue
        if approve_all or d["id"] == draft_id:
            d["status"] = "approved"
            d["approved_at"] = datetime.now(timezone.utc).isoformat()
            updated += 1
            print(f"  ✓ Approved: {d['blog_title']}")

    if updated == 0:
        print("No matching drafts found to approve.")
        return

    save(LI_QUEUE, queue)
    print(f"\n✓ {updated} draft(s) approved and ready to post.")
    print("  python3 las_linkedin_engine.py --post --all")

def reject_draft(draft_id):
    queue = get_queue()
    for d in queue.get("drafts", []):
        if d["id"] == draft_id and d["status"] == "draft":
            d["status"] = "rejected"
            d["rejected_at"] = datetime.now(timezone.utc).isoformat()
            save(LI_QUEUE, queue)
            print(f"  Rejected: {d['blog_title']}")
            return
    print(f"Draft not found or not in draft status: {draft_id}")

def post_to_linkedin(draft):
    access_token = os.environ.get("LINKEDIN_ACCESS_TOKEN", "")
    person_id = os.environ.get("LINKEDIN_PERSON_ID", "")

    if not access_token or not person_id:
        print("  LinkedIn credentials not configured.")
        print("  Set LINKEDIN_ACCESS_TOKEN and LINKEDIN_PERSON_ID as GitHub secrets.")
        print("  See README section: LinkedIn API Setup")
        return False

    payload = {
        "author": f"urn:li:person:{person_id}",
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": draft["draft_text"]},
                "shareMediaCategory": "ARTICLE",
                "media": [{
                    "status": "READY",
                    "originalUrl": draft.get("blog_url", ""),
                    "title": {"text": draft.get("blog_title", "")},
                }]
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        "https://api.linkedin.com/v2/ugcPosts", data=data,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            result = json.loads(r.read())
        print(f"  ✓ Posted to LinkedIn: {result.get('id', '')}")
        return True
    except Exception as e:
        print(f"  ✗ LinkedIn API error: {e}")
        return False

def post_approved(post_id=None, post_all=False):
    queue = get_queue()
    drafts = queue.get("drafts", [])

    # SAFETY CHECK — only approved drafts can be posted
    if post_all:
        targets = [d for d in drafts if d["status"] == "approved"]
    elif post_id:
        targets = [d for d in drafts if d["id"] == post_id and d["status"] == "approved"]
    else:
        print("Specify --id <slug> or --all")
        return

    if not targets:
        print("No approved drafts found to post.")
        pending = [d for d in drafts if d["status"] == "draft"]
        if pending:
            print(f"  {len(pending)} draft(s) need approval first.")
            print("  python3 las_linkedin_engine.py --review")
            print("  python3 las_linkedin_engine.py --approve --all")
        return

    print(f"Posting {len(targets)} approved draft(s) to LinkedIn...")
    posted = []
    for draft in targets:
        print(f"  Posting: {draft['blog_title']}")
        success = post_to_linkedin(draft)
        if success:
            draft["status"] = "posted"
            draft["posted_at"] = datetime.now(timezone.utc).isoformat()
            queue["posted"].append(draft)
            posted.append(draft)

    posted_ids = {d["id"] for d in posted}
    queue["drafts"] = [d for d in drafts if d["id"] not in posted_ids]
    save(LI_QUEUE, queue)
    print(f"\n✓ {len(posted)} post(s) published to LinkedIn")

def show_status():
    queue = get_queue()
    drafts = queue.get("drafts", [])
    posted = queue.get("posted", [])

    draft_count = sum(1 for d in drafts if d["status"] == "draft")
    approved_count = sum(1 for d in drafts if d["status"] == "approved")
    rejected_count = sum(1 for d in drafts if d["status"] == "rejected")

    print(f"\n{'='*50}")
    print("LinkedIn Content Engine — Status")
    print(f"{'='*50}")
    print(f"  Drafts (need review):  {draft_count}")
    print(f"  Approved (ready):      {approved_count}")
    print(f"  Rejected:              {rejected_count}")
    print(f"  Posted:                {len(posted)}")
    print(f"{'='*50}")

    if draft_count:
        print(f"\nPending review ({draft_count}):")
        for d in drafts:
            if d["status"] == "draft":
                print(f"  [{d['id']}] {d['blog_title']}")
                print(f"  Preview: {d['draft_text'][:100]}...")
                print()

    if approved_count:
        print(f"\nApproved — ready to post ({approved_count}):")
        for d in drafts:
            if d["status"] == "approved":
                print(f"  [{d['id']}] {d['blog_title']}")
        print(f"\n  Run: python3 las_linkedin_engine.py --post --all")

    if posted:
        print(f"\nPosted ({len(posted)}):")
        for d in posted[-3:]:
            print(f"  [{d.get('posted_at','')[:10]}] {d['blog_title']}")

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="LinkedIn Content Engine — Erica Layer")
    p.add_argument("--generate", action="store_true", help="Generate drafts for new blog posts")
    p.add_argument("--review", action="store_true", help="Review all pending drafts")
    p.add_argument("--approve", action="store_true", help="Approve draft(s) for posting")
    p.add_argument("--reject", action="store_true", help="Reject a draft")
    p.add_argument("--post", action="store_true", help="Post APPROVED drafts to LinkedIn")
    p.add_argument("--status", action="store_true", help="Show queue status")
    p.add_argument("--id", type=str, help="Specific post slug")
    p.add_argument("--all", action="store_true", dest="do_all", help="Apply to all")
    args = p.parse_args()

    if args.generate:   generate_all()
    elif args.review:   review_drafts()
    elif args.approve:  approve_drafts(draft_id=args.id, approve_all=args.do_all)
    elif args.reject:   reject_draft(args.id)
    elif args.post:     post_approved(post_id=args.id, post_all=args.do_all)
    elif args.status:   show_status()
    else: p.print_help()
