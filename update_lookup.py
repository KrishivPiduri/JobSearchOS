#!/usr/bin/env python3
"""
Fetch the latest job listings from workatastartup.com and update job_lookup.json.

job_lookup.json maps job ID → {title, description, company_name, company_website, ...}

Existing entries are preserved. New jobs are added. Nothing is ever deleted
(the table is append-only so lookup_job.py keeps working for old listings).

Credentials expire with your browser session. When this script returns a 401/403:
  1. Log in to workatastartup.com in Chrome
  2. Open DevTools → Network tab → click any XHR request
  3. Copy the full Cookie and x-csrf-token header values
  4. Paste them into secret.py as WAAS_COOKIE and WAAS_CSRF_TOKEN

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

ROOT        = Path(__file__).parent
LOOKUP_PATH = ROOT / "job_lookup.json"
API_URL     = "https://www.workatastartup.com/companies/fetch"


def load_lookup() -> dict:
    if LOOKUP_PATH.exists():
        return json.loads(LOOKUP_PATH.read_text(encoding="utf-8"))
    return {}


def save_lookup(data: dict):
    LOOKUP_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_from_api() -> dict:
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


def build_entries(data: dict) -> dict:
    """
    Convert the raw API response into a flat lookup:
        { "job_id": { title, description, company_name, company_website, ... } }
    """
    entries = {}

    for company in data.get("companies", []):
        company_name    = company.get("name", "")
        company_website = company.get("website_url") or company.get("website") or ""

        for job in company.get("jobs", []):
            job_id = str(job["id"])
            entries[job_id] = {
                "title":                    job.get("title", ""),
                "description":              job.get("description", ""),
                "company_name":             company_name,
                "company_website":          company_website,
                "show_path":                job.get("show_path", ""),
                "pretty_salary_range":      job.get("pretty_salary_range", ""),
                "pretty_location_or_remote": job.get("pretty_location_or_remote", ""),
                "company_id":               company.get("id"),
            }

    return entries


def main():
    existing = load_lookup()
    data     = fetch_from_api()
    fresh    = build_entries(data)

    n_new     = sum(1 for k in fresh if k not in existing)
    n_updated = sum(1 for k in fresh if k in existing)

    # Merge: fresh data wins on overlap, existing-only entries are kept
    merged = {**existing, **fresh}
    save_lookup(merged)

    print(f"\nDone.")
    print(f"  New entries added:    {n_new}")
    print(f"  Existing updated:     {n_updated}")
    print(f"  Total in lookup:      {len(merged)}")
    print(f"  Saved to:             {LOOKUP_PATH.name}")


if __name__ == "__main__":
    main()
