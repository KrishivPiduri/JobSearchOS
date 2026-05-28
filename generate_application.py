#!/usr/bin/env python3
"""
Generate a tailored resume and cover letter for a job.

Run with no arguments — walks you through inputs interactively.

For the job listing, either:
  - Paste a URL (script fetches the text)
  - Leave blank and paste the description directly (end with a line containing only ".")

For context URLs (company page, team page, interviewer profile, etc.):
  - Enter one URL per line
  - Leave blank to finish

Outputs:
    resumes/<company>-<role>.md
    outreach/<company>-cover-letter.md

Requires:
    pip install openai requests beautifulsoup4
    secret.py with API_KEY set
"""

import re
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlparse

import secret

try:
    import openai
except ImportError:
    sys.exit("Missing dependency: pip install openai")

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("Missing dependencies: pip install requests beautifulsoup4")


ROOT         = Path(__file__).parent
PROFILE_PATH = ROOT / "profile" / "career.md"
RESUMES_DIR  = ROOT / "resumes"
OUTREACH_DIR = ROOT / "outreach"
MODEL        = "gpt-5.4-mini"


# ── Web fetching ──────────────────────────────────────────────────────────────

def fetch_text(url: str) -> str:
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  Warning: could not fetch {url}: {e}", file=sys.stderr)
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


# ── Utilities ─────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:50].strip("-")


def paste_text(prompt: str) -> str:
    """Read multi-line pasted text. User ends input with a line containing only '.'"""
    print(prompt)
    print("  (paste text, then enter a line with just '.' to finish)")
    lines = []
    while True:
        line = input()
        if line.strip() == ".":
            break
        lines.append(line)
    return "\n".join(lines).strip()


# ── Prompts ───────────────────────────────────────────────────────────────────

def get_job_text() -> str:
    """Ask for a job URL or offer to accept pasted text."""
    val = input("Job listing URL (or press Enter to paste text): ").strip()

    if not val:
        return paste_text("\nPaste the job description:")

    print(f"  Fetching...")
    text = fetch_text(val)
    if not text:
        sys.exit("Could not fetch the URL.")
    return text


def get_context_pages() -> list[tuple[str, str]]:
    """Ask for optional context URLs. Returns list of (url, text)."""
    print("\nContext URLs — company page, team page, interviewer profile, etc.")
    print("Enter one per line. Leave blank to finish:")
    pages = []
    while True:
        url = input("  URL: ").strip()
        if not url:
            break
        print(f"  Fetching...")
        text = fetch_text(url)
        if text:
            pages.append((url, text))
        else:
            print(f"  (skipped — could not fetch)")
    return pages


# ── OpenAI ────────────────────────────────────────────────────────────────────

