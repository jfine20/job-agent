import os
import anthropic
from resume_context import RESUME, PROFILE_SUMMARY

client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-4-6"


def score_job_fit(job_title: str, job_description: str, company: str) -> tuple[float, str]:
    """Score a job listing 0-10 for fit with Sam's profile. Returns (score, summary)."""
    prompt = f"""You are a career advisor helping Samantha Shenker find the right job.

SAMANTHA'S PROFILE:
{PROFILE_SUMMARY}

JOB LISTING:
Title: {job_title}
Company: {company}
Description: {job_description[:3000]}

Score this job's fit for Samantha on a scale of 0-10, where:
- 8-10: Excellent fit, she should definitely apply
- 5-7: Good fit, worth considering
- 3-4: Partial fit, stretch role
- 0-2: Poor fit, not recommended

Respond with ONLY:
SCORE: [number]
SUMMARY: [1-2 sentences explaining why it is or isn't a fit, and what to highlight if she applies]"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()

    score = 5.0
    summary = "No summary available."
    for line in text.splitlines():
        if line.startswith("SCORE:"):
            try:
                score = float(line.replace("SCORE:", "").strip())
            except ValueError:
                pass
        elif line.startswith("SUMMARY:"):
            summary = line.replace("SUMMARY:", "").strip()

    return score, summary


def tailor_application(job_title: str, job_description: str, company: str) -> dict:
    """Generate tailored resume bullets and cover letter for a specific job."""
    prompt = f"""You are a career coach helping Samantha Shenker apply for a job.

SAMANTHA'S RESUME:
{RESUME}

JOB:
Title: {job_title}
Company: {company}
Description: {job_description[:3000]}

Provide:
1. TAILORED_BULLETS: 4-5 resume bullet points that best match this role (rewrite existing bullets to emphasize relevant experience)
2. COVER_LETTER: A concise, professional cover letter (3 paragraphs max) tailored to this specific role and company

Format your response as:
TAILORED_BULLETS:
- [bullet 1]
- [bullet 2]
...

COVER_LETTER:
[cover letter text]"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()

    bullets = ""
    cover_letter = ""
    if "COVER_LETTER:" in text:
        parts = text.split("COVER_LETTER:")
        bullets = parts[0].replace("TAILORED_BULLETS:", "").strip()
        cover_letter = parts[1].strip()
    else:
        bullets = text

    return {"tailored_bullets": bullets, "cover_letter": cover_letter}


def chat(messages: list[dict]) -> str:
    """Conversational agent with Sam's profile as system context."""
    system = f"""You are a dedicated job search assistant helping Samantha Shenker find a job in finance and investor relations.

SAMANTHA'S PROFILE:
{PROFILE_SUMMARY}

FULL RESUME:
{RESUME}

You help Samantha by:
- Answering questions about her job search strategy
- Suggesting which roles to prioritize and why
- Helping her prepare for interviews
- Advising on how to position her experience
- Helping craft emails, LinkedIn messages, and follow-ups
- Reviewing job descriptions she pastes and giving honest fit assessments

Be warm, direct, and encouraging. Give specific, actionable advice."""

    response = client.messages.create(
        model=MODEL,
        max_tokens=800,
        system=system,
        messages=messages,
    )
    return response.content[0].text
