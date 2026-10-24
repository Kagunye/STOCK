import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_PROFILE = Path(__file__).resolve().parent.parent / "config" / "profile.toml"


@dataclass
class Profile:
    name: str
    title: str
    hourly_rate: float
    min_fixed_budget: float
    min_hourly_rate: float
    skills: list[str]
    highlights: list[str]
    exclude_keywords: list[str] = field(default_factory=list)
    min_client_hires: int = 0
    require_payment_verified: bool = True
    min_score_to_draft: int = 70
    search_queries: list[str] = field(default_factory=list)


def load_profile(path: Path = DEFAULT_PROFILE) -> Profile:
    data = tomllib.loads(Path(path).read_text())
    f = data["freelancer"]
    filters = data.get("filters", {})
    api = data.get("upwork_api", {})
    return Profile(
        name=f["name"],
        title=f["title"],
        hourly_rate=f["hourly_rate"],
        min_fixed_budget=f["min_fixed_budget"],
        min_hourly_rate=f["min_hourly_rate"],
        skills=f["skills"],
        highlights=f.get("highlights", []),
        exclude_keywords=[k.lower() for k in filters.get("exclude_keywords", [])],
        min_client_hires=filters.get("min_client_hires", 0),
        require_payment_verified=filters.get("require_payment_verified", True),
        min_score_to_draft=filters.get("min_score_to_draft", 70),
        search_queries=api.get("search_queries", []),
    )
