"""
Multi-source job scraper for Samantha Shenker's job search.
Sources: LinkedIn, eFinancialCareers, Built In NYC, Wellfound, Greenhouse ATS, Lever ATS, Indeed
"""
import asyncio
import hashlib
import re
from typing import List, Dict
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

# ─── Relevance filters ────────────────────────────────────────────────────────

TITLE_KEYWORDS = [
    "investor relations", "capital formation", "fundraising", "ir associate",
    "ir analyst", "capital markets", "fund operations", "client service",
    "business development", "vc platform", "lp relations", "alternatives",
    "investor services", "chief of staff", "executive operations",
    "operations associate", "investment associate", "relationship manager",
    "portfolio associate", "stakeholder relations", "fund associate",
    "investor experience", "shareholder", "fund development",
]

BODY_KEYWORDS = [
    "investor relations", "capital formation", "fundraising", "lp relations",
    "capital markets", "fund operations", "investor services", "client service",
    "venture capital", "private equity", "real estate investment", "alternatives",
    "asset management", "wealth management", "family office", "hedge fund",
    "climate", "esg", "sustainability", "carbon markets", "crm", "due diligence",
    "pitch deck", "data room", "investor outreach", "pipeline management",
    "docsend", "hubspot", "salesforce", "investment management",
]

SEARCH_QUERIES = [
    "investor relations associate",
    "investor relations analyst",
    "capital formation associate",
    "fundraising associate finance",
    "IR associate private equity",
    "client service associate alternatives",
    "fund operations associate",
    "investor relations coordinator",
    "chief of staff venture capital",
    "operations associate private equity",
    "ESG investor relations associate",
    "real estate investor relations associate",
    "LP relations associate",
    "capital markets associate",
    "business development associate private equity",
    "investor experience associate",
]

