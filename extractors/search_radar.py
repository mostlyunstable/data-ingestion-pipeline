"""
Search Radar: Real Business & Client Discovery
Discovers live, operational businesses across:
- Organic Search Engine extraction (Bing with base64 redirect decoding)
- GitHub Tech Organization directories
- High-intent query rotators across Indian & Global commercial hubs.
"""
import random
import re
import base64
import urllib.parse
import requests
from bs4 import BeautifulSoup
from config import USER_AGENTS, MAX_SEARCH_RESULTS

SKIP_DOMAINS = {
    # Search engines & Tech giants
    "google.com", "google.co.in", "bing.com", "duckduckgo.com", "yahoo.com", "msn.com", "live.com",
    "microsoft.com", "apple.com", "amazon.com", "ebay.com", "etsy.com", "wikipedia.org",
    
    # Social media & video
    "facebook.com", "twitter.com", "x.com", "instagram.com", "linkedin.com", "reddit.com",
    "quora.com", "pinterest.com", "youtube.com", "tiktok.com", "vimeo.com", "discord.com", "discord.gg",
    "slack.com", "medium.com", "substack.com", "figma.com", "notion.site", "github.com", "gitlab.com", "bitbucket.org",

    # Aggregators & Directories (we want direct business sites, not listings)
    "yelp.com", "yellowpages.com", "indiamart.com", "tradeindia.com", "tradewheel.com",
    "justdial.com", "clutch.co", "g2.com", "capterra.com", "trustpilot.com", "trustradius.com",
    "upwork.com", "fiverr.com", "freelancer.com", "toptal.com", "indeed.com", "glassdoor.com", "naukri.com",
    "investopedia.com", "coursera.org", "udemy.com", "forbes.com", "techcrunch.com", "crunchbase.com",
    "gov.in", "nic.in", "reliancedigital.in", "flipkart.com",

    # News, Media & Content Publishers (not prospective client businesses)
    "theverge.com", "politico.com", "wsj.com", "nytimes.com", "bloomberg.com", "reuters.com",
    "cnn.com", "bbc.com", "theguardian.com", "wired.com", "arstechnica.com", "gizmodo.com",
    "businessinsider.com", "gnome.org", "grapheneos.org", "uceprotect.net", "whitelisted.org",
    "washingtonpost.com", "usatoday.com", "huffpost.com", "nbcnews.com", "cnbc.com",
    "techfundingnews.com", "techmeme.com", "theinformation.com", "venturebeat.com", "zdnet.com",
    "cnet.com", "techradar.com", "stratechery.com", "nobelprize.org", "archive.org", "eff.org",

    # Personal hobby, retro, art, and non-commercial portfolio sites
    "dosdays.co.uk", "niklasroy.com", "thoreaubasic.com", "stillwet.art", "dmitrybrant.com",

    # Platform hubs & Foundation models
    "news.ycombinator.com", "ycombinator.com", "producthunt.com",
    "shopify.com", "wordpress.com", "wordpress.org", "wix.com", "squarespace.com",
    "webflow.com", "hubspot.com", "salesforce.com", "mailchimp.com", "klaviyo.com",
    "stripe.com", "paypal.com", "anthropic.com", "openai.com"
}

def decode_bing_u(u_val: str) -> str:
    """Decodes Bing click tracking base64 parameter &u=a1<base64>&ntb=1."""
    if not u_val:
        return ""
    try:
        if u_val.startswith("a1"):
            b64 = u_val[2:]
            padding = len(b64) % 4
            if padding:
                b64 += "=" * (4 - padding)
            return base64.b64decode(b64).decode("utf-8", errors="ignore")
    except Exception:
        pass
    return ""

def clean_target_domain(url: str) -> str:
    """Extracts clean, non-directory business domain from any URL."""
    if not url:
        return ""
    try:
        # Check if DuckDuckGo redirect link /l/?uddg=URL
        if "duckduckgo.com/l/?" in url:
            parsed_q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            if "uddg" in parsed_q:
                url = parsed_q["uddg"][0]

        # Check if Bing tracking redirect link
        if "bing.com/ck/a" in url:
            parsed_q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            if "u" in parsed_q:
                decoded = decode_bing_u(parsed_q["u"][0])
                if decoded:
                    url = decoded

        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]

        if not domain or len(domain) < 4 or "." not in domain:
            return ""

        if any(skip in domain for skip in SKIP_DOMAINS):
            return ""

        # Filter out government, educational portals, personal blogs, and non-commercial TLDs
        if (domain.endswith(".gov") or domain.endswith(".edu") or domain.endswith(".mil") or
            domain.endswith(".art") or domain.endswith(".museum") or
            domain.startswith("blog.") or ".blogspot." in domain or ".wordpress." in domain or
            domain.endswith(".org.in") or domain.endswith(".nic.in")):
            return ""

        # Filter out documentation, developer, api, and infrastructure subdomains
        if any(domain.startswith(sub) for sub in [
            "docs.", "doc.", "developer.", "developers.", "api.", "status.",
            "support.", "help.", "community.", "forum.", "cdn.", "assets."
        ]):
            return ""

        return domain
    except Exception:
        return ""

