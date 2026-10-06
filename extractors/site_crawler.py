"""
High-Speed Async Site Deep Crawler
Crawls homepage + top contact/about/team subpages in parallel.
Extracts company metadata, emails, phones, socials, and tech stack.
"""
import asyncio
import random
import re
import urllib.parse
import aiohttp
from bs4 import BeautifulSoup
from config import USER_AGENTS, CONTACT_SUBPAGES, REQUEST_TIMEOUT
from extractors.contact_miner import (
    extract_emails, extract_phones, extract_socials_and_linkedin,
    detect_country_and_location
)
from extractors.tech_detector import detect_tech_stack
from transformers.opportunity_auditor import audit_business_for_services
from transformers.cleaner import clean_company_brand_name

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

def normalize_url(raw_url: str) -> str:
    """Ensures URL starts with http(s):// and is clean."""
    url = raw_url.strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        url = "https://" + url
    return url.rstrip("/")

def extract_domain(url: str) -> str:
    """Extracts base domain (e.g., example.com) from any URL."""
    try:
        parsed = urllib.parse.urlparse(normalize_url(url))
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return url.lower()

def is_spa_or_js_rendered(html: str) -> bool:
    """
    Detects if HTML is an unhydrated JavaScript client-side SPA or blocked page needing browser rendering.
    """
    if not html or len(html.strip()) < 100:
        return True
    lower_html = html.lower()
    if "just a moment..." in lower_html and "cloudflare" in lower_html:
        return True
    if "enable javascript to continue" in lower_html or "please turn javascript on" in lower_html:
        return True
    if "<noscript>you need to enable javascript" in lower_html:
        return True
    spa_markers = [
        '<div id="root"></div>', '<div id="root"> </div>',
        '<div id="app"></div>', '<div id="app"> </div>',
        '<div id="__next"></div>', '<div id="__next"> </div>',
        '<app-root></app-root>', '<app-root> </app-root>'
    ]
    if any(m in lower_html for m in spa_markers):
        clean = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
        clean = re.sub(r'<[^>]+>', ' ', clean)
        visible_text = ' '.join(clean.split())
        if len(visible_text) < 250:
            return True
    return False

async def fetch_html_playwright(url: str, timeout_ms: int = 12000) -> str:
    """
    Renders JavaScript client-side single page applications (SPAs) using headless Chromium.
    Safely times out and handles environment limits gracefully.
    """
    if not PLAYWRIGHT_AVAILABLE:
        return ""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-blink-features=AutomationControlled"
                ]
            )
            context = await browser.new_context(
                user_agent=random.choice(USER_AGENTS),
                viewport={"width": 1280, "height": 800},
                java_script_enabled=True,
                ignore_https_errors=True
            )
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                await page.wait_for_timeout(1500)
                content = await page.content()
                await browser.close()
                return content[:2_000_000]
            except Exception:
                await browser.close()
                return ""
    except Exception:
        return ""

async def fetch_html(session: aiohttp.ClientSession, url: str) -> str:
    """Fetches HTML with stealth headers and SSL ignore."""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Upgrade-Insecure-Requests": "1"
    }
    try:
        async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT), ssl=False) as resp:
            if resp.status == 200:
                # Limit to 2MB to prevent memory bloat on massive pages
                content = await resp.read()
                return content[:2_000_000].decode("utf-8", errors="ignore")
    except Exception:
        pass
    return ""

