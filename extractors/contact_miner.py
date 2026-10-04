"""
Aggressive Contact & Social Miner
Extracts emails (including Cloudflare-obfuscated), phone numbers (India + International),
LinkedIn company & personal profiles, socials, and location signals.
"""
import re
import urllib.parse
from bs4 import BeautifulSoup
from config import IGNORED_EMAIL_DOMAINS, IGNORED_EMAIL_PREFIXES

# Indian Major Cities & States for geo-detection
INDIAN_GEO_KEYWORDS = {
    "india", "bengaluru", "bangalore", "mumbai", "delhi", "new delhi",
    "hyderabad", "chennai", "pune", "gurgaon", "gurugram", "noida",
    "kolkata", "ahmedabad", "jaipur", "kochi", "coimbatore", "chandigarh",
    "indore", "karnataka", "maharashtra", "haryana", "tamil nadu", "kerala"
}

# International Geo Keywords
US_GEO_KEYWORDS = {
    "usa", "united states", "california", "new york", "texas", "florida",
    "san francisco", "austin", "chicago", "los angeles", "seattle", "boston"
}
UK_GEO_KEYWORDS = {"uk", "united kingdom", "london", "manchester", "birmingham", "edinburgh"}
CAN_GEO_KEYWORDS = {"canada", "toronto", "vancouver", "montreal"}
AUS_GEO_KEYWORDS = {"australia", "sydney", "melbourne", "brisbane"}

def decode_cloudflare_email(cf_hex: str) -> str:
    """Decodes Cloudflare email obfuscation (data-cfemail)."""
    try:
        r = int(cf_hex[:2], 16)
        email = ''.join([chr(int(cf_hex[i:i+2], 16) ^ r) for i in range(2, len(cf_hex), 2)])
        return email
    except Exception:
        return ""

