"""Command line entry point: python -m upwork_agent <command>."""

import argparse
import json
import sys
from pathlib import Path

from .config import DEFAULT_PROFILE, load_profile
from .store import DEFAULT_DB, Store, row_dict, row_job, row_proposal, row_score


def cmd_add(args, store, profile):
    from .sources.manual import job_from_text

    text = Path(args.file).read_text() if args.file else sys.stdin.read()
    job = job_from_text(text, url=args.url or "")
    print(("added " if store.add_job(job) else "already stored ") + job.id)


def cmd_fetch(args, store, profile):
    from .sources import upwork_api

    queries = args.query or profile.search_queries
    added = 0
    for q in queries:
        for job in upwork_api.search(q, limit=args.limit):
            added += store.add_job(job)
    print(f"fetched {len(queries)} searches, {added} new jobs")


def cmd_run(args, store, profile):
    import anthropic

    from .pipeline import process

    process(store, profile, anthropic.Anthropic())


def cmd_list(args, store, profile):
    rows = store.by_status(args.status) if args.status else store.all()
    for row in rows:
        job = row_job(row)
        score = f"{row['score']:3d}" if row["score"] is not None else "  -"
        print(f"{row['status']:<9} {score}  {job.id:<24} {job.title[:70]}")


def cmd_show(args, store, profile):
    row = store.get(args.job_id)
    if not row:
        sys.exit(f"no job {args.job_id}")
    job, score, proposal = row_job(row), row_score(row), row_proposal(row)
    print(f"{job.title}\n{job.url}\nstatus: {row['status']}  {row['filter_reason'] or ''}\n")
    if score:
        print(f"score {score.score}  can_deliver={score.can_deliver}")
        for r in score.reasons:
            print(f"  + {r}")
        for r in score.risks:
            print(f"  ! {r}")
    if proposal:
        print(f"\n--- bid: ${proposal.bid_amount:g} ({proposal.bid_type}), {proposal.estimated_duration} ---\n")
        print(proposal.cover_letter)
        for i, a in enumerate(proposal.screening_answers, 1):
            print(f"\nQ{i}: {a}")
        if proposal.questions_for_client:
            print("\nQuestions to ask:", *proposal.questions_for_client, sep="\n  - ")


def cmd_mark(args, store, profile):
    store.set_status(args.job_id, args.status)
    print(f"{args.job_id} -> {args.status}")


def cmd_export(args, store, profile):
    json.dump([row_dict(r) for r in store.all()], sys.stdout, indent=2)
    print()


def main(argv=None):
    p = argparse.ArgumentParser(prog="upwork_agent", description=__doc__)
    p.add_argument("--profile", default=DEFAULT_PROFILE, type=Path)
    p.add_argument("--db", default=DEFAULT_DB, type=Path)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add", help="add a job by pasting its text (stdin or --file)")
    a.add_argument("--file")
    a.add_argument("--url")
    a.set_defaults(fn=cmd_add)

    f = sub.add_parser("fetch", help="pull jobs from the Upwork API (needs UPWORK_ACCESS_TOKEN)")
    f.add_argument("--query", action="append", help="override the search terms in profile.toml")
    f.add_argument("--limit", type=int, default=20)
    f.set_defaults(fn=cmd_fetch)

    sub.add_parser("run", help="filter, score and draft proposals (needs ANTHROPIC_API_KEY)").set_defaults(fn=cmd_run)

    ls = sub.add_parser("list", help="list jobs")
    ls.add_argument("--status")
    ls.set_defaults(fn=cmd_list)

    s = sub.add_parser("show", help="show a job's score and draft proposal")
    s.add_argument("job_id")
    s.set_defaults(fn=cmd_show)

    m = sub.add_parser("mark", help="record what you did: submitted, skipped, hired")
    m.add_argument("job_id")
    m.add_argument("status", choices=["submitted", "skipped", "hired"])
    m.set_defaults(fn=cmd_mark)

    sub.add_parser("export", help="dump everything as JSON").set_defaults(fn=cmd_export)

    args = p.parse_args(argv)
    args.fn(args, Store(args.db), load_profile(args.profile))


if __name__ == "__main__":
    main()