def _id(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()[:16]

def _is_relevant(title: str, desc: str = "") -> bool:
    t = title.lower()
    d = desc.lower()[:5000]
    if any(k in t for k in TITLE_KEYWORDS):
        return True
    hits = sum(1 for k in BODY_KEYWORDS if k in d)
    return hits >= 2

def _is_nyc_or_remote(location: str) -> bool:
    """Return True only for NYC or genuinely remote US roles."""
    if not location:
        return True  # we default blank locations to NYC
    loc = location.lower()
    if "new york" in loc or "nyc" in loc:
        return True
    if "remote" in loc:
        # reject Canada and non-NY region-specific remotes
        if "canada" in loc:
            return False
        if any(x in loc for x in ["southeast", "midwest", "west coast", "southwest", "national only"]):
            return False
        return True
    return False


def _normalize(raw: Dict) -> Dict:
    raw.setdefault("salary_range", None)
    raw.setdefault("company_type", None)
    return raw


# ─── Source 1: Greenhouse public ATS API ─────────────────────────────────────

GREENHOUSE_COMPANIES = [
    # PE / Private Credit / Alternatives
    ("Apollo Global Management", "apollo"),
    ("Ares Management", "aresmgmt"),
    ("Blue Owl Capital", "blueowl"),
    ("Hamilton Lane", "hamiltonlane"),
    ("Golub Capital", "golubcapital"),
    ("Blackstone", "blackstone"),
    ("iCapital", "icapital"),
    ("iCapital Network", "icapitalnetwork"),
    ("Neuberger Berman", "neubergerberman"),
    ("CAIS", "cais"),
    ("Benefit Street Partners", "benefitstreetpartners"),
    ("General Atlantic", "generalatlantic"),
    ("Summit Partners", "summitpartners"),
    ("Warburg Pincus", "warburgpincus"),
    ("Insight Partners", "insightpartners"),
    ("Vista Equity Partners", "vistaequitypartners"),
    ("Advent International", "advent"),
    ("Bain Capital", "baincapital"),
    ("Veritas Capital", "veritascapital"),
    ("Stone Point Capital", "stonepoint"),
    ("GTCR", "gtcr"),
    ("TA Associates", "ta"),
    ("Francisco Partners", "franciscopartners"),
    ("Leonard Green Partners", "lgp"),
    ("Antares Capital", "antarescapital"),
    ("Owl Rock Capital", "owlrock"),
    ("Monroe Capital", "monroecapital"),
    ("WhiteHorse Capital", "whitehorsecapital"),
    ("Twin Brook Capital", "twinbrook"),
    # Real Estate
    ("Greystar", "greystar"),
    ("Hines", "hines"),
    ("RXR Realty", "rxr"),
    ("Brookfield Asset Management", "brookfield"),
    ("Tishman Speyer", "tishmanspey"),
    ("JLL", "jll"),
    ("CBRE", "cbre"),
    ("Cushman & Wakefield", "cushwake"),
    ("Compass", "compass"),
    ("Oxford Properties", "oxford"),
    ("Nuveen Real Estate", "nuveen"),
    ("MetLife Investment Management", "metlife"),
    ("Rockpoint Group", "rockpoint"),
    ("BentallGreenOak", "bentallgreenoak"),
    # Climate / ESG / Environmental
    ("Generate Capital", "generatecapital"),
    ("Fifth Wall", "fifthwall"),
    ("Breakthrough Energy", "breakthroughenergy"),
    ("ClimateAI", "climateai"),
    ("Carbon Direct", "carbondirect"),
    ("Pachama", "pachama"),
    ("Intersect Power", "intersectpower"),
    ("Arcadia", "arcadia"),
    ("Invenergy", "invenergy"),
    ("Nexamp", "nexamp"),
    ("Sunrun", "sunrun"),
    ("CleanCapital", "cleancapital"),
    ("Greenbacker Capital", "greenbackercapital"),
    ("Hannon Armstrong", "hannonarmstrong"),
    ("Energize Capital", "energizecapital"),
    ("Generate Capital", "generate"),
    # Alt Investment Platforms / IR Tech
    ("Addepar", "addepar"),
    ("Carta", "carta"),
    ("Broadridge", "broadridge"),
    ("Preqin", "preqin"),
    ("PitchBook", "pitchbook"),
    ("Yieldstreet", "yieldstreet"),
    ("Republic", "republic"),
    ("Fundrise", "fundrise"),
    ("Percent", "percent"),
    ("MSCI", "msci"),
    ("FactSet", "factset"),
    ("Donnelley Financial Solutions", "dfsco"),
    ("Ipreo", "ipreo"),
    # Asset Management
    ("PGIM", "pgim"),
    ("Lord Abbett", "lordabbett"),
    ("Pimco", "pimco"),
    ("BlackRock", "blackrock"),
    ("AllianceBernstein", "alliancebernstein"),
    ("Voya Financial", "voya"),
    ("Franklin Templeton", "franklintempleton"),
    ("Lazard Asset Management", "lazard"),
    ("Silvercrest Asset Management", "silvercrest"),
    ("Manning & Napier", "manningnapier"),
    # Wealth / Family Office
    ("Rockefeller Capital Management", "rockefellercapital"),
    ("Glenmede", "glenmede"),
    ("Fiduciary Trust", "fiduciarytrust"),
    ("Bernstein Private Wealth", "bernstein"),
    ("Silvercrest", "silvercrest"),
]

# ─── Source: Workday public API ───────────────────────────────────────────────
# Many major financial firms use Workday. Their job search API is public.
# Format: (display_name, workday_tenant, site_id)

WORKDAY_COMPANIES = [
    ("Blackstone",           "blackstone",     "Blackstone_Careers"),
    ("KKR",                  "kkr",            "KKR_Careers"),
    ("Carlyle Group",        "carlyle",        "External"),
    ("Apollo Global",        "apollo",         "External"),
    ("JPMorgan",             "jpmc",           "External"),
    ("Goldman Sachs",        "goldmansachs",   "External_Career_Site"),
    ("Morgan Stanley",       "morganstanley",  "External"),
    ("Lazard",               "lazard",         "External"),
    ("Brookfield",           "brookfield",     "External"),
    ("Vornado Realty",       "vno",            "External"),
    ("Boston Properties",    "bxp",            "External"),
    ("CBRE",                 "cbre",           "External"),
    ("JLL",                  "jll",            "jllcareers"),
    ("Northern Trust",       "northerntrust",  "External"),
    ("Franklin Templeton",   "franklintempleton", "External"),
    ("AllianceBernstein",    "alliancebernstein", "External"),
    ("Nuveen",               "nuveen",         "External"),
    ("Pimco",                "pimco",          "External"),
    ("PGIM",                 "pgim",           "External"),
    ("Voya Financial",       "voya",           "External"),
    ("Hines",                "hines",          "External"),
    ("Greystar",             "greystar",       "External"),
    ("Cushman & Wakefield",  "cushwake",       "External"),
]

WORKDAY_SEARCH_TERMS = [
    "investor relations", "capital formation", "fundraising",
    "fund operations", "capital markets", "client service",
    "business development", "investment associate",
]

async def scrape_workday() -> List[Dict]:
    jobs = []
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "X-Workday-Client": "2022.35.6",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    }
    async with httpx.AsyncClient(timeout=15, follow_redirects=True, headers=headers) as client:
        for company, tenant, site in WORKDAY_COMPANIES:
            for term in WORKDAY_SEARCH_TERMS[:4]:
                try:
                    url = f"https://{tenant}.wd5.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
                    payload = {"limit": 20, "offset": 0, "searchText": term}
                    r = await client.post(url, json=payload)
                    if r.status_code != 200:
                        # Try alternate URL pattern
                        url2 = f"https://{tenant}.wd1.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"
                        r = await client.post(url2, json=payload)
                        if r.status_code != 200:
                            continue
                    data = r.json()
                    for posting in data.get("jobPostings", []):
                        title = posting.get("title", "")
                        location_nodes = posting.get("locationsText", "") or ""
                        external_path = posting.get("externalPath", "")
                        apply_url = f"https://{tenant}.wd5.myworkdayjobs.com{external_path}" if external_path else ""

                        if not _is_nyc_or_remote(location_nodes):
                            continue
                        if not _is_relevant(title):
                            continue

                        jobs.append(_normalize({
                            "external_id": f"wd_{_id(title + company + external_path)}",
                            "title": title, "company": company,
                            "location": location_nodes or "New York, NY",
                            "description": f"Workday: {title} at {company}. Search: '{term}'.",
                            "apply_url": apply_url,
                            "source": "workday",
                        }))
                    await asyncio.sleep(0.3)
                except Exception:
                    pass

    # Deduplicate within workday results
    seen: set = set()
    unique = [j for j in jobs if not (j["external_id"] in seen or seen.add(j["external_id"]))]
    print(f"Workday: {len(unique)} relevant jobs")
    return unique