def clean_email(email: str) -> str:
    """Validates and cleans an email string."""
    if not email:
        return ""
    email = email.strip().lower()

    # Strip unicode escape artifacts like u003e, u003c
    email = re.sub(r'^(?:u003e|u003c|\\u003e|\\u003c|>|<|/|\\)+', '', email)
    email = re.sub(r'^[^\w]+|[^\w]+$', '', email)

    # Basic structure check
    if not re.match(r'^[a-z0-9][a-z0-9_.+-]*@[a-z0-9-]+\.[a-z0-9-.]+$', email):
        return ""

    # Check length
    if len(email) < 6 or len(email) > 100:
        return ""

    # Check invalid extensions (like images, scripts, or assets mistaken for email)
    if any(email.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.css', '.js', '.woff', '.ttf']):
        return ""

    user, domain = email.split('@', 1)

    # User must not be dummy or library
    if user in ["u003e", "u003c", "3e", "3c", "test", "demo", "sample", "you", "user", "username", "sam", "fake"]:
        return ""

    # TLD must be purely alphabetic (rejects package versions like @1.11.3)
    if '.' not in domain:
        return ""
    tld = domain.split('.')[-1]
    if not re.match(r'^[a-zA-Z]{2,12}$', tld):
        return ""

    # Filter out code/cdn/library usernames
    if any(lib in user for lib in ['bootstrap', 'jquery', 'slick', 'carousel', 'swiper', 'fontawesome', 'webpack', 'react']):
        return ""

    if domain in IGNORED_EMAIL_DOMAINS:
        return ""
    if user in IGNORED_EMAIL_PREFIXES:
        return ""

    return email

def extract_emails(html_content: str, soup: BeautifulSoup) -> set:
    """Aggressively finds emails from plain text, mailto links, and Cloudflare tags."""
    emails = set()

    # 1. Cloudflare protected emails
    for tag in soup.find_all(attrs={"data-cfemail": True}):
        decoded = decode_cloudflare_email(tag["data-cfemail"])
        cleaned = clean_email(decoded)
        if cleaned:
            emails.add(cleaned)

    # 2. mailto: links
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('mailto:'):
            raw = href.replace('mailto:', '').split('?')[0]
            cleaned = clean_email(raw)
            if cleaned:
                emails.add(cleaned)

    # 3. Clean Regex across all HTML (decoding common unicode escapes first)
    clean_html = html_content.replace('\\u003e', '').replace('\\u003c', '').replace('u003e', '').replace('u003c', '')
    raw_matches = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', clean_html)
    for match in raw_matches:
        cleaned = clean_email(match)
        if cleaned:
            emails.add(cleaned)

    return emails

def extract_phones(text: str, soup: BeautifulSoup) -> set:
    """Extracts strictly verified phone numbers (India + Int'l). Never matches random numbers."""
    phones = set()

    # 1. tel: links
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        if href.startswith('tel:'):
            raw_phone = href.replace('tel:', '').strip()
            raw_phone = urllib.parse.unquote(raw_phone)
            digits = re.sub(r'\D', '', raw_phone)
            if 8 <= len(digits) <= 15:
                phones.add(raw_phone)

        # WhatsApp links
        elif 'wa.me/' in href or 'whatsapp.com/send' in href:
            match = re.search(r'(?:wa\.me/|phone=)(\d{10,15})', href)
            if match:
                w_phone = f"+{match.group(1)}"
                phones.add(w_phone)

    # 2. Strict Indian Phone Regex (MUST explicitly have +91 or 91- prefix)
    indian_matches = re.findall(r'(?:\+91[\-\s]?|91[\-\s])[6-9]\d{4}[\-\s]?\d{5}\b', text)
    for p in indian_matches:
        clean = re.sub(r'\s+', ' ', p.strip())
        digits = re.sub(r'\D', '', clean)
        if len(digits) >= 10:
            if not clean.startswith('+'):
                clean = f"+{clean}"
            phones.add(clean)

    # 3. Formatted US/UK/International Phone Patterns
    # (xxx) xxx-xxxx
    us_matches = re.findall(r'(?:\+1[\s-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b', text)
    for p in us_matches:
        digits = re.sub(r'\D', '', p)
        if len(digits) == 10 or (len(digits) == 11 and digits.startswith('1')):
            # Avoid postal codes or fake year sequences
            if not p.startswith(('202', '199', '198')):
                phones.add(p.strip())

    # +44 (UK)
    uk_matches = re.findall(r'\+44[\s-]?[1-9]\d{1,4}[\s-]?\d{3,4}[\s-]?\d{3,4}\b', text)
    for p in uk_matches:
        phones.add(p.strip())

    # Explicit labeled phones: e.g. "Call: +91 988...", "Phone: (555)..."
    labeled = re.findall(r'(?:phone|call us|mobile|contact no|helpline)[\s:]+([+0-9\s().-]{8,20})', text, re.IGNORECASE)
    for p in labeled:
        clean = p.strip()
        digits = re.sub(r'\D', '', clean)
        if 8 <= len(digits) <= 15 and not clean.startswith(('202', '199')):
            phones.add(clean)

    # Deduplicate by pure numeric digits
    unique_phones = {}
    for p in phones:
        digits = re.sub(r'\D', '', p)
        if 7 <= len(digits) <= 15:
            if digits not in unique_phones or len(p) > len(unique_phones[digits]):
                unique_phones[digits] = p

    return set(list(unique_phones.values())[:3])

def extract_socials_and_linkedin(soup: BeautifulSoup) -> dict:
    """Extracts social profiles and distinguishes LinkedIn company vs personal profile."""
    socials = {
        "linkedin_company": "",
        "linkedin_profiles": [],
        "twitter": "",
        "instagram": "",
        "facebook": "",
        "github": ""
    }

    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        lower_href = href.lower()

        # LinkedIn Company vs Individual Founder/Team
        if "linkedin.com/company/" in lower_href or "linkedin.com/school/" in lower_href:
            if not socials["linkedin_company"]:
                socials["linkedin_company"] = href.split('?')[0]
        elif "linkedin.com/in/" in lower_href:
            clean_profile = href.split('?')[0]
            if clean_profile not in socials["linkedin_profiles"]:
                socials["linkedin_profiles"].append(clean_profile)

        # Twitter / X
        elif ("twitter.com/" in lower_href or "x.com/" in lower_href) and not socials["twitter"]:
            if not any(skip in lower_href for skip in ['/intent/', '/share', '/status']):
                socials["twitter"] = href.split('?')[0]

        # Instagram
        elif "instagram.com/" in lower_href and not socials["instagram"]:
            if not any(skip in lower_href for skip in ['/p/', '/reel/', '/stories']):
                socials["instagram"] = href.split('?')[0]

        # Facebook
        elif "facebook.com/" in lower_href and not socials["facebook"]:
            if not any(skip in lower_href for skip in ['/sharer', '/share', '/dialog']):
                socials["facebook"] = href.split('?')[0]

        # GitHub
        elif "github.com/" in lower_href and not socials["github"]:
            socials["github"] = href.split('?')[0]

    return socials

def detect_country_and_location(text: str, phones: set) -> tuple:
    """Infers whether the business is Indian or International."""
    lower_text = text.lower()

    # Check phones for +91 or +1 or +44
    for phone in phones:
        if "+91" in phone:
            return "India", ""
        if "+44" in phone:
            return "United Kingdom", "London"
        if "+1" in phone:
            return "United States", ""

    # Check Indian geo keywords
    for kw in INDIAN_GEO_KEYWORDS:
        if f" {kw} " in f" {lower_text} " or f",{kw}" in lower_text or f", {kw}" in lower_text:
            city = kw.title() if kw != "india" else ""
            return "India", city

    # Check US keywords
    for kw in US_GEO_KEYWORDS:
        if kw in lower_text:
            return "United States", kw.title() if kw != "usa" and kw != "united states" else ""

    # Check UK keywords
    for kw in UK_GEO_KEYWORDS:
        if kw in lower_text:
            return "United Kingdom", kw.title() if kw != "uk" else ""

    for kw in CAN_GEO_KEYWORDS:
        if kw in lower_text:
            return "Canada", kw.title() if kw != "canada" else ""

    for kw in AUS_GEO_KEYWORDS:
        if kw in lower_text:
            return "Australia", kw.title() if kw != "australia" else ""

    return "International / Global", ""
