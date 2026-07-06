import os
import anthropic
from resume_context import RESUME, PROFILE_SUMMARY

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL_SCORE = "claude-haiku-4-5-20251001"   # fast + cheap for batch scoring
MODEL_CHAT  = "claude-sonnet-4-6"            # best for chat + tailoring


SCORE_SYSTEM = f"""You are a career advisor scoring job listings for Samantha Shenker.

{PROFILE_SUMMARY}

Scoring rubric (0-10):
- 9-10: Near-perfect match — associate/coordinator level IR, capital formation, or fund ops role; NYC; 0-3 yrs exp required
- 7-8: Strong match — core IR/fundraising skills needed, company is relevant (PE/VC/real estate/climate), junior-to-mid level
- 5-6: Decent match — overlapping skills but not a perfect title/industry fit, or slightly too senior
- 3-4: Stretch — adjacent role, she could make a case but it's a reach
- 1-2: Poor fit — too senior, wrong function, wrong industry, or requires hard skills she lacks
- 0: No fit — pure tech/engineering/accounting/legal

Seniority levels: entry (0-1yr), associate (1-4yr), manager (4-7yr), vp (7-12yr), director (10+yr), executive (C-suite)
Company types: pe, vc, real_estate, climate, asset_mgmt, wealth, fintech, other"""


def score_job(title: str, description: str, company: str) -> dict:
    """Score a single job. Returns dict with score, seniority, company_type, summary."""
    prompt = f"""Job to evaluate:
Title: {title}
Company: {company}
Description: {description[:4000]}

Respond in EXACTLY this format (no other text):
SCORE: [0-10 number]
SENIORITY: [entry/associate/manager/vp/director/executive]
COMPANY_TYPE: [pe/vc/real_estate/climate/asset_mgmt/wealth/fintech/other]
SUMMARY: [1 sentence: key reason for score + what to highlight if applying]"""

    try:
        resp = client.messages.create(
            model=MODEL_SCORE,
            max_tokens=150,
            system=SCORE_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        result = {"fit_score": 5.0, "seniority": "associate", "company_type": "other", "fit_summary": ""}
        for line in text.splitlines():
            if line.startswith("SCORE:"):
                try:
                    result["fit_score"] = float(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith("SENIORITY:"):
                result["seniority"] = line.split(":", 1)[1].strip().lower()
            elif line.startswith("COMPANY_TYPE:"):
                result["company_type"] = line.split(":", 1)[1].strip().lower()
            elif line.startswith("SUMMARY:"):
                result["fit_summary"] = line.split(":", 1)[1].strip()
        return result
    except Exception as e:
        print(f"Scoring error: {e}")
        return {"fit_score": 5.0, "seniority": "associate", "company_type": "other", "fit_summary": ""}


def tailor_application(title: str, description: str, company: str) -> dict:
    prompt = f"""You are a career coach helping Samantha Shenker apply for a job.

SAMANTHA'S RESUME:
{RESUME}

JOB:
Title: {title}
Company: {company}
Description: {description[:4000]}

Provide:
1. TAILORED_BULLETS: 5 resume bullets that best match this role (rewrite her existing bullets to directly mirror the job's language and priorities)
2. COVER_LETTER: A tight 3-paragraph cover letter (opening hook, why her experience fits, why this company/role specifically)

Format:
TAILORED_BULLETS:
- [bullet]
...

COVER_LETTER:
[letter]"""

    resp = client.messages.create(
        model=MODEL_CHAT, max_tokens=1200,
        messages=[{"role": "user", "content": prompt}],
    )
    text = resp.content[0].text.strip()
    bullets, cover = "", ""
    if "COVER_LETTER:" in text:
        parts = text.split("COVER_LETTER:", 1)
        bullets = parts[0].replace("TAILORED_BULLETS:", "").strip()
        cover = parts[1].strip()
    else:
        bullets = text
    return {"tailored_bullets": bullets, "cover_letter": cover}


def chat(messages: list) -> str:
    system = f"""You are a dedicated job search assistant for Samantha Shenker.

{PROFILE_SUMMARY}

FULL RESUME:
{RESUME}

You help Sam by:
- Answering questions about job search strategy and which roles to prioritize
- Giving honest assessments of job descriptions she pastes
- Helping with interview prep and how to tell her story
- Writing outreach emails, LinkedIn messages, and follow-ups
- Explaining what to highlight for specific types of firms (PE vs VC vs real estate vs climate)

Be direct, warm, and specific. Use her actual numbers ($10M raise, 100+ meetings, 150+ CRM contacts, 25+ data rooms) when relevant."""

    resp = client.messages.create(
        model=MODEL_CHAT, max_tokens=900,
        system=system, messages=messages,
    )
    return resp.content[0].text
