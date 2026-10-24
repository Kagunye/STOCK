from types import SimpleNamespace

import pytest

from upwork_agent import claude
from upwork_agent.config import load_profile
from upwork_agent.filters import reject_reason
from upwork_agent.models import Job, JobScore, Proposal
from upwork_agent.pipeline import process
from upwork_agent.sources.manual import job_from_text
from upwork_agent.sources.upwork_api import _to_job
from upwork_agent.store import Store, row_proposal


@pytest.fixture
def profile():
    return load_profile()


def job(**kw):
    base = dict(id="j1", title="Python trading bot", description="Build a backtester", budget_type="fixed",
                budget_min=500, budget_max=500, client_payment_verified=True, client_hires=3)
    base.update(kw)
    return Job(**base)


def test_filters(profile):
    assert reject_reason(job(), profile) is None
    assert "keyword" in reject_reason(job(description="guaranteed profit bot"), profile)
    assert "below" in reject_reason(job(budget_max=50), profile)
    assert "below" in reject_reason(job(budget_type="hourly", budget_max=10), profile)
    assert "verified" in reject_reason(job(client_payment_verified=False), profile)


def test_manual_job_parsing():
    j = job_from_text("Stock scraper\nNeed a scraper. Hourly: $30-$50/hr", url="https://www.upwork.com/jobs/~01abcdef1234567890")
    assert j.id == "~01abcdef1234567890"
    assert (j.budget_type, j.budget_min, j.budget_max) == ("hourly", 30, 50)
    assert job_from_text("T\nFixed-price budget: $1,200").budget_max == 1200


def test_api_mapping():
    j = _to_job({"id": "1", "ciphertext": "~01ab", "title": "t", "description": "d",
                 "amount": {"rawValue": "0"}, "hourlyBudgetMin": {"rawValue": "25"}, "hourlyBudgetMax": {"rawValue": "40"},
                 "skills": [{"name": "Python"}], "client": {"totalHires": 2, "verificationStatus": "VERIFIED",
                                                           "location": {"country": "US"}}})
    assert j.budget_type == "hourly" and j.budget_max == 40 and j.client_payment_verified
    assert j.url.endswith("~01ab")


def test_strict_schema_requires_all_fields():
    schema = claude._strict_schema(Proposal)
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])


def test_pipeline_with_fake_claude(tmp_path, profile, monkeypatch):
    store = Store(tmp_path / "jobs.db")
    store.add_job(job(id="good"))
    store.add_job(job(id="cheap", budget_max=20))
    store.add_job(job(id="meh"))

    def fake_score(client, profile, j):
        return JobScore(score=90 if j.id == "good" else 40, can_deliver=True, reasons=["fit"], risks=[])

    def fake_draft(client, profile, j, score):
        return Proposal(cover_letter="hello", bid_amount=450, bid_type="fixed", estimated_duration="1 week")

    monkeypatch.setattr(claude, "score_job", fake_score)
    monkeypatch.setattr(claude, "draft_proposal", fake_draft)
    process(store, profile, client=SimpleNamespace(), log=lambda *_: None)

    assert store.get("cheap")["status"] == "filtered"
    assert store.get("meh")["status"] == "scored"
    assert store.get("good")["status"] == "drafted"
    assert row_proposal(store.get("good")).bid_amount == 450

    store.set_status("good", "submitted")
    assert store.get("good")["status"] == "submitted"
    with pytest.raises(ValueError):
        store.set_status("good", "bogus")