async def scrape_greenhouse(companies: List[tuple]) -> List[Dict]:
    jobs = []
    async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
        for name, token in companies:
            try:
                r = await client.get(
                    f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
                )
                if r.status_code != 200:
                    continue
                for job in r.json().get("jobs", []):
                    title = job.get("title", "")
                    location = job.get("location", {}).get("name", "")
                    if not _is_nyc_or_remote(location):
                        continue
                    desc = BeautifulSoup(job.get("content", ""), "lxml").get_text()[:5000]
                    if not _is_relevant(title, desc):
                        continue
                    jobs.append(_normalize({
                        "external_id": f"gh_{job.get('id', _id(title+name))}",
                        "title": title, "company": name,
                        "location": location or "New York, NY",
                        "description": desc,
                        "apply_url": job.get("absolute_url", ""),
                        "source": "greenhouse",
                    }))
                await asyncio.sleep(0.15)
            except Exception:
                pass
    print(f"Greenhouse: {len(jobs)} relevant jobs")
    return jobs


# ─── Source 2: Lever public ATS API ──────────────────────────────────────────

LEVER_COMPANIES = [
    ("KKR", "kkr"),
    ("Carlyle Group", "carlyle"),
    ("Bridgewater Associates", "bridgewaterassociates"),
    ("Point72", "point72"),
    ("Citadel", "citadel"),
    ("Millennium Management", "millennium"),
    ("Coatue Management", "coatue"),
    ("Two Sigma", "twosigma"),
    ("D.E. Shaw", "deshaw"),
    ("Sculptor Capital", "sculptor"),
    ("Silver Lake", "silverlake"),
    ("Thoma Bravo", "thomabravo"),
    ("Bessemer Venture Partners", "bvp"),
    ("Andreessen Horowitz", "a16z"),
    ("Accel", "accel"),
    ("Lightspeed", "lightspeedvp"),
    ("Tiger Global", "tigerglobal"),
    ("General Catalyst", "generalcatalyst"),
    ("Canapi Ventures", "canapi"),
    ("Energy Impact Partners", "energyimpact"),
    ("Lowercarbon Capital", "lowercarbon"),
    ("Galvanize Climate Solutions", "galvanizeclimate"),
    ("Congruent Ventures", "congruent"),
    ("Prelude Ventures", "preludeventures"),
    ("DBL Partners", "dbl"),
    ("Related Companies", "related"),
    ("Slate Property Group", "slate"),
    ("Mack Real Estate", "mackrealestate"),
    ("Brookfield Properties", "brookfieldproperties"),
    ("Envestnet", "envestnet"),
    ("Morningstar", "morningstar"),
    ("Orion Advisor Solutions", "orionadvisor"),
]

