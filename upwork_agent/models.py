from typing import Literal, Optional

from pydantic import BaseModel, Field


class Job(BaseModel):
    id: str
    title: str
    description: str
    url: str = ""
    budget_type: Literal["fixed", "hourly", "unknown"] = "unknown"
    budget_min: Optional[float] = None
    budget_max: Optional[float] = None
    skills: list[str] = Field(default_factory=list)
    client_country: str = ""
    client_hires: Optional[int] = None
    client_payment_verified: Optional[bool] = None
    posted_at: str = ""
    source: str = "manual"


class JobScore(BaseModel):
    score: int = Field(description="0-100 fit score for this freelancer")
    can_deliver: bool = Field(description="True if Claude-assisted work can realistically deliver this job")
    reasons: list[str] = Field(description="Short bullet reasons for the score")
    risks: list[str] = Field(description="Red flags or scope risks")


class Proposal(BaseModel):
    cover_letter: str = Field(description="The proposal text to paste into Upwork")
    bid_amount: float = Field(description="Suggested bid in USD (hourly rate or fixed total)")
    bid_type: Literal["fixed", "hourly"]
    estimated_duration: str
    screening_answers: list[str] = Field(
        default_factory=list, description="Answers to screening questions, in order, if any were in the post"
    )
    questions_for_client: list[str] = Field(default_factory=list)
