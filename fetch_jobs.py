#!/usr/bin/env python3
"""
Fetch the latest matched jobs from workatastartup.com and update matched.json.

- Adds new jobs (enriched with company name).
- Never re-adds jobs you've already applied to (tracked in applied_ids.json).
- Never duplicates jobs already in matched.json.
- Saves the raw API response to jobs.json as a cache.

Credentials expire with your browser session. When fetch starts failing:
  1. Log in to workatastartup.com in Chrome
  2. Open DevTools → Network → any XHR request → copy Cookie and x-csrf-token headers
  3. Update WAAS_COOKIE and WAAS_CSRF_TOKEN in secret.py

Requires:
    pip install requests
    secret.py with WAAS_COOKIE and WAAS_CSRF_TOKEN set
"""

import json
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests")

import secret

ROOT         = Path(__file__).parent
MATCHED_PATH = ROOT / "matched.json"
APPLIED_PATH = ROOT / "applied_ids.json"
JOBS_PATH    = ROOT / "jobs.json"

API_URL = "https://www.workatastartup.com/companies/fetch"


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_json(path: Path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── API call ──────────────────────────────────────────────────────────────────

def fetch_raw() -> dict:
    """Call the WaaS companies API and return the parsed response."""
    cookie     = getattr(secret, "WAAS_COOKIE",     "")
    csrf_token = getattr(secret, "WAAS_CSRF_TOKEN", "")

    if not cookie:
        sys.exit(
            "WAAS_COOKIE is not set in secret.py.\n"
            "See the docstring at the top of this file for instructions."
        )

    headers = {
        "accept":           "application/json",
        "content-type":     "application/json",
        "origin":           "https://www.workatastartup.com",
        "referer":          "https://www.workatastartup.com/companies",
        "user-agent":       "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36",
        "x-csrf-token":     csrf_token,
        "x-requested-with": "XMLHttpRequest",
        "Cookie":           cookie,
    }
    payload = json.dumps({"ids": list(range(1_000_000))})

    print("Fetching from workatastartup.com...")
    try:
        resp = requests.post(API_URL, headers=headers, data=payload, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as e:
        if hasattr(e, "response") and e.response is not None and e.response.status_code in (401, 403, 422):
            sys.exit(
                f"Auth error ({e.response.status_code}) — your session cookie has expired.\n"
                "Refresh WAAS_COOKIE and WAAS_CSRF_TOKEN in secret.py and try again."
            )
        sys.exit(f"Request failed: {e}")

    return resp.json()


# ── Processing ────────────────────────────────────────────────────────────────

def process(data: dict, applied_ids: set, existing_ids: set) -> tuple[list, int, int, int]:
    """
    Extract and enrich matched jobs from the API response.

    Returns:
        (new_jobs, n_new, n_skipped_applied, n_skipped_existing)
    """
    # Build company lookup: id → {name, slug, ...}
    companies = {c["id"]: c for c in data.get("companies", [])}

    # Build job lookup: job_id → (job_dict, company_dict)
    all_jobs: dict[int, tuple[dict, dict]] = {}
    for company in data.get("companies", []):
        for job in company.get("jobs", []):
            all_jobs[job["id"]] = (job, company)

    recommended_ids = set(data.get("recommendedJobIds", []))

    new_jobs          = []
    n_skipped_applied  = 0
    n_skipped_existing = 0

    for job_id in recommended_ids:
        if job_id in applied_ids:
            n_skipped_applied += 1
            continue
        if job_id in existing_ids:
            n_skipped_existing += 1
            continue
        if job_id not in all_jobs:
            continue

        job, company = all_jobs[job_id]
        enriched = dict(job)
        enriched["company_name"] = company.get("name", "")
        enriched["company_slug"] = company.get("slug", "")
        new_jobs.append(enriched)

    return new_jobs, len(new_jobs), n_skipped_applied, n_skipped_existing


def backfill_company_names(jobs: list, data: dict) -> list:
    """Add company_name to existing matched jobs that are missing it."""
    companies = {c["id"]: c for c in data.get("companies", [])}
    for job in jobs:
        if not job.get("company_name") and job.get("company_id") in companies:
            c = companies[job["company_id"]]
            job["company_name"] = c.get("name", "")
            job["company_slug"] = c.get("slug", "")
    return jobs


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    applied_ids  = set(load_json(APPLIED_PATH, []))
    existing     = load_json(MATCHED_PATH, [])
    existing_ids = {j["id"] for j in existing}

    data = fetch_raw()

    # Cache the raw response
    save_json(JOBS_PATH, data)
    print(f"Raw response saved to {JOBS_PATH.name}")

    # Backfill company names on existing jobs while we have the data
    existing = backfill_company_names(existing, data)

    new_jobs, n_new, n_applied, n_existing = process(data, applied_ids, existing_ids)

    # Merge: existing (now with backfilled names) + new, minus any applied
    updated = [j for j in existing if j["id"] not in applied_ids] + new_jobs
    save_json(MATCHED_PATH, updated)

    print(f"\nDone.")
    print(f"  New jobs added:          {n_new}")
    print(f"  Already in list:         {n_existing}")
    print(f"  Skipped (already applied): {n_applied}")
    print(f"  Total in matched list:   {len(updated)}")


if __name__ == "__main__":
    main()