def call_openai(job_text: str, context_pages: list[tuple[str, str]], profile: str) -> str:
    sections = [f"## JOB POSTING\n\n{job_text}"]
    for url, text in context_pages:
        if text:
            sections.append(f"## ADDITIONAL CONTEXT ({url})\n\n{text}")
    user_content = "\n\n---\n\n".join(sections)

    today = date.today().strftime("%B %d, %Y")

    system = f"""You are a job application strategist helping a specific candidate apply to a specific role.

Your job is to produce two documents grounded entirely in the candidate's real experience:
1. A resume in LaTeX
2. A cover letter formatted as a formal letter

---

## RESUME RULES
- Output valid, compilable LaTeX using the template structure below — no markdown, no code fences
- Open with a 3-line summary written for this specific role and company — not generic
- Include only roles relevant to this position; shrink or omit unrelated ones
- Lead each role with the 2–3 bullets most relevant to the job posting
- Mirror the job posting's language where it accurately describes what the candidate did
- Cap at 4–5 bullets per role
- Quantify wherever the profile supports it
- Do not fabricate, embellish, or add skills the candidate has not demonstrated

Use this LaTeX structure exactly:

\\documentclass[10pt, letterpaper]{{article}}
\\usepackage[top=0.6in, bottom=0.6in, left=0.75in, right=0.75in]{{geometry}}
\\usepackage{{enumitem}}
\\usepackage{{hyperref}}
\\usepackage[T1]{{fontenc}}
\\usepackage[utf8]{{inputenc}}
\\usepackage{{parskip}}
\\usepackage{{titlesec}}
\\titleformat{{\\section}}{{\\large\\bfseries}}{{}}{{0em}}{{}}[\\titlerule]
\\titlespacing{{\\section}}{{0pt}}{{10pt}}{{6pt}}
\\setlist[itemize]{{noitemsep, topsep=2pt, leftmargin=*}}
\\pagestyle{{empty}}
\\begin{{document}}

% Header
\\begin{{center}}
  {{\\LARGE \\textbf{{Deepika Nathany}}}} \\\\[4pt]
  San Francisco, CA \\quad | \\quad
  \\href{{mailto:deepika@example.com}}{{deepika@example.com}} \\quad | \\quad
  \\href{{https://linkedin.com/in/deepikanathany}}{{linkedin.com/in/deepikanathany}}
\\end{{center}}

\\section*{{Summary}}
[3-line summary tailored to this role]

\\section*{{Experience}}

\\textbf{{[Title]}} \\hfill \\textit{{[Date range]}} \\\\
\\textit{{[Company]}}
\\begin{{itemize}}
  \\item [bullet]
\\end{{itemize}}

\\section*{{Education \\& Certifications}}
[education entries]

\\end{{document}}

---

## COVER LETTER RULES
- Format as a formal business letter, not an essay
- Letter structure:
    Deepika Nathany
    {today}

    [Hiring Manager name if known, otherwise leave blank]
    [Company Name]

    Dear [Hiring Manager / specific name if known],

    [Paragraph 1 — 4–5 sentences: why this specific role at this specific company, concrete not flattering]

    [Paragraph 2 — 4–5 sentences: the 2–3 experiences from the candidate's background that map most directly to what this role needs]

    [Paragraph 3 — 3–4 sentences: one sentence on fit, one on what you'd contribute in the first 90 days, a clean close]

    Sincerely,

    Deepika Nathany
- No fluff, no buzzwords, no "I am passionate about"
- Tone: senior, direct, respectful of the reader's time

---

## CANDIDATE PROFILE

{profile}

---

## OUTPUT FORMAT

Return exactly this structure with these exact headers (nothing before the first header):

# RESUME

[full LaTeX source — no code fences, starts with \\documentclass]

# COVER LETTER

[letter text exactly as described above]"""

    client   = openai.OpenAI(api_key=secret.API_KEY)
    response = client.chat.completions.create(
        model=MODEL,
        service_tier="flex",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user_content},
        ],
    )
    usage = response.usage
    print(f"  Tokens — input: {usage.prompt_tokens}, output: {usage.completion_tokens}")
    return response.choices[0].message.content


def strip_code_fences(text: str) -> str:
    """Remove ```latex ... ``` or ``` ... ``` wrappers if the model added them."""
    text = re.sub(r"^```[a-zA-Z]*\n", "", text.strip())
    text = re.sub(r"\n```$", "", text.strip())
    return text.strip()


def split_output(raw: str) -> tuple[str, str]:
    resume_match = re.search(r"#\s*RESUME\s*\n(.*?)(?=#\s*COVER LETTER|$)", raw, re.DOTALL | re.IGNORECASE)
    cover_match  = re.search(r"#\s*COVER LETTER\s*\n(.*?)$",                raw, re.DOTALL | re.IGNORECASE)
    resume = strip_code_fences(resume_match.group(1).strip()) if resume_match else raw.strip()
    cover  = cover_match.group(1).strip() if cover_match else ""
    return resume, cover


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if not PROFILE_PATH.exists():
        sys.exit(f"Career profile not found at {PROFILE_PATH} — fill in profile/career.md first.")

    job_text      = get_job_text()
    context_pages = get_context_pages()

    company = input("\nCompany name (for filename): ").strip() or "company"
    role    = input("Role title   (for filename): ").strip() or "role"

    if not job_text.strip():
        sys.exit("Job description is empty — cannot generate.")

    profile = PROFILE_PATH.read_text(encoding="utf-8")

    print(f"\nCalling OpenAI...", flush=True)
    raw = call_openai(job_text, context_pages, profile)

    resume, cover = split_output(raw)

    RESUMES_DIR.mkdir(exist_ok=True)
    OUTREACH_DIR.mkdir(exist_ok=True)

    company_slug = slugify(company)
    role_slug    = slugify(role)
    resume_path  = RESUMES_DIR  / f"{company_slug}-{role_slug}.tex"
    cover_path   = OUTREACH_DIR / f"{company_slug}-cover-letter.md"

    resume_path.write_text(resume, encoding="utf-8")
    cover_path.write_text(cover,  encoding="utf-8")

    print(f"\nDone.")
    print(f"  Resume:       {resume_path}")
    print(f"  Cover letter: {cover_path}")


if __name__ == "__main__":
    main()
