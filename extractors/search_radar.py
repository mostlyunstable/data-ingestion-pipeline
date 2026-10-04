"""
Search Radar: Business & Client Discovery
Finds real business websites based on Niche (e.g. Web Agency, E-commerce, SaaS)
and Location (e.g. Mumbai, Bangalore, New York, London).
Uses resilient search extraction to discover target domains without captchas.
"""
import random
import re
import urllib.parse
import requests
from bs4 import BeautifulSoup
from config import USER_AGENTS, MAX_SEARCH_RESULTS

SKIP_DOMAINS = {
    "google.com", "google.co.in", "bing.com", "duckduckgo.com", "yahoo.com",
    "wikipedia.org", "youtube.com", "facebook.com", "twitter.com", "x.com",
    "instagram.com", "reddit.com", "quora.com", "pinterest.com", "medium.com",
    "glassdoor.com", "indeed.com", "naukri.com", "linkedin.com", "github.com",
    "yelp.com", "yellowpages.com"
}

def clean_target_domain(url: str) -> str:
    """Extracts clean domain from search result link."""
    try:
        # Check if DuckDuckGo redirect link /l/?uddg=URL
        if "duckduckgo.com/l/?" in url:
            parsed_q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            if "uddg" in parsed_q:
                url = parsed_q["uddg"][0]

        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        if any(skip in domain for skip in SKIP_DOMAINS):
            return ""

        # Ignore non-top-level extensions
        if not "." in domain or len(domain) < 4:
            return ""

        return domain
    except Exception:
        return ""

def search_duckduckgo_lite(query: str, max_results: int = MAX_SEARCH_RESULTS) -> list:
    """Queries DuckDuckGo HTML endpoint with stealth headers."""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://html.duckduckgo.com/"
    }

    url = "https://html.duckduckgo.com/html/"
    discovered_domains = []
    seen = set()

    try:
        data = {"q": query, "b": ""}
        resp = requests.post(url, data=data, headers=headers, timeout=10)

        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            # Result links
            links = soup.find_all("a", class_="result__url") or soup.find_all("a", class_="result__snippet")
            if not links:
                links = soup.find_all("a", href=True)

            for a in links:
                raw_href = a.get("href", "")
                domain = clean_target_domain(raw_href)
                if domain and domain not in seen:
                    seen.add(domain)
                    discovered_domains.append(f"https://{domain}")
                    if len(discovered_domains) >= max_results:
                        break
    except Exception as e:
        print(f"[SearchRadar] DuckDuckGo search error: {e}")

    return discovered_domains

def search_bing_lite(query: str, max_results: int = MAX_SEARCH_RESULTS) -> list:
    """Fallback search using Bing standard HTML search."""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    }

    encoded_q = urllib.parse.quote_plus(query)
    url = f"https://www.bing.com/search?q={encoded_q}&count=50"
    discovered = []
    seen = set()

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            # Bing result headings
            for li in soup.find_all("li", class_="b_algo"):
                h2 = li.find("h2")
                if h2:
                    a = h2.find("a", href=True)
                    if a:
                        domain = clean_target_domain(a["href"])
                        if domain and domain not in seen:
                            seen.add(domain)
                            discovered.append(f"https://{domain}")
                            if len(discovered) >= max_results:
                                break
    except Exception as e:
        print(f"[SearchRadar] Bing search error: {e}")

    return discovered

def hunt_businesses(niche: str, location: str, limit: int = 25) -> list:
    """
    Combines search queries to locate business domains.
    Example: 'web design agency', 'Bangalore' -> 'web design agency in Bangalore'
    """
    niche = niche.strip()
    location = location.strip()

    if location:
        queries = [
            f'"{niche}" "{location}"',
            f"{niche} companies in {location}",
            f"best {niche} in {location}"
        ]
    else:
        queries = [
            f"{niche} companies",
            f"top {niche} agencies"
        ]

    results = []
    seen = set()

    for q in queries:
        # Try DuckDuckGo first
        found = search_duckduckgo_lite(q, max_results=limit)
        # If DDG blocked or sparse, fallback to Bing
        if len(found) < 5:
            found.extend(search_bing_lite(q, max_results=limit))

        for url in found:
            clean_dom = clean_target_domain(url)
            if clean_dom and clean_dom not in seen:
                seen.add(clean_dom)
                results.append(url)
                if len(results) >= limit:
                    break
        if len(results) >= limit:
            break

    return results
