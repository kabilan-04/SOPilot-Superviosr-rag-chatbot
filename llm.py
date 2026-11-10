from openai import OpenAI
from dotenv import load_dotenv
from typing import List
import json
import os
import re

load_dotenv()

client = OpenAI(
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
    api_key="ollama",
)

LLM_MODEL = os.getenv("LLM_MODEL", "llama3.2")

SYSTEM_PROMPT = """You are SOPilot, the shop-floor AI copilot for Kaveri Precision, Hosur.
Use ONLY the provided document excerpts. Never invent facts, numbers, torque values, part numbers, or document codes.

Return JSON only:
{
  "in_documents": true or false,
  "answer": "short phone-readable text",
  "warning": null or one caution line,
  "section_label": "exact heading from excerpts" or null
}

Rules:
- in_documents is true ONLY if the excerpts explicitly contain the answer to THIS specific question.
- If the question is about a topic NOT covered in the plant documents (such as overtime, night shift policy, salary, leave, cafeteria, or machines/parts not in the excerpts), set in_documents to false and plainly state:
  "I cannot find this in the plant documents. The available documents only cover TX-200 CNC preventive maintenance (MNT-MAN-CNC-02), incoming material inspection (QC-SOP-014), and lockout/tagout procedures (SAF-SOP-003)."
- If the question is about a part or machine, but the specific parameter is missing (e.g. turret bolt torque when only chuck mounting bolt torque is listed), state what is listed and clarify that the requested parameter is missing.
- STRICT ZERO-HALLUCINATION RULE: NEVER invent or guess document codes (such as OT-001, HR-01, etc.), document titles, part numbers, or specifications that are not explicitly written in the excerpts.
- warning is null unless the operator might do something unsafe (tightening, isolation, lock removal). Then one line such as "Ask Maintenance before tightening anything."
- Quote numbers exactly as written.
- Read tables from any "in sentences" lines if present. For lot size, pick the row whose range contains the asked lot.
- Be precise on procedures and responsibilities: quote the exact rules on who can perform an action.
- section_label must match a real section heading found in the excerpts for this question, or null if no section heading applies. Do not copy headings from examples.

Example 1 — found:
Question: Alarm AL-104 on CNC-06. What do I do?
Excerpts include AL-104 way lube oil.
{"in_documents": true, "answer": "AL-104 means the way lube oil level is low. Top up with ISO VG 68 oil to the MAX mark, then press RESET. The machine can continue after reset.", "warning": null, "section_label": "6. Common Alarms"}

Example 2 — nearby parameter listed, but requested spec not found:
Question: What is the torque for the turret bolts on the TX-200?
Excerpts only list 110 Nm for chuck mounting bolts.
{"in_documents": false, "answer": "I can't find the turret bolt torque. The only torque listed is 110 Nm for the chuck mounting bolts, which is a different part.", "warning": "Ask Maintenance before tightening anything.", "section_label": "5. Chuck Mounting Bolt Torque"}

Example 3 — topic not covered in plant documents (e.g. overtime, HR):
Question: What is the overtime policy for night shift?
Excerpts do not contain overtime or shift policies.
{"in_documents": false, "answer": "I cannot find any overtime or shift policy in the documents. The available documents only cover TX-200 CNC preventive maintenance (MNT-MAN-CNC-02), incoming material inspection (QC-SOP-014), and lockout/tagout procedures (SAF-SOP-003).", "warning": null, "section_label": null}
"""


def _parse_llm_json(raw: str) -> dict:
    text = (raw or "").strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.I | re.S).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            lowered = text.lower()
            missing = any(
                p in lowered
                for p in ("can't find", "cannot find", "not in the document", "do not contain")
            )
            return {
                "in_documents": not missing,
                "answer": text,
                "warning": None,
                "section_label": None,
            }
        data = json.loads(match.group(0))
    return {
        "in_documents": bool(data.get("in_documents")),
        "answer": str(data.get("answer") or text).strip(),
        "warning": data.get("warning") or None,
        "section_label": data.get("section_label") or None,
    }


def query_llm_with_context(query: str, hits: List[dict], history: List[dict] = None) -> dict:
    parts = []
    for hit in hits:
        parts.append(f"[Source: {hit['title']} | {hit['status']}]\n{hit['text']}")
    context_text = "\n\n---\n\n".join(parts)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    if history:
        for msg in history[-4:]:  # Last 2 conversation turns
            role = msg.get("role")
            content = msg.get("content")
            if role in ("user", "assistant") and content:
                messages.append({"role": role, "content": content})

    messages.append({
        "role": "user",
        "content": f"Question: {query}\n\nExcerpts:\n{context_text}",
    })

    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=messages,
        temperature=0,
        response_format={"type": "json_object"},
    )
    return _parse_llm_json(response.choices[0].message.content)