async def scrape_lever(companies: List[tuple]) -> List[Dict]:
    jobs = []
    async with httpx.AsyncClient(timeout=12, follow_redirects=True) as client:
        for name, slug in companies:
            try:
                r = await client.get(f"https://api.lever.co/v0/postings/{slug}?mode=json")
                if r.status_code != 200:
                    continue
                for job in r.json():
                    title = job.get("text", "")
                    location = job.get("categories", {}).get("location", "")
                    if not _is_nyc_or_remote(location):
                        continue
                    desc = BeautifulSoup(
                        job.get("descriptionPlain") or job.get("description", ""), "lxml"
                    ).get_text()[:5000]
                    if not _is_relevant(title, desc):
                        continue
                    jobs.append(_normalize({
                        "external_id": f"lever_{job.get('id', _id(title+name))}",
                        "title": title, "company": name,
                        "location": location or "New York, NY",
                        "description": desc,
                        "apply_url": job.get("hostedUrl", ""),
                        "source": "lever",
                    }))
                await asyncio.sleep(0.15)
            except Exception:
                pass
    print(f"Lever: {len(jobs)} relevant jobs")
    return jobs


# ─── Sources 3-7: Playwright (LinkedIn, eFC, Wellfound, Built In, Indeed) ─────

async def scrape_playwright_sources(queries: List[str]) -> List[Dict]:
    from playwright.async_api import async_playwright
    jobs = []

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={"width": 1440, "height": 900},
            locale="en-US",
            timezone_id="America/New_York",
        )
        await ctx.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            window.chrome = { runtime: {} };
        """)

        jobs += await _linkedin(ctx, queries[:8])
        jobs += await _google_jobs(ctx, queries[:10])
        jobs += await _efinancialcareers(ctx, queries[:5])
        jobs += await _wellfound(ctx, queries[:4])
        jobs += await _builtin(ctx, queries[:3])
        jobs += await _indeed(ctx, queries[:6])
        jobs += await _direct_company_pages(ctx)

        await browser.close()

    print(f"Playwright total: {len(jobs)} jobs")
    return jobs


async def _google_jobs(ctx, queries: List[str]) -> List[Dict]:
    """Scrape Google Jobs widget — aggregates postings from company career pages."""
    jobs = []
    page = await ctx.new_page()
    try:
        for query in queries:
            try:
                # Google Jobs widget URL
                url = (
                    f"https://www.google.com/search"
                    f"?q={quote_plus(query + ' New York NY')}"
                    f"&ibp=htl;jobs&hl=en&gl=us"
                )
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(3000)

                # Click "More jobs" if present to expand
                try:
                    more = await page.query_selector("g-scrolling-carousel button, [jsname='N9Xkfe'], [data-ved] span:has-text('More jobs')")
                    if more:
                        await more.click()
                        await page.wait_for_timeout(1500)
                except Exception:
                    pass

                soup = BeautifulSoup(await page.content(), "lxml")

                # Google Jobs cards appear in li[class*="iFjolb"], div[class*="PwjeAc"], etc.
                cards = (
                    soup.select("li.iFjolb") or
                    soup.select("div.PwjeAc") or
                    soup.select("[data-jlid]") or
                    soup.select("div.BjJfJf")
                )

                for card in cards[:20]:
                    title_el = card.select_one("div.BjJfJf, div[class*='title'], h3, .jO4UFC")
                    company_el = card.select_one("div.vNEEBe, div[class*='company'], .nJlQNd")
                    location_el = card.select_one("div.Qk80Jf, div[class*='location'], .ubEfBe")
                    link_el = card.select_one("a[href]")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    location = location_el.get_text(strip=True) if location_el else "New York, NY"
                    href = (link_el.get("href") or "") if link_el else ""

                    if not title or not _is_relevant(title):
                        continue
                    if not _is_nyc_or_remote(location):
                        continue

                    jobs.append(_normalize({
                        "external_id": f"gjobs_{_id(title+company+query)}",
                        "title": title, "company": company, "location": location,
                        "description": f"Google Jobs: {title} at {company}. Found via: '{query}'.",
                        "apply_url": href, "source": "google_jobs",
                    }))

                await page.wait_for_timeout(2000)
            except Exception as e:
                print(f"Google Jobs '{query}': {e}")
    finally:
        await page.close()
    print(f"Google Jobs: {len(jobs)} jobs")
    return jobs


async def _linkedin(ctx, queries: List[str]) -> List[Dict]:
    jobs = []
    page = await ctx.new_page()
    try:
        for query in queries:
            try:
                # f_TPR=r1209600 = last 2 weeks; sortBy=DD = date descending
                url = (
                    f"https://www.linkedin.com/jobs/search/"
                    f"?keywords={quote_plus(query)}"
                    f"&location=New+York%2C+New+York%2C+United+States"
                    f"&f_TPR=r1209600&sortBy=DD"
                )
                await page.goto(url, wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_timeout(3000)

                if "authwall" in page.url or "checkpoint" in page.url:
                    print(f"LinkedIn: auth wall hit, skipping")
                    break

                # Scroll to load more cards
                for _ in range(5):
                    await page.evaluate("window.scrollBy(0, 600)")
                    await page.wait_for_timeout(600)

                soup = BeautifulSoup(await page.content(), "lxml")
                cards = soup.select("div.base-card, li.result-card, div[data-entity-urn]")

                for card in cards[:25]:
                    title_el = card.select_one("h3.base-search-card__title, h3[class*='title'], span[class*='title']")
                    company_el = card.select_one("h4.base-search-card__subtitle, a[class*='company'], span[class*='company']")
                    location_el = card.select_one("span.job-search-card__location, span[class*='location']")
                    link_el = card.select_one("a.base-card__full-link, a[href*='/jobs/view/']")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    location = location_el.get_text(strip=True) if location_el else "New York, NY"
                    href = (link_el.get("href") or "").split("?")[0] if link_el else ""

                    if not title or not company or not _is_relevant(title):
                        continue

                    jobs.append(_normalize({
                        "external_id": f"li_{_id(title+company+href[:30])}",
                        "title": title, "company": company, "location": location,
                        "description": f"LinkedIn: {title} at {company}. Found via: '{query}'.",
                        "apply_url": href, "source": "linkedin",
                    }))

                await page.wait_for_timeout(2000)
            except Exception as e:
                print(f"LinkedIn '{query}': {e}")
    finally:
        await page.close()
    print(f"LinkedIn: {len(jobs)} jobs")
    return jobs


async def _efinancialcareers(ctx, queries: List[str]) -> List[Dict]:
    jobs = []
    page = await ctx.new_page()
    try:
        for query in queries:
            try:
                url = f"https://www.efinancialcareers.com/search?q={quote_plus(query)}&location=New+York&radius=25"
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(3000)

                soup = BeautifulSoup(await page.content(), "lxml")

                # Try multiple card selectors
                cards = (
                    soup.select("article[data-job-id]") or
                    soup.select("[class*='JobCard']") or
                    soup.select("div[class*='job-card']") or
                    soup.select("li[class*='job-item']")
                )

                for card in cards[:25]:
                    title_el = (
                        card.select_one("[class*='job-title'], [class*='jobTitle'], h2 a, h3 a") or
                        card.select_one("h2, h3")
                    )
                    company_el = card.select_one("[class*='company'], [class*='employer'], [class*='Company']")
                    location_el = card.select_one("[class*='location'], [class*='Location']")
                    link_el = card.select_one("a[href*='/jobs/'], a[href*='/job/']") or card.select_one("a")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    location = location_el.get_text(strip=True) if location_el else "New York, NY"
                    href = (link_el.get("href") or "") if link_el else ""
                    apply_url = f"https://www.efinancialcareers.com{href}" if href.startswith("/") else href

                    if not title or len(title) < 4 or not _is_relevant(title):
                        continue

                    jobs.append(_normalize({
                        "external_id": f"efc_{_id(title+company)}",
                        "title": title, "company": company, "location": location,
                        "description": f"eFinancialCareers: {title} at {company}. Search: '{query}'.",
                        "apply_url": apply_url, "source": "efinancialcareers",
                    }))

                await page.wait_for_timeout(1500)
            except Exception as e:
                print(f"eFC '{query}': {e}")
    finally:
        await page.close()
    print(f"eFinancialCareers: {len(jobs)} jobs")
    return jobs


async def _wellfound(ctx, queries: List[str]) -> List[Dict]:
    jobs = []
    page = await ctx.new_page()
    try:
        for query in queries[:4]:
            try:
                url = f"https://wellfound.com/jobs?q={quote_plus(query)}&l=New+York+City"
                await page.goto(url, wait_until="networkidle", timeout=25000)
                await page.wait_for_timeout(3500)

                soup = BeautifulSoup(await page.content(), "lxml")

                for card in soup.select("[data-test='JobListing'], [class*='JobListing'], [class*='job-listing']")[:20]:
                    title_el = card.select_one("h2, h3, [class*='title'], [class*='Title']")
                    company_el = card.select_one("[class*='company'], [class*='Company'], [class*='startup']")
                    link_el = card.select_one("a[href*='/jobs/']") or card.select_one("a")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    href = (link_el.get("href") or "") if link_el else ""
                    apply_url = f"https://wellfound.com{href}" if href.startswith("/") else href

                    if not title or not _is_relevant(title):
                        continue

                    jobs.append(_normalize({
                        "external_id": f"wf_{_id(title+company)}",
                        "title": title, "company": company, "location": "New York, NY",
                        "description": f"Wellfound: {title} at {company}. Search: '{query}'.",
                        "apply_url": apply_url, "source": "wellfound",
                    }))

                await page.wait_for_timeout(2000)
            except Exception as e:
                print(f"Wellfound '{query}': {e}")
    finally:
        await page.close()
    print(f"Wellfound: {len(jobs)} jobs")
    return jobs


async def _builtin(ctx, queries: List[str]) -> List[Dict]:
    jobs = []
    page = await ctx.new_page()
    try:
        for query in queries[:3]:
            try:
                url = f"https://builtin.com/jobs/nyc?search={quote_plus(query)}"
                await page.goto(url, wait_until="networkidle", timeout=25000)
                await page.wait_for_timeout(3000)

                soup = BeautifulSoup(await page.content(), "lxml")

                for card in soup.select("article, [data-id], [class*='JobCard'], [class*='job-card']")[:20]:
                    title_el = card.select_one("h2, h3, [class*='title'], [class*='Title']")
                    company_el = card.select_one("[class*='company'], [class*='Company']")
                    link_el = card.select_one("a[href*='/job/'], a[href]")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    href = (link_el.get("href") or "") if link_el else ""
                    apply_url = f"https://builtin.com{href}" if href.startswith("/") else href

                    if not title or not _is_relevant(title):
                        continue

                    jobs.append(_normalize({
                        "external_id": f"bi_{_id(title+company)}",
                        "title": title, "company": company, "location": "New York, NY",
                        "description": f"Built In NYC: {title} at {company}.",
                        "apply_url": apply_url, "source": "builtin",
                    }))

                await page.wait_for_timeout(2000)
            except Exception as e:
                print(f"Built In '{query}': {e}")
    finally:
        await page.close()
    print(f"Built In NYC: {len(jobs)} jobs")
    return jobs


async def _indeed(ctx, queries: List[str]) -> List[Dict]:
    jobs = []
    page = await ctx.new_page()
    try:
        for query in queries:
            try:
                url = f"https://www.indeed.com/jobs?q={quote_plus(query)}&l=New+York%2C+NY&sort=date&fromage=14"
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_timeout(2500)

                soup = BeautifulSoup(await page.content(), "lxml")

                for card in soup.select("div.job_seen_beacon, div.tapItem, [data-testid='jobsearch-SerpJobCard']")[:15]:
                    title_el = card.select_one("h2.jobTitle span, a[data-jk] span, [class*='jobTitle'] span")
                    company_el = card.select_one("[data-testid='company-name'], span.companyName")
                    location_el = card.select_one("[data-testid='text-location'], div.companyLocation")
                    link_el = card.select_one("a[data-jk], h2 a, a[id^='job_']")

                    title = title_el.get_text(strip=True) if title_el else ""
                    company = company_el.get_text(strip=True) if company_el else ""
                    location = location_el.get_text(strip=True) if location_el else "New York, NY"
                    href = (link_el.get("href") or "") if link_el else ""
                    apply_url = f"https://www.indeed.com{href}" if href.startswith("/") else href

                    if not title or not company or not _is_relevant(title):
                        continue

                    jk_match = re.search(r"jk=([a-f0-9]+)", apply_url)
                    job_key = jk_match.group(1) if jk_match else _id(title + company)

                    jobs.append(_normalize({
                        "external_id": f"indeed_{job_key}",
                        "title": title, "company": company, "location": location,
                        "description": f"Indeed: {title} at {company}. Search: '{query}'.",
                        "apply_url": apply_url, "source": "indeed",
                    }))

                await page.wait_for_timeout(1500)
            except Exception as e:
                print(f"Indeed '{query}': {e}")
    finally:
        await page.close()
    print(f"Indeed: {len(jobs)} jobs")
    return jobs


# ─── Source: Direct company career pages ─────────────────────────────────────
# Companies that don't use Greenhouse/Lever and aren't well-indexed by job boards.
# Claude reads the raw page text and extracts job listings from any page structure.

DIRECT_CAREER_PAGES = [
    # PE / Investment Banks — own ATS, not on Greenhouse/Lever
    ("Goldman Sachs",         "https://www.goldmansachs.com/careers/"),
    ("Morgan Stanley",        "https://www.morganstanley.com/about-us/career"),
    ("Lazard",                "https://www.lazard.com/careers/"),
    ("Evercore",              "https://www.evercore.com/careers/"),
    ("Houlihan Lokey",        "https://www.hl.com/en/careers"),
    ("Jefferies",             "https://www.jefferies.com/careers/"),
    ("KKR",                   "https://www.kkr.com/our-firm/careers"),
    ("Carlyle Group",         "https://www.carlyle.com/careers"),
    ("TPG",                   "https://www.tpg.com/careers"),
    ("Warburg Pincus",        "https://www.warburgpincus.com/careers/"),
    ("Cerberus Capital",      "https://www.cerberuscapital.com/careers/"),
    ("Leonard Green",         "https://www.leonardgreen.com/careers/"),
    ("Apollo Global",         "https://www.apollo.com/about/careers"),
    ("Blackstone",            "https://www.blackstone.com/careers/"),
    ("Fortress Investment",   "https://www.fortress.com/careers"),
    ("Oaktree Capital",       "https://www.oaktreecapital.com/careers"),
    ("Ares Management",       "https://www.aresmgmt.com/careers"),
    # Real Estate
    ("Tishman Speyer",        "https://www.tishmanspeyer.com/who-we-are/careers/"),
    ("Related Companies",     "https://www.related.com/careers"),
    ("Vornado Realty",        "https://www.vno.com/company/careers"),
    ("SL Green",              "https://www.slgreen.com/about/careers"),
    ("RXR",                   "https://www.rxr.com/about/careers"),
    ("Silverstein Properties","https://www.silversteinproperties.com/careers/"),
    ("LeFrak Organization",   "https://www.lefrak.com/about/careers/"),
    ("Paramount Group",       "https://www.paramountgroup.com/careers/"),
    ("Extell Development",    "https://www.extelldev.com/careers/"),
    ("Brookfield",            "https://bam.brookfield.com/about/careers"),
    # Wealth / Family Office
    ("Northern Trust",        "https://careers.northerntrust.com/"),
    ("Bessemer Trust",        "https://www.bessemertrust.com/careers"),
    ("Rockefeller Capital",   "https://www.rockco.com/about-us/careers"),
    ("Glenmede",              "https://www.glenmede.com/about/careers"),
    ("Fiduciary Trust",       "https://www.fiduciarytrust.com/about/careers"),
    ("Silvercrest AM",        "https://www.silvercrestam.com/about/careers"),
    # Asset Management
    ("AllianceBernstein",     "https://www.alliancebernstein.com/corporate/careers"),
    ("Man Group",             "https://www.man.com/careers"),
    ("Two Sigma",             "https://www.twosigma.com/careers/"),
    ("D.E. Shaw",             "https://www.deshaw.com/careers/"),
    ("Citadel",               "https://www.citadel.com/careers/"),
    ("Point72",               "https://www.point72.com/careers/"),
    ("Bridgewater",           "https://www.bridgewater.com/careers/"),
    ("Sculptor Capital",      "https://www.sculptor.com/careers"),
    ("Coatue Management",     "https://www.coatue.com/careers"),
    # Climate / ESG
    ("Energy Impact Partners","https://www.energyimpactpartners.com/about/careers/"),
    ("Galvanize Climate",     "https://www.galvanizeclimate.com/careers"),
    ("Lowercarbon Capital",   "https://jobs.lever.co/lowercarbon"),
    ("Generate Capital",      "https://www.generatecapital.com/careers"),
    ("Fifth Wall",            "https://www.fifthwall.com/careers"),
    ("Breakthrough Energy",   "https://www.breakthroughenergy.org/careers/"),
    ("Congruent Ventures",    "https://www.congruentvc.com/careers/"),
    ("DBL Partners",          "https://www.dbl.vc/careers/"),
    ("Prelude Ventures",      "https://www.preludeventures.com/careers/"),
    ("Aligned Climate",       "https://alignedclimatecapital.com/careers/"),
]


def _extract_jobs_with_claude(company: str, url: str, page_text: str) -> list:
    """Use Claude Haiku to extract structured job listings from arbitrary career page text."""
    import os, anthropic as _ant
    _client = _ant.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    prompt = f"""Extract all open job listings from this company's career page.

