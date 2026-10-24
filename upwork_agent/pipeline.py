"""Filter -> score -> draft for every job waiting in the store."""

import anthropic

from . import claude
from .config import Profile
from .filters import reject_reason
from .store import Store, row_job, row_score


def process(store: Store, profile: Profile, client: anthropic.Anthropic, log=print) -> None:
    for row in store.by_status("new"):
        job = row_job(row)
        reason = reject_reason(job, profile)
        if reason:
            store.mark_filtered(job.id, reason)
            log(f"skip   {job.title[:60]!r}: {reason}")
            continue
        try:
            score = claude.score_job(client, profile, job)
        except claude.ClaudeRefused as exc:
            store.mark_filtered(job.id, f"declined by Claude: {exc}")
            log(f"skip   {job.title[:60]!r}: declined")
            continue
        store.save_score(job.id, score)
        log(f"score  {score.score:3d} {job.title[:60]!r}")

    for row in store.by_status("scored"):
        job, score = row_job(row), row_score(row)
        if not score.can_deliver or score.score < profile.min_score_to_draft:
            continue
        try:
            proposal = claude.draft_proposal(client, profile, job, score)
        except claude.ClaudeRefused as exc:
            log(f"no draft {job.title[:60]!r}: {exc}")
            continue
        store.save_proposal(job.id, proposal)
        log(f"draft  ${proposal.bid_amount:g} {proposal.bid_type} {job.title[:60]!r}")
