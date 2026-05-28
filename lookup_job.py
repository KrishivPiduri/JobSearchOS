#!/usr/bin/env python3
"""
Look up a workatastartup.com job URL in the local lookup table.

Usage:
    python lookup_job.py https://www.workatastartup.com/jobs/89758

Prints the job description, company name, and company website.
Run update_lookup.py first to build or refresh the table.
"""

import json
import re
import sys
from pathlib import Path

ROOT        = Path(__file__).parent
LOOKUP_PATH = ROOT / "job_lookup.json"


def extract_job_id(url: str) -> str | None:
    """Pull the numeric job ID out of a workatastartup.com job URL."""
    match = re.search(r"/jobs/(\d+)", url)
    return match.group(1) if match else None


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python lookup_job.py <job_url>")

    url    = sys.argv[1].strip()
    job_id = extract_job_id(url)

    if not job_id:
        sys.exit(f"Could not parse a job ID from: {url}\nExpected format: https://www.workatastartup.com/jobs/<id>")

    if not LOOKUP_PATH.exists():
        sys.exit("job_lookup.json not found — run update_lookup.py first.")

    lookup = json.loads(LOOKUP_PATH.read_text(encoding="utf-8"))

    if job_id not in lookup:
        sys.exit(f"Job ID {job_id} not found in lookup table — run update_lookup.py to refresh.")

    job = lookup[job_id]

    print(f"\nTitle:    {job.get('title', '—')}")
    print(f"Company:  {job.get('company_name', '—')}")
    print(f"Website:  {job.get('company_website', '—')}")
    print(f"Salary:   {job.get('pretty_salary_range') or '—'}")
    print(f"Location: {job.get('pretty_location_or_remote') or '—'}")
    print(f"\n{'─' * 56}\n")
    print(job.get("description", "(no description)"))


if __name__ == "__main__":
    main()