Company: {company}
URL: {url}
Page text (truncated):
{page_text[:6000]}

Return ONLY a JSON array. Each item: {{"title": "...", "location": "...", "url": "..."}}
- Only include roles relevant to: investor relations, capital markets, fundraising, fund operations, business development, client service, operations, chief of staff, executive assistant, IR coordinator, capital formation, investment associate, ESG, sustainability, real estate
- Only include NYC, remote, or US-based roles
- If no relevant jobs found, return []
- Do not include engineering, legal, accounting, or IT roles
- Return [] if the page text doesn't contain job listings"""

    try:
        resp = _client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
        )
        text = resp.content[0].text.strip()
        # Extract JSON from response
        import json, re as _re
        match = _re.search(r'\[.*\]', text, _re.DOTALL)
        if match:
            return json.loads(match.group())
    except Exception as e:
        print(f"Claude extraction error for {company}: {e}")
    return []


_JOBS_LINK_SELECTORS = [
    "a[href*='open-position']", "a[href*='openings']",
    "a[href*='/opportunities']", "a[href*='/open-roles']",
    "a[href*='job-listing']", "a[href*='current-openings']",
    "a[href*='vacancies']", "a[href*='/jobs/']",
]
_JOBS_LINK_TEXT = [
    "open positions", "view positions", "view jobs", "see jobs",
    "job openings", "current openings", "open roles", "open opportunities",
    "all jobs", "browse jobs", "career opportunities", "see all",
    "view all", "view openings", "apply now",
]

