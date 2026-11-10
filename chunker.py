import re
from typing import List


def _sampling_plan_sentences(text: str) -> str:
    """PDF tables come out one cell per line. Rewrite the sampling plan as sentences
    so the 3B model can read 'lot of 200 → 13 samples' instead of a stacked list.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    try:
        i = next(n for n, line in enumerate(lines) if line.lower() == "lot size (pieces)")
    except StopIteration:
        return text
    rows = []
    j = i + 4
    lot_pat = re.compile(r"^(\d+\s*[-–]\s*\d+|Above\s+[\d,]+)$", re.I)
    while j + 3 < len(lines) and lot_pat.match(lines[j]):
        lot, samples, accept, reject = lines[j : j + 4]
        rows.append(
            f"- Lot size {lot} pieces: inspect {samples} samples; "
            f"accept if minor defects are {accept}; reject if minor defects are {reject}."
        )
        j += 4
    if not rows:
        return text
    return text + "\n\nSampling plan in sentences:\n" + "\n".join(rows) + "\n"


def chunk_pages(pages: List[str], chunk_size: int = 1100, chunk_overlap: int = 180) -> List[str]:
    chunks: List[str] = []
    full_text = _sampling_plan_sentences("\n".join(pages))
    text_length = len(full_text)

    if text_length == 0:
        return chunks

    start = 0
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = full_text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= text_length:
            break
        start = end - chunk_overlap

    return chunks
