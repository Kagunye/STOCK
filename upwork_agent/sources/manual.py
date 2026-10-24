"""Add a job by pasting its post text (title on the first line)."""

import hashlib
import re

from ..models import Job

_UPWORK_ID = re.compile(r"~0?[0-9a-f]{10,}")


def job_from_text(text: str, url: str = "") -> Job:
    text = text.strip()
    if not text:
        raise ValueError("job text is empty")
    title, _, body = text.partition("\n")
    match = _UPWORK_ID.search(url)
    job_id = match.group(0) if match else "manual-" + hashlib.sha1(text.encode()).hexdigest()[:12]
    budget_type, lo, hi = _guess_budget(text)
    return Job(
        id=job_id,
        title=title.strip(),
        description=body.strip() or title.strip(),
        url=url,
        budget_type=budget_type,
        budget_min=lo,
        budget_max=hi,
        source="manual",
    )


def _guess_budget(text: str):
    hourly = re.search(r"\$(\d+(?:\.\d+)?)\s*-\s*\$(\d+(?:\.\d+)?)\s*(?:/hr|per hour|hourly)", text, re.I)
    if hourly:
        return "hourly", float(hourly.group(1)), float(hourly.group(2))
    fixed = re.search(r"(?:fixed[- ]price|budget)[^$\n]{0,20}\$(\d[\d,]*(?:\.\d+)?)", text, re.I)
    if fixed:
        value = float(fixed.group(1).replace(",", ""))
        return "fixed", value, value
    return "unknown", None, None
