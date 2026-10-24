"""Cheap rule-based checks run before any Claude call."""

from typing import Optional

from .config import Profile
from .models import Job


def reject_reason(job: Job, profile: Profile) -> Optional[str]:
    """Return why a job should be skipped, or None if it passes."""
    text = f"{job.title}\n{job.description}".lower()
    for kw in profile.exclude_keywords:
        if kw in text:
            return f"excluded keyword: {kw!r}"

    if job.budget_type == "fixed" and job.budget_max is not None and job.budget_max < profile.min_fixed_budget:
        return f"fixed budget ${job.budget_max:g} below ${profile.min_fixed_budget:g}"
    if job.budget_type == "hourly" and job.budget_max is not None and job.budget_max < profile.min_hourly_rate:
        return f"hourly max ${job.budget_max:g} below ${profile.min_hourly_rate:g}"

    if profile.require_payment_verified and job.client_payment_verified is False:
        return "client payment not verified"
    if job.client_hires is not None and job.client_hires < profile.min_client_hires:
        return f"client has {job.client_hires} hires (< {profile.min_client_hires})"
    return None
