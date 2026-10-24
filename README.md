# Upwork job assistant

Finds Upwork jobs that fit your profile, uses Claude to score them, and writes a tailored proposal for
each good match. **You review every draft and click submit yourself.** Upwork's Terms of Service
forbid bots that scrape the site or bid automatically, and breaking them can get the account banned.
This tool stays inside those rules.

```
 Upwork API / pasted job ─▶ rule filters ─▶ Claude score ─▶ Claude proposal ─▶ YOU review & submit
                              (free)         (0-100)        (cover letter,
                                                             bid, answers)
```

## Setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...        # from console.anthropic.com
```

Then edit `config/profile.toml` with your skills, rates, deal-breakers and search terms.
Profile copy to paste into Upwork is in [`docs/UPWORK_PROFILE.md`](docs/UPWORK_PROFILE.md).

## Daily use

```bash
# 1. Get jobs in. Either paste a post (title on the first line)...
pbpaste | python -m upwork_agent add --url "https://www.upwork.com/jobs/~01..."
#    ...or, once you have Upwork API access:
python -m upwork_agent fetch

# 2. Filter, score and draft
python -m upwork_agent run

# 3. Review
python -m upwork_agent list --status drafted
python -m upwork_agent show <job_id>       # cover letter, bid, screening answers

# 4. Submit on Upwork yourself, then record it
python -m upwork_agent mark <job_id> submitted   # or: skipped / hired
```

`python -m upwork_agent export` prints everything as JSON.

## Getting Upwork API access (optional)

1. Apply for a key at <https://www.upwork.com/developer/keys/apply>. Describe it as a personal job
   search tool for your own account. Approval takes days to weeks.
2. Complete the OAuth2 flow to get an access token for your account.
3. `export UPWORK_ACCESS_TOKEN=...` and run `python -m upwork_agent fetch`.

Until then, add jobs by pasting them in. It takes a few seconds per job from your Best Matches feed.

## After you're hired

Open a Claude Code session in a repo for that client's project and give it the job post plus your
messages with the client. Claude builds the deliverable; you check it, run it, and send it.
Tell clients you use AI-assisted development (the profile copy already says so).

## Tests

```bash
python -m pytest -q
```
