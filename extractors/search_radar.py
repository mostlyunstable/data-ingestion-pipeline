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

# Indian Spam, Gambling, News, Aggregator & Non-Business Keywords to Annihilate
INDIAN_SPAM_KEYWORDS = {
    # Gambling / Satta / Matka / Betting
    "satta", "matka", "dpboss", "kalyan-matka", "kalyanmatka",
    "gambling", "lottery", "betting", "teenpatti", "casin",
    "nagpur-satta", "satta-matka", "sattamatka",

    # News / Media / Portals / Tabloids / Editorial / Blogs
    "newslaundry", "freepress", "thewire", "opindia", "scroll.in",
    "theprint", "altnews", "swarajya", "ndtv", "timesofindia",
    "hindustantimes", "indiatoday", "dainik", "jagran", "bhaskar",
    "amarujala", "eenadu", "sakshi", "lokmat", "punjabkesari",
    "tribune", "chronicle", "herald", "express", "patrika",
    "wikipedia", "bharatpedia", "vikaspedia",
    "news18", "zeenews", "aajtak", "firstpost", "deccan",
    "medicalnewstoday", "brokebackpacker", "soulofseoul",
    "travelblog", "backpacking",

    # Enterprise Marketplaces & Conglomerates
    "amazon.in", "flipkart.com", "meesho.com", "myntra.com", "ajio.com",
    "tatacliq.com", "jiomart.com", "blinkit.com", "zepto.in",
    "swiggy.com", "zomato.com", "bigbasket.com", "nykaa.com", "purplle.com",

    # Directories, Aggregators & Mega Portals
    "justdial", "indiamart", "tradeindia", "sulekha", "quikr", "olx",
    "practo", "lybrate", "sehat", "credihealth", "vaidam", "clinicspots",
    "magicbricks", "99acres", "housing.com", "nobroker", "squareyards",
    "threebestrated", "docindia", "dermatologistsindia", "bdir.in", "365doctor",
    "cardekho", "zigwheels", "bikedekho", "policybazaar", "paisabazaar",
    "typingbaba", "englishtohindityping", "shiksha", "naukri"
}

SKIP_DOMAINS = {
    # Search engines & Tech giants
    "google.com", "google.co.in", "bing.com", "duckduckgo.com", "yahoo.com", "msn.com", "live.com",
    "microsoft.com", "apple.com", "amazon.com", "amazon.in", "ebay.com", "etsy.com", "wikipedia.org",
    
    # Social media & video & chat platforms
    "facebook.com", "meta.com", "twitter.com", "x.com", "instagram.com", "linkedin.com", "reddit.com",
    "whatsapp.com", "wa.me", "t.me", "telegram.org", "signal.org",
    "quora.com", "pinterest.com", "youtube.com", "tiktok.com", "vimeo.com", "discord.com", "discord.gg",
    "slack.com", "medium.com", "substack.com", "figma.com", "notion.site", "github.com", "gitlab.com", "bitbucket.org",

    # Aggregators & Directories (we want direct business sites, not listings)
    "yelp.com", "yellowpages.com", "indiamart.com", "tradeindia.com", "tradewheel.com",
    "justdial.com", "clutch.co", "g2.com", "capterra.com", "trustpilot.com", "trustradius.com",
    "upwork.com", "fiverr.com", "freelancer.com", "toptal.com", "indeed.com", "glassdoor.com", "naukri.com",
    "investopedia.com", "coursera.org", "udemy.com", "forbes.com", "techcrunch.com", "crunchbase.com",
    "gov.in", "nic.in", "reliancedigital.in", "flipkart.com", "meesho.com",
    "sulekha.com", "zhihu.com", "stylecraze.com", "practo.com", "lybrate.com", "magicbricks.com",
    "99acres.com", "housing.com", "lbb.in", "yappe.in", "quikr.com", "olx.in", "sehat.com",
    "credihealth.com", "vaidam.com", "clinicspots.com", "clinicsspots.com", "topdoctors.co.uk",
    "realself.com", "healthshare.com.au", "doctify.com", "zocdoc.com", "healthgrades.com",
    "vitals.com", "webmd.com", "healthline.com", "goodfirms.co", "sortlist.com", "bark.com",
    "thumbtack.com", "angi.com", "houzz.com", "architecturaldigest.com", "londonprivatedentists.com",
    "whatclinic.com", "dentalplans.com", "1800dentist.com", "ratemds.com", "momjunction.com",
    "femina.in", "cosmopolitan.in", "vogue.in", "gqindia.com", "timeout.com", "tripadvisor.com",
    "foursquare.com", "lawyerratings.com", "avvo.com", "findlaw.com", "justia.com", "lawyers.com",
    "realtor.com", "zillow.com", "redfin.com", "rightmove.co.uk", "zoopla.co.uk", "onthemarket.com",
    "threebestrated.in", "docindia.org", "dermatologistsindia.in", "bdir.in", "365doctor.in",
    "cardekho.com", "zigwheels.com", "bikedekho.com", "policybazaar.com", "paisabazaar.com",
    "typingbaba.com", "englishtohindityping.com", "shiksha.com",

    # News, Media & Content Publishers (not prospective client businesses)
    "theverge.com", "politico.com", "wsj.com", "nytimes.com", "bloomberg.com", "reuters.com",
    "cnn.com", "bbc.com", "theguardian.com", "wired.com", "arstechnica.com", "gizmodo.com",
    "businessinsider.com", "gnome.org", "grapheneos.org", "uceprotect.net", "whitelisted.org",
    "washingtonpost.com", "usatoday.com", "huffpost.com", "nbcnews.com", "cnbc.com",
    "techfundingnews.com", "techmeme.com", "theinformation.com", "venturebeat.com", "zdnet.com",
    "cnet.com", "techradar.com", "stratechery.com", "nobelprize.org", "archive.org", "eff.org",
    "freepressjournal.in", "newslaundry.com", "medicalnewstoday.com", "iadvl.org",

    # Personal hobby, retro, art, and non-commercial portfolio sites
    "dosdays.co.uk", "niklasroy.com", "thoreaubasic.com", "stillwet.art", "dmitrybrant.com",

    # Entertainment, Bollywood, Gossip & Biography Portals (not commercial businesses)
    "imdb.com", "starsunfolded.com", "bollywoodhungama.com", "pinkvilla.com", "filmfare.com",
    "koimoi.com", "tellychakkar.com", "bollywoodbubble.com", "boxofficeindia.com", "filmibeat.com",
    "cineblitz.in", "glamsham.com", "santabanta.com", "scoopwhoop.com", "mensxp.com", "storypick.com",

    # Educational dictionaries, encyclopedias, and reference portals (not SMB clients)
    "dictionary.net", "vocabulary.com", "oxfordlearnersdictionaries.com", "britannica.com",
    "merriam-webster.com", "wordreference.com", "cambridge.org", "collinsdictionary.com",
    "thesaurus.com", "dictionary.com", "wiktionary.org", "wikipedia.org", "dictionaryapi.dev",
    "bharatpedia.org",

    # Platform hubs & Foundation models
    "news.ycombinator.com", "ycombinator.com", "producthunt.com",
    "shopify.com", "wordpress.com", "wordpress.org", "wix.com", "squarespace.com",
    "webflow.com", "hubspot.com", "salesforce.com", "mailchimp.com", "klaviyo.com",
    "stripe.com", "paypal.com", "anthropic.com", "openai.com"
}

