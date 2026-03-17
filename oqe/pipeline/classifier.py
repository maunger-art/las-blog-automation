CLUSTER_SIGNALS = {
    "founder-dependency": ["bottleneck","everything through me","cant delegate","doing everything","founder dependency","letting go","micromanage","trust my team","step back"],
    "operational-clarity": ["process","processes","documentation","sop","standard operating","systems","workflow","consistency","documented","playbook","handbook"],
    "team-alignment": ["align","alignment","okr","goals","priorities","quarterly","accountability","scorecard","decision","communication","same page"],
    "fractional-leadership": ["fractional coo","fractional executive","part time coo","what is a fractional","hire a fractional","need a coo","do i need a coo"],
    "sustainable-growth": ["scale","scaling","growing too fast","overwhelmed","burnout","sustainable","capacity","too much on my plate","prioritize","focus"],
    "hiring-and-roles": ["hire","hiring","first hire","job description","role clarity","onboarding","retain","retention","turnover","right person","right seat"],
    "leadership-mindset": ["leadership","founder mindset","ceo mindset","confidence","burnout","work life balance","habits","productivity","decision making"],
}
CONTENT_TYPES = {
    "how-to": ["how do i","how to","how can i","how should i"],
    "what-is": ["what is","what are","what does","explain"],
    "when-to": ["when should","when do i","when is the right time"],
    "comparison": ["vs ","versus","difference between","which is"],
    "story": ["why does","why is","why do"],
}
TOOL_LINKS = {
    "fractional-leadership": {"tool_id":"diagnostic-assessment","tool_url":"https://layeradvisory.com/#diagnostic","cta_copy":"Not sure if you need a fractional COO? Take the 5-minute diagnostic."},
    "founder-dependency": {"tool_id":"diagnostic-assessment","tool_url":"https://layeradvisory.com/#diagnostic","cta_copy":"Find out where founder dependency is costing you most."},
    "operational-clarity": {"tool_id":"diagnostic-assessment","tool_url":"https://layeradvisory.com/#diagnostic","cta_copy":"Discover which operational gaps are slowing your team down."},
}
def match_cluster(text, taxonomy):
    tl = text.lower()
    scores = {}
    for cid, signals in CLUSTER_SIGNALS.items():
        h = sum(1 for s in signals if s in tl)
        if h > 0: scores[cid] = h
    if scores: return max(scores, key=scores.get)
    for c in taxonomy.get("clusters", []):
        h = sum(1 for k in c.get("keywords", []) if k.lower() in tl)
        if h > 0: scores[c["id"]] = h
    return max(scores, key=scores.get) if scores else None

def infer_content_type(text):
    tl = text.lower()
    for ct, signals in CONTENT_TYPES.items():
        if any(tl.startswith(s) or s in tl for s in signals): return ct
    return "how-to"

def classify_question(question, taxonomy):
    text = question.get("normalized_text", question.get("text", ""))
    cid = match_cluster(text, taxonomy)
    if not cid:
        question["status"] = "discarded"; question["discard_reason"] = "no cluster match"; return question
    question["cluster_id"] = cid
    question["content_type"] = infer_content_type(text)
    question["tool_link"] = TOOL_LINKS.get(cid)
    question["status"] = "classified"
    return question