def search_bing_lite(query: str, max_results: int = MAX_SEARCH_RESULTS) -> list:
    """Organic web search using Bing with base64 redirect decoding."""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9"
    }

    encoded_q = urllib.parse.quote_plus(query)
    url = f"https://www.bing.com/search?q={encoded_q}&count=40"
    discovered = []
    seen = set()

    try:
        resp = requests.get(url, headers=headers, timeout=9)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            for li in soup.find_all("li", class_="b_algo"):
                for a in li.find_all("a", href=True):
                    raw_href = a["href"]
                    real_href = raw_href
                    if "bing.com/ck/a" in raw_href:
                        parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                        if "u" in parsed:
                            decoded = decode_bing_u(parsed["u"][0])
                            if decoded:
                                real_href = decoded

                    domain = clean_target_domain(real_href)
                    if domain and domain not in seen:
                        seen.add(domain)
                        discovered.append(f"https://{domain}")
                        if len(discovered) >= max_results:
                            break
                if len(discovered) >= max_results:
                    break
    except Exception as e:
        print(f"[SearchRadar] Bing search error: {e}")

    return discovered

def search_duckduckgo_lite(query: str, max_results: int = MAX_SEARCH_RESULTS) -> list:
    """DuckDuckGo query fallback."""
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
        resp = requests.post(url, data=data, headers=headers, timeout=8)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            links = soup.find_all("a", class_="result__url") or soup.find_all("a", class_="result__snippet") or soup.find_all("a", href=True)
            for a in links:
                raw_href = a.get("href", "")
                domain = clean_target_domain(raw_href)
                if domain and domain not in seen:
                    seen.add(domain)
                    discovered_domains.append(f"https://{domain}")
                    if len(discovered_domains) >= max_results:
                        break
    except Exception:
        pass

    return discovered_domains

def discover_github_tech_companies(location: str = "Bangalore", keyword: str = "", limit: int = 15) -> list:
    """
    High-fidelity discovery of real businesses and digital agencies via GitHub Organizations.
    Pulls verified business URLs with zero scraping friction.
    """
    headers = {"User-Agent": "OmniLead-Scanner/1.0"}
    query_parts = ["type:org"]
    if location:
        query_parts.append(f"location:{location}")
    if keyword:
        query_parts.append(keyword)

    q = " ".join(query_parts)
    url = f"https://api.github.com/search/users?q={urllib.parse.quote(q)}&per_page={min(limit, 25)}"
    discovered = []
    seen = set()

    try:
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            for item in items:
                login = item.get("login")
                if not login:
                    continue
                try:
                    org_resp = requests.get(f"https://api.github.com/orgs/{login}", headers=headers, timeout=4)
                    if org_resp.status_code == 200:
                        blog = org_resp.json().get("blog", "")
                        if blog:
                            domain = clean_target_domain(blog)
                            if domain and domain not in seen:
                                seen.add(domain)
                                discovered.append(f"https://{domain}")
                                if len(discovered) >= limit:
                                    break
                except Exception:
                    continue
    except Exception as e:
        print(f"[SearchRadar] GitHub org discovery error: {e}")

    return discovered

def hunt_businesses(niche: str, location: str, limit: int = 25) -> list:
    """
    Combines multi-engine search queries to locate real target domains.
    Rotates queries across Bing, GitHub Org directories, and DuckDuckGo.
    """
    niche = niche.strip()
    location = location.strip()

    results = []
    seen = set()

    # 1. First probe GitHub Organizations for tech/agency niches
    if any(k in niche.lower() for k in ["tech", "software", "agency", "saas", "app", "dev", "ai"]):
        loc = location or random.choice(["Bangalore", "Mumbai", "San Francisco", "London", "Austin"])
        kw = random.choice(["agency", "tech", "software", "solutions", "labs", "studio"])
        gh_results = discover_github_tech_companies(location=loc, keyword=kw, limit=min(limit, 10))
        for u in gh_results:
            d = clean_target_domain(u)
            if d and d not in seen:
                seen.add(d)
                results.append(u)

    if len(results) >= limit:
        return results[:limit]

    # 2. Organic Web Search Queries
    if location:
        queries = [
            f'"{niche}" in {location} official website',
            f"{niche} companies {location}",
            f"top {niche} in {location}"
        ]
    else:
        queries = [
            f"{niche} companies",
            f"top {niche} agencies"
        ]

    for q in queries:
        found = search_bing_lite(q, max_results=limit)
        if len(found) < 4:
            found.extend(search_duckduckgo_lite(q, max_results=limit))

        for url in found:
            clean_dom = clean_target_domain(url)
            if clean_dom and clean_dom not in seen:
                seen.add(clean_dom)
                results.append(url)
                if len(results) >= limit:
                    break
        if len(results) >= limit:
            break

    return results[:limit]