async def _try_click_through(page) -> bool:
    """Try to click a 'View Jobs' style button to reach actual listings. Returns True if navigated."""
    for sel in _JOBS_LINK_SELECTORS:
        try:
            el = await page.query_selector(sel)
            if el:
                await el.click()
                await page.wait_for_timeout(3000)
                return True
        except Exception:
            pass
    # Try text-based matches
    links = await page.query_selector_all("a")
    for link in links:
        try:
            text = (await link.inner_text()).lower().strip()
            if any(t in text for t in _JOBS_LINK_TEXT):
                await link.click()
                await page.wait_for_timeout(3000)
                return True
        except Exception:
            pass
    return False


async def _direct_company_pages(ctx) -> List[Dict]:
    jobs = []

    for company_name, career_url in DIRECT_CAREER_PAGES:
        page = await ctx.new_page()
        try:
            await page.goto(career_url, wait_until="domcontentloaded", timeout=22000)
            await page.wait_for_timeout(4000)

            # Try to click through to actual job listings page
            await _try_click_through(page)
            await page.wait_for_timeout(3000)

            # Scroll to trigger lazy-loading
            for _ in range(5):
                await page.evaluate("window.scrollBy(0, 700)")
                await page.wait_for_timeout(500)

            final_url = page.url
            page_text = await page.evaluate("document.body.innerText")

            if not page_text or len(page_text.strip()) < 150:
                continue

            extracted = _extract_jobs_with_claude(company_name, final_url, page_text)

            for item in extracted:
                title = item.get("title", "").strip()
                location = item.get("location", "New York, NY").strip()
                job_url = item.get("url", "").strip() or final_url

                if not title or not _is_relevant(title):
                    continue
                if not _is_nyc_or_remote(location):
                    continue

                jobs.append(_normalize({
                    "external_id": f"direct_{_id(title + company_name)}",
                    "title": title,
                    "company": company_name,
                    "location": location or "New York, NY",
                    "description": f"Found on {company_name} careers page. Role: {title}.",
                    "apply_url": job_url,
                    "source": "direct",
                }))

        except Exception as e:
            print(f"Direct page error {company_name}: {e}")
        finally:
            await page.close()

    print(f"Direct company pages: {len(jobs)} relevant jobs")
    return jobs


# ─── Main entry point ─────────────────────────────────────────────────────────

async def scrape_all_jobs() -> List[Dict]:
    greenhouse_task = scrape_greenhouse(GREENHOUSE_COMPANIES)
    lever_task = scrape_lever(LEVER_COMPANIES)
    workday_task = scrape_workday()
    playwright_task = scrape_playwright_sources(SEARCH_QUERIES)

    gh, lv, wd, pw = await asyncio.gather(greenhouse_task, lever_task, workday_task, playwright_task)

    all_jobs = gh + lv + wd + pw

    seen: set = set()
    unique = []
    for job in all_jobs:
        eid = job.get("external_id", "")
        if eid and eid not in seen and job.get("title"):
            seen.add(eid)
            unique.append(job)

    print(f"Total unique jobs scraped: {len(unique)}")
    return unique
