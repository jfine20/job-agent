import asyncio
import hashlib
import re
from typing import List, Dict

import httpx
from bs4 import BeautifulSoup

# --- Keywords used to filter relevant jobs across all sources ---
KEYWORDS = [
    "investor relations", "capital formation", "fundraising", "lp relations",
    "capital markets", "fund operations", "investor services", "client service",
    "business development", "venture capital", "private equity", "real estate",
    "alternatives", "asset management", "wealth management", "family office",
    "climate", "environmental", "esg", "sustainability", "carbon",
]

TITLE_KEYWORDS = [
    "investor relations", "capital formation", "fundraising", "ir associate",
    "ir analyst", "capital markets", "fund operations", "client service",
    "business development", "vc platform", "lp relations", "alternatives",
    "investor services", "portfolio", "stakeholder",
]

SEARCH_QUERIES = [
    "investor relations associate New York",
    "investor relations analyst New York",
    "capital formation associate New York",
    "fundraising associate finance New York",
    "real estate investor relations New York",
    "client service associate finance New York",
    "vc platform associate New York",
    "business development associate private equity New York",
    "fund operations associate New York",
    "capital markets associate New York",
    "climate finance associate New York",
    "ESG associate investor relations New York",
]

# Greenhouse ATS — public JSON API, no auth needed
# Format: (display_name, greenhouse_board_token)
GREENHOUSE_COMPANIES = [
    # Private equity / alternatives
    ("Apollo Global Management", "apollo"),
    ("Carlyle Group", "carlyle"),
    ("Ares Management", "aresmgmt"),
    ("Blue Owl Capital", "blueowl"),
    ("Hamilton Lane", "hamiltonlane"),
    ("Golub Capital", "golubcapital"),
    ("Owl Rock", "owlrock"),
    ("Blackstone", "blackstone"),
    ("iCapital", "icapital"),
    ("Neuberger Berman", "neubergerberman"),
    # Real estate
    ("Greystar", "greystar"),
    ("Nuveen", "nuveen"),
    ("Brookfield Asset Management", "brookfield"),
    ("Hines", "hines"),
    ("RXR Realty", "rxr"),
    # Climate / ESG / Environmental
    ("Generate Capital", "generatecapital"),
    ("Fifth Wall", "fifthwall"),
    ("Aligned Climate Capital", "alignedclimatecapital"),
    ("Prelude Ventures", "preludeventures"),
    ("Breakthrough Energy", "breakthroughenergy"),
    ("ClimateAI", "climateai"),
    ("Climeworks", "climeworks"),
    ("Carbon Direct", "carbondirect"),
    ("Pachama", "pachama"),
    # VC / Growth
    ("General Atlantic", "generalatlantic"),
    ("Tiger Global", "tigerglobal"),
    ("Insight Partners", "insightpartners"),
    ("Summit Partners", "summitpartners"),
    ("Warburg Pincus", "warburgpincus"),
    ("Vista Equity Partners", "vistaequitypartners"),
    # IR-adjacent
    ("iCapital Network", "icapitalnetwork"),
    ("Addepar", "addepar"),
    ("Carta", "carta"),
    ("Broadridge", "broadridge"),
    ("SS&C Technologies", "ssctechnologies"),
    ("Preqin", "preqin"),
    ("PitchBook", "pitchbook"),
]

# Lever ATS — public JSON API, no auth needed
# Format: (display_name, lever_slug)
LEVER_COMPANIES = [
    ("Blackstone", "blackstone"),
    ("KKR", "kkr"),
    ("Two Sigma", "twosigma"),
    ("D.E. Shaw", "deshaw"),
    ("Bridgewater Associates", "bridgewater"),
    ("Point72", "point72"),
    ("Citadel", "citadel"),
    ("Millennium Management", "millennium"),
    ("Coatue Management", "coatue"),
    ("Tiger Management", "tiger"),
    ("Bessemer Venture Partners", "bvp"),
    ("Andreessen Horowitz", "a16z"),
    ("Sequoia Capital", "sequoiacap"),
    ("Accel", "accel"),
    ("Lightspeed", "lightspeedvp"),
    ("Canapi Ventures", "canapi"),
    ("Generate Capital", "generate"),
    ("Energy Impact Partners", "energyimpact"),
    ("Breakthrough Energy Ventures", "bev"),
    ("Lowercarbon Capital", "lowercarbon"),
    ("Climate Fund Managers", "climatefundmanagers"),
    ("BlueTriton Brands", "bluetriton"),
    ("Sustainable Development Capital", "sdcl"),
]


