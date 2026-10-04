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

def extract_company_name(title: str, domain: str) -> str:
    """Infers clean company name from HTML title or domain."""
    if not title:
        # Fallback to domain name capitalized
        name = domain.split(".")[0]
        return name.replace("-", " ").replace("_", " ").title()

    # Split common title delimiters: |, -, :, •, ~
    delimiters = ["|", " - ", " – ", " — ", " : ", " • ", " ~ "]
    parts = [title]
    for d in delimiters:
        if d in title:
            parts = [p.strip() for p in title.split(d) if p.strip()]
            break

    # Pick the part that matches the domain root or looks most like a brand
    clean_domain_root = domain.split(".")[0].replace("-", "").replace("_", "").lower()
    candidate = parts[-1] if len(parts) > 1 else parts[0]

    for p in parts:
        p_clean = re.sub(r'[^a-zA-Z0-9]', '', p).lower()
        if clean_domain_root in p_clean or (len(clean_domain_root) > 4 and clean_domain_root[:4] in p_clean):
            candidate = p
            break
        elif not any(p.lower().startswith(bad) for bad in ["best ", "top ", "welcome ", "#1 "]) and len(p) < len(candidate):
            candidate = p

    candidate = re.sub(r'^(Welcome to|Home|Home Page|Official Site)\s*[:-]?\s*', '', candidate, flags=re.IGNORECASE)
    return candidate.strip() or domain

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

        if not home_html:
            return {}

        home_soup = BeautifulSoup(home_html, "html.parser")

        # Extract Title & Meta Description
        title = home_soup.title.string.strip() if home_soup.title and home_soup.title.string else ""
        result["company_name"] = extract_company_name(title, domain)

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

        # Step 2: Discover High-Value Subpages (Contact, About, Team)
        subpage_urls = set()
        for a in home_soup.find_all("a", href=True):
            href = a["href"].strip()
            # Normalize internal link
            lower_href = href.lower()
            if any(sub in lower_href for sub in ["contact", "about", "team", "privacy"]):
                full_sub = urllib.parse.urljoin(result["website"], href)
                # Keep only same domain
                if extract_domain(full_sub) == domain:
                    subpage_urls.add(full_sub)

        # If none found from links, probe common endpoints
        if not subpage_urls:
            for sub in ["/contact", "/about", "/team"]:
                subpage_urls.add(f"https://{domain}{sub}")

        # Limit to top 4 candidate subpages for fast aggressive execution
        target_subpages = list(subpage_urls)[:4]

        # Step 3: Fetch Subpages in Parallel
        subpage_tasks = [fetch_html(session, s_url) for s_url in target_subpages]
        subpage_results = await asyncio.gather(*subpage_tasks, return_exceptions=True)

        combined_text = home_soup.get_text()

        for s_html in subpage_results:
            if isinstance(s_html, str) and s_html:
                s_soup = BeautifulSoup(s_html, "html.parser")
                combined_text += " " + s_soup.get_text()

                result["emails"].update(extract_emails(s_html, s_soup))
                result["phones"].update(extract_phones(s_soup.get_text(), s_soup))

                s_socials = extract_socials_and_linkedin(s_soup)
                for k, v in s_socials.items():
                    if k == "linkedin_profiles":
                        for p in v:
                            if p not in result["linkedin_profiles"]:
                                result["linkedin_profiles"].append(p)
                    elif v and not result[k]:
                        result[k] = v

        # Step 4: Infer Country & Geo Location
        country, city = detect_country_and_location(combined_text, result["phones"])
        result["country"] = country
        result["city"] = city

        # Step 5: Autonomous Service & Opportunity Audit
        audit = audit_business_for_services(home_html, home_soup, result["company_name"], result["tech_stack"], result["industry_niche"])
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

    # Convert sets to lists
    result["emails"] = sorted(list(result["emails"]))
    result["phones"] = sorted(list(result["phones"]))

    return result
