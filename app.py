"""
Job Search OS — Streamlit UI

Run with:
    streamlit run app.py
"""

import json
import re
from datetime import date
from pathlib import Path

import streamlit as st

import secret

try:
    import openai
except ImportError:
    st.error("Missing dependency: pip install openai")
    st.stop()

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    st.error("Missing dependencies: pip install requests beautifulsoup4")
    st.stop()


# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT         = Path(__file__).parent
PROFILE_PATH = ROOT / "profile" / "career.md"
RESUMES_DIR  = ROOT / "resumes"
OUTREACH_DIR = ROOT / "outreach"
LOOKUP_PATH  = ROOT / "job_lookup.json"
MODEL        = "gpt-5.4-mini"
WAAS_API_URL = "https://www.workatastartup.com/companies/fetch"


# ── Shared helpers ────────────────────────────────────────────────────────────

def fetch_text(url: str) -> tuple[str, str | None]:
    """Fetch URL and return (text, error). text is empty string on failure."""
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
        return "", str(e)

    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    text = soup.get_text(separator="\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip(), None


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:50].strip("-")


def strip_code_fences(text: str) -> str:
    text = re.sub(r"^```[a-zA-Z]*\n", "", text.strip())
    text = re.sub(r"\n```$", "", text.strip())
    return text.strip()


def split_output(raw: str) -> tuple[str, str]:
    resume_match = re.search(r"#\s*RESUME\s*\n(.*?)(?=#\s*COVER LETTER|$)", raw, re.DOTALL | re.IGNORECASE)
    cover_match  = re.search(r"#\s*COVER LETTER\s*\n(.*?)$",                raw, re.DOTALL | re.IGNORECASE)
    resume = strip_code_fences(resume_match.group(1).strip()) if resume_match else raw.strip()
    cover  = cover_match.group(1).strip() if cover_match else ""
    return resume, cover