async def crawl_single_company(target_url_or_domain: str, niche: str = "", source: str = "direct") -> dict:
    """
    Deep-mines a company website:
    1. Homepage extraction
    2. Parallel subpage discovery & extraction (/contact, /about, /team)
    3. Merges emails, phones, socials, and tech stacks.
    """
    base_url = normalize_url(target_url_or_domain)
    domain = extract_domain(base_url)

    if not domain:
        return {}

    result = {
        "domain": domain,
        "company_name": "",
        "website": f"https://{domain}",
        "emails": set(),
        "phones": set(),
        "linkedin_company": "",
        "linkedin_profiles": [],
        "twitter": "",
        "instagram": "",
        "facebook": "",
        "github": "",
        "country": "",
        "city": "",
        "industry_niche": niche or "Digital / Business",
        "tech_stack": [],
        "meta_description": "",
        "source": source
    }

    connector = aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        # Step 1: Fetch Homepage
        home_html = await fetch_html(session, result["website"])
        if not home_html:
            # Try http fallback
            home_html = await fetch_html(session, f"http://{domain}")

        # Headless Browser SPA Fallback (renders client-side JS / React / Vue / blocked shells)
        if is_spa_or_js_rendered(home_html):
            pw_html = await fetch_html_playwright(result["website"])
            if pw_html and len(pw_html) > len(home_html):
                home_html = pw_html

        if not home_html:
            return {}

        home_soup = BeautifulSoup(home_html, "html.parser")

        # Extract Title & Meta Description
        title = home_soup.title.string.strip() if home_soup.title and home_soup.title.string else ""
        result["company_name"] = clean_company_brand_name(title, domain)

        meta_desc = home_soup.find("meta", attrs={"name": "description"}) or home_soup.find("meta", attrs={"property": "og:description"})
        if meta_desc and meta_desc.get("content"):
            result["meta_description"] = meta_desc["content"].strip()[:400]

        # Extract Contacts & Tech from Homepage
        result["emails"].update(extract_emails(home_html, home_soup))
        result["phones"].update(extract_phones(home_soup.get_text(), home_soup))
        home_socials = extract_socials_and_linkedin(home_soup)
        for k, v in home_socials.items():
            if v and not result[k]:
                result[k] = v

        result["tech_stack"] = detect_tech_stack(home_html, home_soup)

        # Step 2: Discover High-Value Subpages (Contact, About, Team, Doctors, Founders)
        subpage_urls = set()
        for a in home_soup.find_all("a", href=True):
            href = a["href"].strip()
            lower_href = href.lower()
            if any(sub in lower_href for sub in ["contact", "about", "team", "doctor", "dentist", "specialist", "founder", "leadership", "meet"]):
                full_sub = urllib.parse.urljoin(result["website"], href)
                # Keep only same domain
                if extract_domain(full_sub) == domain:
                    subpage_urls.add(full_sub)

        # If none found from links, probe common endpoints
        if not subpage_urls:
            for sub in ["/contact", "/about", "/team", "/doctors"]:
                subpage_urls.add(f"https://{domain}{sub}")

        # Limit to top 4 candidate subpages for fast aggressive execution
        target_subpages = list(subpage_urls)[:4]

        # Step 3: Fetch Subpages in Parallel
        subpage_tasks = [fetch_html(session, s_url) for s_url in target_subpages]
        subpage_results = await asyncio.gather(*subpage_tasks, return_exceptions=True)

        combined_text = home_soup.get_text()

        for s_url, s_html in zip(target_subpages, subpage_results):
            sub_content = s_html if isinstance(s_html, str) else ""
            if is_spa_or_js_rendered(sub_content):
                pw_sub = await fetch_html_playwright(s_url, timeout_ms=8000)
                if pw_sub and len(pw_sub) > len(sub_content):
                    sub_content = pw_sub

            if sub_content:
                s_soup = BeautifulSoup(sub_content, "html.parser")
                combined_text += " " + s_soup.get_text()

                result["emails"].update(extract_emails(sub_content, s_soup))
                is_legal = any(k in s_url.lower() for k in ["privacy", "terms", "legal", "policy", "compliance"])
                if not is_legal:
                    result["phones"].update(extract_phones(s_soup.get_text(), s_soup))

                s_socials = extract_socials_and_linkedin(s_soup)
                for k, v in s_socials.items():
                    if k == "linkedin_profiles":
                        for p in v:
                            if p not in result["linkedin_profiles"]:
                                result["linkedin_profiles"].append(p)
                    elif v and not result[k]:
                        result[k] = v

        # Convert sets to lists
        result["emails"] = sorted(list(result["emails"]))
        result["phones"] = sorted(list(result["phones"]))

        # Step 4: Infer Country & Geo Location
        country, city = detect_country_and_location(combined_text, result["phones"])
        result["country"] = country
        result["city"] = city

        # Step 5: Autonomous Service & Opportunity Audit
        audit = audit_business_for_services(
            html_content=home_html,
            soup=home_soup,
            company_name=result["company_name"],
            tech_stack=result["tech_stack"],
            niche=result["industry_niche"],
            combined_text=combined_text,
            emails=result["emails"],
            domain=domain
        )
        result["service_match"] = audit["service_match"]
        result["opportunity_type"] = audit["opportunity_type"]
        result["audit_notes"] = audit["audit_notes"]
        result["contact_name"] = audit["contact_name"]
        result["business_summary"] = audit["business_summary"]
        result["where_they_are_good"] = audit["where_they_are_good"]
        result["where_they_are_lacking"] = audit["where_they_are_lacking"]
        result["confident_pitch"] = audit["confident_pitch"]
        result["lead_score"] = audit["lead_score"]
        result["pitch_hook"] = audit["pitch_hook"]

    return result