ENTERPRISE_DOMAINS = {
    "samsung.com", "apple.com", "google.com", "google.co.in", "microsoft.com", "amazon.com", "amazon.in",
    "plaid.com", "wise.com", "myntra.com", "tatacliq.com", "tata.com", "tatamotors.com", "reliance.com",
    "jio.com", "airtel.in", "irctc.co.in", "irctctourism.com", "ixigo.com", "maxhealthcare.in",
    "aakashhealthcare.com", "geeksforgeeks.org", "deepai.org", "directi.com", "speedtest.net",
    "flipkart.com", "zomato.com", "swiggy.com", "makemytrip.com", "yatra.com", "cleartrip.com",
    "ola.in", "uber.com", "paytm.com", "phonepe.com", "cred.club", "byjus.com", "unacademy.com",
    "vedantu.com", "deloitte.com", "mckinsey.com", "pwc.com", "ey.com", "kpmg.com", "accenture.com",
    "tcs.com", "infosys.com", "wipro.com", "cognizant.com", "hcltech.com", "mpmetrorail.com",
    "confirmtkt.com", "railyatri.in", "shadowfax.in", "dtdc.com", "linear.app", "superhuman.com",
    "raycast.com", "warp.dev", "clickhouse.com", "questdb.io", "timescale.com", "airbyte.com",
    "meltano.com", "dagster.io", "prefect.io", "gymshark.com", "allbirds.com", "warbyparker.com",
    "glossier.com", "hims.com", "nykaa.com", "purplle.com", "ajio.com", "only.in", "wforwoman.com",
    "thecollective.in", "luxepolis.com", "luxuryescapes.com", "toprankers.com", "tophat.com",
    "feedough.com", "edtechhub.org", "nirankarihealthcity.org", "projectreal.gg", "ama.org",
    "zohorecruit.in", "mpcareer.in", "govtjobguru.in", "plutuseducation.com", "digitalregenesys.com",
    "zerodha.com", "zerodha.tech", "groww.in", "upstox.com", "angelone.in", "newtonschool.co",
    "scaler.com", "private.com"
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

        # Exact or subdomain check against skip list (prevents partial substring match bugs)
        if any(domain == skip or domain.endswith("." + skip) for skip in SKIP_DOMAINS):
            return ""

        # Strictly filter out Indian spam, gambling, betting, satta, matka
        if any(spam in domain for spam in INDIAN_SPAM_KEYWORDS):
            return ""
        if re.search(r'(satta|matka|dpboss|kalyan-matka|kalyanmatka|lottery|gambl|teenpatti)', domain):
            return ""

        # Filter out foreign country TLDs when targeting Indian businesses
        if domain.endswith((".cn", ".ru", ".jp", ".de", ".fr", ".br", ".vn", ".it", ".nl", ".pl", ".ua", ".kr", ".tr", ".id", ".th", ".pk", ".bd", ".ng", ".ir", ".cz", ".ro", ".hu", ".se", ".no", ".fi", ".dk", ".ar", ".cl", ".mx", ".za")):
            return ""

        # Filter out dictionary, vocabulary, question-answer, sentence examples, content farms & search portals
        if any(cf in domain for cf in [
            "askdifference", "finesentence", "sentence", "grammar", "meaning", "definition",
            "synonym", "antonym", "thesaurus", "dictionary", "baidu.", "zhihu.", "weibo.",
            "lyrics", "quotes", "sayings", "wallpaper", "apkmod", "modapk", "torrent",
            "converter", "calculator", "differencebetween", "diffchecker", "wikihow",
            "samfw", "softonic", "getdroidtips", "droidcrafts", "tenorshare", "mindthegapps",
            "elevenforum", "tenforums", "symbolab", "rolladie", "onlinedice", "multigentool",
            "apkpure", "apkmirror", "xda-developers"
        ]):
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

        # Filter out news publishers, job aggregators, and banking portals
        if any(domain == m or domain.endswith("." + m) for m in [
            "news18.com", "hindustantimes.com", "siasat.com", "how2shout.com",
            "directv.com", "icicidirect.com", "natelangana.com", "kollegeapply.com",
            "indgovtjobs.in", "ndtv.com", "moneycontrol.com", "livemint.com",
            "firstpost.com", "zeenews.com", "abplive.com", "aajtak.in", "thehindu.com",
            "deccanchronicle.com", "akhiljobs.com", "eapply.in", "adda247.com",
            "hdfcbank.com", "icicibank.com", "sbi.co.in", "tipsnetbd.com"
        ]):
            return ""

        # Filter out massive enterprises and conglomerates
        if any(domain == ent or domain.endswith("." + ent) for ent in ENTERPRISE_DOMAINS):
            return ""

        # Filter out institutional, railway, bank, directory, adult, casino, and aggregator keywords
        if any(k in domain for k in [
            "metrorail", "railway", "bank.", ".bank", "zohorecruit",
            "privatedentists", "findadentist", "findadoctor", "doctorlisting", "clinicdirectory",
            "bestclinics", "dentistnearme", "comparepractices", "lawyerlisting", "directory.",
            "top10", "top-10", "bestin", "casino", "betting", "adult", "porn"
        ]):
            return ""

        base = domain.rsplit('.', 1)[0]
        if any(domain.startswith(p) for p in ["news.", "epaper.", "jobs.", "secure."]) or \
           base.endswith(("times", "news", "jobs", "daily")):
            return ""

        return domain
    except Exception:
        return ""

def search_bing_lite(query: str, max_results: int = MAX_SEARCH_RESULTS) -> list:
    """Organic web search using Bing with Indian locale and base64 redirect decoding."""
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-IN,en-US;q=0.9,en;q=0.8"
    }

    encoded_q = urllib.parse.quote_plus(query)
    discovered = []
    seen = set()

    for offset in [1, 15, 31]:
        if len(discovered) >= max_results:
            break
        url = f"https://www.bing.com/search?q={encoded_q}&setmkt=en-in&setlang=en-in&cc=IN&count=50&first={offset}"
        try:
            resp = requests.get(url, headers=headers, timeout=8)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                
                # Extract candidate links from both h2 headers and b_algo lists
                candidate_links = []
                for h2 in soup.find_all("h2"):
                    a = h2.find("a", href=True)
                    if a and a["href"] not in candidate_links:
                        candidate_links.append(a["href"])

                for li in soup.find_all("li", class_="b_algo"):
                    for a in li.find_all("a", href=True):
                        if a["href"] not in candidate_links:
                            candidate_links.append(a["href"])

                for raw_href in candidate_links:
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
        except Exception:
            pass

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
    Combines precision multi-engine search queries to locate real target Indian domains.
    Uses natural high-yield query patterns without rigid double quotes.
    """
    niche = niche.strip()
    location = location.strip()
    clean_loc = location.replace(",", " ").strip()

    results = []
    seen = set()

    # Precision Organic Search Queries for Indian Businesses
    if clean_loc:
        queries = [
            f"{niche} in {clean_loc} official website contact",
            f"{niche} clinic {clean_loc} appointment phone +91",
            f"{niche} studio {clean_loc} portfolio contact us",
            f"{niche} brand India buy online contact",
            f"{niche} {clean_loc} book appointment contact us",
            f"{niche} {clean_loc} phone email contact"
        ]
    else:
        queries = [
            f"{niche} India official website contact us",
            f"{niche} clinic India appointment phone",
            f"{niche} boutique studio practice India contact"
        ]

    for q in queries:
        found = search_bing_lite(q, max_results=limit)
        for url in found:
            clean_dom = clean_target_domain(url)
            if clean_dom and clean_dom not in seen:
                seen.add(clean_dom)
                results.append(f"https://{clean_dom}")
                if len(results) >= limit:
                    return results[:limit]

    return results[:limit]