def _make_id(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def _is_relevant(title: str, description: str) -> bool:
    title_lower = title.lower()
    desc_lower = (description or "").lower()[:2000]
    if any(kw in title_lower for kw in TITLE_KEYWORDS):
        return True
    if any(kw in title_lower for kw in KEYWORDS):
        return True
    keyword_hits = sum(1 for kw in KEYWORDS if kw in desc_lower)
    return keyword_hits >= 3


# --- Source 1: Indeed (Playwright) ---
async def scrape_indeed(queries: List[str]) -> List[Dict]:
    from playwright.async_api import async_playwright

    jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        for query in queries:
            try:
                url = f"https://www.indeed.com/jobs?q={query.replace(' ', '+')}&l=New+York%2C+NY&sort=date&fromage=14"
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(2000)
                content = await page.content()
                soup = BeautifulSoup(content, "lxml")

                cards = soup.select("div.job_seen_beacon, div[data-testid='jobsearch-SerpJobCard']")
                if not cards:
                    cards = soup.select("div.tapItem, div.slider_item")

                for card in cards[:15]:
                    title_el = card.select_one("h2.jobTitle span, h2 a span, a[data-jk] span")
                    company_el = card.select_one("span[data-testid='company-name'], span.companyName")
                    location_el = card.select_one("div[data-testid='text-location'], div.companyLocation")
                    link_el = card.select_one("a[id^='job_'], a[data-jk], h2 a")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    location = location_el.get_text(strip=True) if location_el else "New York, NY"
                    href = link_el.get("href", "") if link_el else ""
                    apply_url = f"https://www.indeed.com{href}" if href.startswith("/") else href
                    jk = re.search(r"jk=([a-f0-9]+)", apply_url)
                    job_key = jk.group(1) if jk else _make_id(title + company)

                    if not title or not company:
                        continue
                    if not _is_relevant(title, ""):
                        continue

                    jobs.append({
                        "external_id": f"indeed_{job_key}",
                        "title": title,
                        "company": company,
                        "location": location,
                        "description": f"Found via Indeed search: {query}",
                        "apply_url": apply_url,
                        "source": "indeed",
                    })

                await page.wait_for_timeout(1500)
            except Exception as e:
                print(f"Indeed error for '{query}': {e}")

        await browser.close()

    print(f"Indeed: found {len(jobs)} jobs")
    return jobs


# --- Source 2: Greenhouse public ATS API ---
async def scrape_greenhouse(companies: List[tuple]) -> List[Dict]:
    jobs = []
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        for company_name, token in companies:
            try:
                url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue
                data = resp.json()
                for job in data.get("jobs", []):
                    title = job.get("title", "")
                    location = job.get("location", {}).get("name", "")
                    # Only include NY or remote jobs
                    loc_lower = location.lower()
                    if location and "new york" not in loc_lower and "ny" not in loc_lower and "remote" not in loc_lower:
                        continue
                    description = BeautifulSoup(job.get("content", ""), "lxml").get_text()[:3000]
                    if not _is_relevant(title, description):
                        continue
                    jobs.append({
                        "external_id": f"gh_{job.get('id', _make_id(title + company_name))}",
                        "title": title,
                        "company": company_name,
                        "location": location or "New York, NY",
                        "description": description,
                        "apply_url": job.get("absolute_url", ""),
                        "source": "greenhouse",
                    })
                await asyncio.sleep(0.3)
            except Exception as e:
                print(f"Greenhouse error for {company_name}: {e}")

    print(f"Greenhouse: found {len(jobs)} relevant jobs")
    return jobs


# --- Source 3: Lever public ATS API ---
async def scrape_lever(companies: List[tuple]) -> List[Dict]:
    jobs = []
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        for company_name, slug in companies:
            try:
                url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
                resp = await client.get(url)
                if resp.status_code != 200:
                    continue
                postings = resp.json()
                for job in postings:
                    title = job.get("text", "")
                    location = job.get("categories", {}).get("location", "")
                    loc_lower = location.lower()
                    if location and "new york" not in loc_lower and "ny" not in loc_lower and "remote" not in loc_lower:
                        continue
                    description = BeautifulSoup(
                        job.get("descriptionPlain", "") or job.get("description", ""), "lxml"
                    ).get_text()[:3000]
                    if not _is_relevant(title, description):
                        continue
                    jobs.append({
                        "external_id": f"lever_{job.get('id', _make_id(title + company_name))}",
                        "title": title,
                        "company": company_name,
                        "location": location or "New York, NY",
                        "description": description,
                        "apply_url": job.get("hostedUrl", ""),
                        "source": "lever",
                    })
                await asyncio.sleep(0.3)
            except Exception as e:
                print(f"Lever error for {company_name}: {e}")

    print(f"Lever: found {len(jobs)} relevant jobs")
    return jobs


async def scrape_all_jobs() -> List[Dict]:
    greenhouse_task = scrape_greenhouse(GREENHOUSE_COMPANIES)
    lever_task = scrape_lever(LEVER_COMPANIES)
    indeed_task = scrape_indeed(SEARCH_QUERIES[:6])  # first 6 queries for speed

    greenhouse_jobs, lever_jobs, indeed_jobs = await asyncio.gather(
        greenhouse_task, lever_task, indeed_task
    )

    all_jobs = greenhouse_jobs + lever_jobs + indeed_jobs

    # Deduplicate by external_id
    seen = set()
    unique = []
    for job in all_jobs:
        if job["external_id"] not in seen:
            seen.add(job["external_id"])
            unique.append(job)

    print(f"Total unique jobs scraped: {len(unique)}")
    return unique
