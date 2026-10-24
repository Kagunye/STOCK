"""Job search through Upwork's official GraphQL API.

Requires an approved Upwork API key and an OAuth2 access token for your account
(https://www.upwork.com/developer). Put the token in UPWORK_ACCESS_TOKEN.

The query below follows Upwork's published `marketplaceJobPostingsSearch` schema; if Upwork
changes field names, adjust QUERY and _to_job together.
"""

import os

import requests

from ..models import Job

ENDPOINT = "https://api.upwork.com/graphql"

QUERY = """
query Search($filter: MarketplaceJobPostingsSearchFilter) {
  marketplaceJobPostingsSearch(
    marketPlaceJobFilter: $filter
    searchType: USER_JOBS_SEARCH
    sortAttributes: [{ field: RECENCY }]
  ) {
    edges {
      node {
        id
        ciphertext
        title
        description
        createdDateTime
        amount { rawValue }
        hourlyBudgetMin { rawValue }
        hourlyBudgetMax { rawValue }
        skills { name }
        client {
          totalHires
          verificationStatus
          location { country }
        }
      }
    }
  }
}
"""


class UpworkAPIError(RuntimeError):
    pass


def search(query: str, token: str | None = None, limit: int = 20) -> list[Job]:
    token = token or os.environ.get("UPWORK_ACCESS_TOKEN")
    if not token:
        raise UpworkAPIError("UPWORK_ACCESS_TOKEN is not set; see README for getting Upwork API access")
    resp = requests.post(
        ENDPOINT,
        json={
            "query": QUERY,
            "variables": {"filter": {"searchExpression_eq": query, "pagination_eq": {"after": "0", "first": limit}}},
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if resp.status_code != 200:
        raise UpworkAPIError(f"Upwork API returned {resp.status_code}: {resp.text[:300]}")
    payload = resp.json()
    if payload.get("errors"):
        raise UpworkAPIError(f"Upwork API errors: {payload['errors']}")
    edges = payload["data"]["marketplaceJobPostingsSearch"]["edges"]
    return [_to_job(edge["node"]) for edge in edges]


def _raw(obj) -> float | None:
    if not obj or obj.get("rawValue") in (None, "", "0", 0):
        return None
    return float(obj["rawValue"])


def _to_job(node: dict) -> Job:
    hourly_lo, hourly_hi = _raw(node.get("hourlyBudgetMin")), _raw(node.get("hourlyBudgetMax"))
    fixed = _raw(node.get("amount"))
    if hourly_lo or hourly_hi:
        budget_type, lo, hi = "hourly", hourly_lo, hourly_hi
    elif fixed:
        budget_type, lo, hi = "fixed", fixed, fixed
    else:
        budget_type, lo, hi = "unknown", None, None
    client = node.get("client") or {}
    cipher = node.get("ciphertext") or ""
    return Job(
        id=cipher or str(node["id"]),
        title=node.get("title", ""),
        description=node.get("description", ""),
        url=f"https://www.upwork.com/jobs/{cipher}" if cipher else "",
        budget_type=budget_type,
        budget_min=lo,
        budget_max=hi,
        skills=[s["name"] for s in node.get("skills") or []],
        client_country=(client.get("location") or {}).get("country", ""),
        client_hires=client.get("totalHires"),
        client_payment_verified=(client.get("verificationStatus") == "VERIFIED") if client else None,
        posted_at=node.get("createdDateTime", ""),
        source="upwork_api",
    )