def call_openai(job_text: str, context_pages: list[tuple[str, str]], profile: str) -> str:
    today    = date.today().strftime("%B %d, %Y")
    sections = [f"## JOB POSTING\n\n{job_text}"]
    for url, text in context_pages:
        if text:
            sections.append(f"## ADDITIONAL CONTEXT ({url})\n\n{text}")
    user_content = "\n\n---\n\n".join(sections)

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
- Use this exact structure:

    Deepika Nathany
    {today}

    [Hiring Manager name if known, otherwise omit this line]
    [Company Name]

    Dear [Hiring Manager / specific name if known],

    [Paragraph 1 — 4–5 sentences: why this specific role at this specific company, concrete not flattering]

    [Paragraph 2 — 4–5 sentences: 2–3 experiences from the candidate's background that map directly to this role]

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

[letter formatted exactly as described above]"""

    client   = openai.OpenAI(api_key=secret.API_KEY)
    response = client.chat.completions.create(
        model=MODEL,
        service_tier="flex",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user_content},
        ],
    )
    return response.choices[0].message.content


# ── Page config ───────────────────────────────────────────────────────────────

st.set_page_config(page_title="Job Search OS", page_icon="💼", layout="wide")
st.title("💼 Job Search OS")

tab_gen, tab_lookup, tab_update = st.tabs([
    "Generate Application",
    "Look Up Job",
    "Update Lookup Table",
])


# ── Tab 1: Generate Application ───────────────────────────────────────────────

with tab_gen:
    if not PROFILE_PATH.exists():
        st.error(f"Career profile not found at `{PROFILE_PATH}`. Fill in `profile/career.md` first.")
        st.stop()

    st.subheader("Job listing")
    input_method = st.radio("Input method", ["URL", "Paste text"], horizontal=True, label_visibility="collapsed")

    job_text_input = ""
    job_url_input  = ""

    if input_method == "URL":
        job_url_input = st.text_input("Job listing URL", placeholder="https://www.workatastartup.com/jobs/...")
    else:
        job_text_input = st.text_area("Paste job description", height=250, placeholder="Paste the full job description here...")

    st.subheader("Context URLs")
    st.caption("Company page, team page, interviewer profile, press coverage — one per line. Optional.")
    context_urls_raw = st.text_area("Context URLs", height=100, label_visibility="collapsed",
                                     placeholder="https://company.com/about\nhttps://company.com/team")

    st.subheader("Output")
    col1, col2 = st.columns(2)
    with col1:
        company_input = st.text_input("Company name", placeholder="Acme Corp")
    with col2:
        role_input = st.text_input("Role title", placeholder="Senior Product Manager")

    generate_clicked = st.button("Generate", type="primary", use_container_width=True)

    if generate_clicked:
        # ── Validate ──
        if input_method == "URL" and not job_url_input.strip():
            st.error("Enter a job listing URL.")
            st.stop()
        if input_method == "Paste text" and not job_text_input.strip():
            st.error("Paste the job description.")
            st.stop()
        if not company_input.strip() or not role_input.strip():
            st.error("Enter both a company name and a role title.")
            st.stop()

        # ── Fetch job text ──
        if input_method == "URL":
            with st.spinner("Fetching job listing..."):
                job_text, err = fetch_text(job_url_input.strip())
            if err:
                st.error(f"Could not fetch job listing: {err}")
                st.stop()
        else:
            job_text = job_text_input.strip()

        # ── Fetch context pages ──
        context_pages = []
        context_urls  = [u.strip() for u in context_urls_raw.splitlines() if u.strip()]
        if context_urls:
            with st.spinner(f"Fetching {len(context_urls)} context page(s)..."):
                for url in context_urls:
                    text, err = fetch_text(url)
                    if text:
                        context_pages.append((url, text))
                    else:
                        st.warning(f"Could not fetch: {url}")

        # ── Call OpenAI ──
        profile = PROFILE_PATH.read_text(encoding="utf-8")
        with st.spinner("Generating resume and cover letter… (flex tier — may take a moment)"):
            try:
                raw = call_openai(job_text, context_pages, profile)
            except Exception as e:
                st.error(f"OpenAI error: {e}")
                st.stop()

        resume, cover = split_output(raw)

        # ── Save to disk ──
        RESUMES_DIR.mkdir(exist_ok=True)
        OUTREACH_DIR.mkdir(exist_ok=True)
        company_slug = slugify(company_input)
        role_slug    = slugify(role_input)
        resume_path  = RESUMES_DIR  / f"{company_slug}-{role_slug}.tex"
        cover_path   = OUTREACH_DIR / f"{company_slug}-cover-letter.md"
        resume_path.write_text(resume, encoding="utf-8")
        cover_path.write_text(cover,  encoding="utf-8")

        # ── Store in session state ──
        st.session_state["resume"]       = resume
        st.session_state["cover"]        = cover
        st.session_state["resume_fname"] = resume_path.name
        st.session_state["cover_fname"]  = cover_path.name

    # ── Results ──
    if "resume" in st.session_state:
        st.divider()
        res_col, cov_col = st.columns(2)

        with res_col:
            st.subheader("Resume (LaTeX)")
            st.code(st.session_state["resume"], language="latex")
            st.download_button(
                "⬇ Download .tex",
                data=st.session_state["resume"],
                file_name=st.session_state["resume_fname"],
                mime="text/plain",
                use_container_width=True,
            )

        with cov_col:
            st.subheader("Cover Letter")
            st.text(st.session_state["cover"])
            st.download_button(
                "⬇ Download .md",
                data=st.session_state["cover"],
                file_name=st.session_state["cover_fname"],
                mime="text/plain",
                use_container_width=True,
            )


# ── Tab 2: Look Up Job ────────────────────────────────────────────────────────

with tab_lookup:
    st.subheader("Look up a workatastartup.com job")
    st.caption("Requires job_lookup.json — run **Update Lookup Table** first if you haven't.")

    lookup_url = st.text_input("Job URL", placeholder="https://www.workatastartup.com/jobs/89758",
                               key="lookup_url")
    lookup_clicked = st.button("Look up", type="primary")

    if lookup_clicked:
        if not lookup_url.strip():
            st.error("Enter a job URL.")
        else:
            match = re.search(r"/jobs/(\d+)", lookup_url)
            if not match:
                st.error("Could not parse a job ID from that URL.")
            elif not LOOKUP_PATH.exists():
                st.error("`job_lookup.json` not found — run **Update Lookup Table** first.")
            else:
                lookup = json.loads(LOOKUP_PATH.read_text(encoding="utf-8"))
                job_id = match.group(1)
                if job_id not in lookup:
                    st.warning(f"Job ID {job_id} not in lookup table. Try refreshing the table.")
                else:
                    job = lookup[job_id]
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Company",  job.get("company_name", "—"))
                    c2.metric("Salary",   job.get("pretty_salary_range") or "—")
                    c3.metric("Location", job.get("pretty_location_or_remote") or "—")

                    if job.get("company_website"):
                        st.markdown(f"**Website:** [{job['company_website']}]({job['company_website']})")

                    st.divider()
                    st.subheader(job.get("title", "Job Description"))
                    st.text(job.get("description", "(no description available)"))


# ── Tab 3: Update Lookup Table ────────────────────────────────────────────────

with tab_update:
    st.subheader("Update job lookup table")
    st.caption(
        "Fetches all current job listings from workatastartup.com and updates `job_lookup.json`. "
        "Requires **WAAS_COOKIE** and **WAAS_CSRF_TOKEN** in `secret.py`. "
        "Refresh these from your browser when the fetch starts failing."
    )

    if st.button("Fetch & update", type="primary"):
        cookie     = getattr(secret, "WAAS_COOKIE",     "")
        csrf_token = getattr(secret, "WAAS_CSRF_TOKEN", "")

        if not cookie:
            st.error(
                "WAAS_COOKIE is not set in secret.py. "
                "Log in to workatastartup.com, open DevTools → Network → any XHR request, "
                "then copy the Cookie and x-csrf-token header values into secret.py."
            )
            st.stop()

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

        with st.spinner("Fetching from workatastartup.com..."):
            try:
                resp = requests.post(WAAS_API_URL, headers=headers, data=payload, timeout=30)
                resp.raise_for_status()
                data = resp.json()
            except requests.RequestException as e:
                code = e.response.status_code if hasattr(e, "response") and e.response else "?"
                if code in (401, 403, 422):
                    st.error(f"Auth error ({code}) — your session cookie has expired. Update WAAS_COOKIE in secret.py.")
                else:
                    st.error(f"Request failed: {e}")
                st.stop()

        # Build entries
        existing = json.loads(LOOKUP_PATH.read_text(encoding="utf-8")) if LOOKUP_PATH.exists() else {}
        fresh    = {}
        for company in data.get("companies", []):
            for job in company.get("jobs", []):
                fresh[str(job["id"])] = {
                    "title":                     job.get("title", ""),
                    "description":               job.get("description", ""),
                    "company_name":              company.get("name", ""),
                    "company_website":           company.get("website_url") or company.get("website") or "",
                    "show_path":                 job.get("show_path", ""),
                    "pretty_salary_range":       job.get("pretty_salary_range", ""),
                    "pretty_location_or_remote": job.get("pretty_location_or_remote", ""),
                    "company_id":                company.get("id"),
                }

        n_new     = sum(1 for k in fresh if k not in existing)
        n_updated = sum(1 for k in fresh if k in existing)
        merged    = {**existing, **fresh}

        LOOKUP_PATH.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")

        st.success(f"Done — {n_new} new jobs added, {n_updated} updated, {len(merged)} total in lookup.")
