import re

from embedder import embed_User_query
from vectorstore import search_chunks
from llm import query_llm_with_context

# Below this cosine score we treat the hit as "closest match", not an answer.
MIN_GROUNDED_SCORE = 0.48

GENERIC_SHORT_INPUTS = {
    "hi", "hey", "hello", "help", "test", "what", "why", "who", "info",
    "sop", "docs", "ok", "yes", "no", "how", "good", "morning", "v", "a"
}


FOLLOWUP_TRIGGERS = (
    r"\b(it|its|that|this|they|them|these|those|there|same|also|then)\b|"
    r"^(what about|how about|and\b|what if|why|which form|which tool|who approves|how many|what is its)"
)

# Keyword check: share of the question's meaningful words that appear in the retrieved text.
# Catches gibberish ("jhvu") and off-topic questions ("overtime policy") that still score
# above the similarity threshold. Raise it to be stricter, lower it if real questions get refused.
# 0.3 was tuned on ~18 questions: gibberish scored 0.0, overtime 0.25, real questions 0.36 or more.
MIN_KEYWORD_COVERAGE = 0.3

NOT_IN_DOCS_ANSWER = (
    "That isn't in the documents I have (quality, maintenance and safety procedures). "
    "Ask your supervisor or the relevant department."
)

_STOPWORDS = {
    "the", "and", "for", "are", "was", "were", "what", "which", "who", "whom", "how", "when",
    "where", "why", "can", "could", "should", "would", "does", "did", "has", "have", "had",
    "with", "from", "this", "that", "these", "those", "there", "their", "about", "into", "than",
    "then", "also", "any", "all", "not", "you", "your", "our", "its", "many", "much", "need",
    "tell", "give", "show", "please", "get", "got", "use", "used", "using", "after", "before",
}


def _stem(word: str) -> str:
    return re.sub(r"(ing|ed|es|s)$", "", word) if len(word) > 4 else word


def keyword_coverage(query: str, hits: list) -> float:
    """Fraction of the question's content words found in the retrieved chunks (0 to 1)."""
    words = [w for w in re.findall(r"[a-z][a-z0-9\-]{2,}", query.lower()) if w not in _STOPWORDS]
    if not words:
        return 0.0
    haystack = " ".join(f"{h.get('title', '')} {h.get('text', '')}" for h in hits).lower()
    hay_words = {_stem(w) for w in re.findall(r"[a-z][a-z0-9\-]+", haystack)}
    found = sum(1 for w in words if _stem(w) in hay_words)
    return found / len(words)


def process_user_query(query: str, history: list[dict] = None):
    clean = (query or "").strip()
    alnum_chars = re.findall(r"[a-zA-Z0-9]", clean)

    # If the user enters a single letter (like 'v'), 1-2 chars, or generic greetings
    if len(alnum_chars) < 3 or clean.lower() in GENERIC_SHORT_INPUTS:
        return {
            "answer": "Please enter a complete question (for example: 'Alarm AL-104 on CNC-06', 'Lot of 200: how many samples?', or 'Who can remove a lock?').",
            "in_documents": False,
            "warning": None,
            "section_label": None,
            "sources": [],
            "closest_match": None,
            "clarification": True,
        }

    # Contextual follow-up expansion for vector retrieval
    search_query = query
    last_user_query = None
    if history:
        for msg in reversed(history):
            if msg.get("role") == "user" and msg.get("content"):
                last_user_query = msg["content"].strip()
                break

    if last_user_query and re.search(FOLLOWUP_TRIGGERS, query, re.I):
        search_query = f"{last_user_query} {query}"

    query_vector = embed_User_query(search_query)
    hits = search_chunks(query_vector, top_k=4, query=search_query)

    # Guard: if nothing relevant was found, say so and skip the LLM (faster, and it can't make things up)
    best_score = hits[0]["score"] if hits else 0.0
    if not hits or best_score < MIN_GROUNDED_SCORE or keyword_coverage(search_query, hits) < MIN_KEYWORD_COVERAGE:
        return {
            "answer": NOT_IN_DOCS_ANSWER,
            "in_documents": False,
            "warning": None,
            "section_label": None,
            "sources": [],
            "closest_match": None,
            "clarification": False,
        }

    generated = query_llm_with_context(query, hits, history=history)

    top = hits[0] if hits else None
    in_documents = bool(generated.get("in_documents"))
    answer_l = (generated.get("answer") or "").lower()

    # Robust detection of negative responses (model saying topic/spec is absent)
    negative_patterns = [
        r"can'?t find",
        r"cannot find",
        r"couldn'?t find",
        r"not found",
        r"not listed",
        r"not mentioned",
        r"not covered",
        r"not available",
        r"does not contain",
        r"do not contain",
        r"not in the",
        r"there is no\b",
        r"\bno\b.*in the (?:documents?|excerpts?)",
    ]
    if any(re.search(pat, answer_l, re.I) for pat in negative_patterns):
        in_documents = False
    if top is None or top["score"] < MIN_GROUNDED_SCORE:
        in_documents = False

    sources = []
    for hit in hits:
        sources.append(
            {
                "title": hit["title"],
                "filename": hit["source"],
                "status": hit["status"],
                "score": round(hit["score"], 3),
            }
        )

    section = generated.get("section_label")
    if section:
        clean_sec = re.sub(r"^(section\s*\d+[\s:\.\-]*|\d+[\s:\.\-]+)", "", section, flags=re.I).strip()
        if not any(
            (section.lower() in h["text"].lower())
            or (clean_sec.lower() in h["text"].lower() and len(clean_sec) > 3)
            for h in hits
        ):
            section = None

    if not section and top:
        heading_match = re.search(r"(?:^|\n)(\d+\.\s+[A-Z][A-Za-z0-9\s\-/]{2,50})(?:\n|$)", top.get("text", ""))
        if heading_match:
            section = heading_match.group(1).strip()

    warning = generated.get("warning")
    if not in_documents and re.search(r"torque|tighten|bolt", query, re.I) and not warning:
        warning = "Ask Maintenance before tightening anything."

    closest = None
    # For out-of-document topics (e.g. overtime, HR, canteen):
    # Only attach closest_match if in_documents is True OR it is a genuine related near-miss (score >= 0.62)
    if in_documents or (top and top["score"] >= 0.62 and not any(re.search(pat, answer_l, re.I) for pat in negative_patterns)):
        closest = {
            "title": top["title"],
            "section": section,
            "status": top["status"],
            "filename": top["source"],
        }

    return {
        "answer": generated["answer"],
        "in_documents": in_documents,
        "warning": warning,
        "section_label": section,
        "sources": sources if in_documents else [],
        "closest_match": closest,
        "clarification": False,
    }


if __name__ == "__main__":
    while True:
        user_query = input("\nQuestion: ").strip()
        if not user_query:
            break
        result = process_user_query(user_query)
        print("\nAnswer:", result["answer"])
        print("In documents:", result["in_documents"])
        if result["closest_match"]:
            print("Source:", result["closest_match"]["title"])