import os
import httpx
import hashlib
from typing import List, Dict
from resume_context import TARGET_ROLES

JSEARCH_KEY = os.getenv("JSEARCH_API_KEY")
JSEARCH_HOST = "jsearch.p.rapidapi.com"


async def fetch_jobs_for_query(query: str, num_pages: int = 2) -> List[Dict]:
    headers = {
        "x-rapidapi-key": JSEARCH_KEY,
        "x-rapidapi-host": JSEARCH_HOST,
    }
    jobs = []
    async with httpx.AsyncClient(timeout=30) as client:
        for page in range(1, num_pages + 1):
            params = {
                "query": f"{query} New York",
                "page": str(page),
                "num_pages": "1",
                "date_posted": "week",
            }
            try:
                resp = await client.get(
                    f"https://{JSEARCH_HOST}/search",
                    headers=headers,
                    params=params,
                )
                resp.raise_for_status()
                data = resp.json()
                jobs.extend(data.get("data", []))
            except Exception as e:
                print(f"JSearch error for '{query}' page {page}: {e}")
    return jobs


def normalize_job(raw: Dict) -> Dict:
    job_id = raw.get("job_id", "")
    external_id = hashlib.md5(job_id.encode()).hexdigest()
    return {
        "external_id": external_id,
        "title": raw.get("job_title", ""),
        "company": raw.get("employer_name", ""),
        "location": raw.get("job_city", "") + ", " + raw.get("job_state", ""),
        "description": (raw.get("job_description") or "")[:4000],
        "apply_url": raw.get("job_apply_link", ""),
        "source": "jsearch",
    }


async def scrape_all_jobs() -> List[Dict]:
    seen_ids = set()
    all_jobs = []

    for role in TARGET_ROLES:
        raw_jobs = await fetch_jobs_for_query(role)
        for raw in raw_jobs:
            normalized = normalize_job(raw)
            if normalized["external_id"] not in seen_ids and normalized["title"]:
                seen_ids.add(normalized["external_id"])
                all_jobs.append(normalized)

    print(f"Scraped {len(all_jobs)} unique jobs")
    return all_jobs
