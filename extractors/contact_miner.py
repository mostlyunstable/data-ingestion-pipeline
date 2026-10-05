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

DUMMY_DOMAIN_ROOTS = {
    "acme", "example", "sample", "test", "demo", "placeholder", "dummy",
    "yourcompany", "mycompany", "yourdomain", "mydomain", "domain", "website",
    "wixpress", "sentry", "cloudflare", "gravatar", "schema"
}

def clean_email(email: str, company_domain: str = "") -> str:
    """Validates, unescapes, and cleans an email string."""
    if not email:
        return ""
    email = email.strip().lower()

    # Strip HTML / unicode / hex escape artifacts
    email = email.strip('\\/<> \t\n\r"\'')
    for p in ['x3c', 'x3e', 'u003c', 'u003e', '3c', '3e']:
        if email.startswith(p):
            email = email[len(p):]
    email = email.strip('\\/<> \t\n\r"\'')

    # Basic structure check
    if not re.match(r'^[a-z0-9][a-z0-9_.+-]*@[a-z0-9-]+\.[a-z0-9-.]+$', email):
        return ""

    if len(email) < 6 or len(email) > 90:
        return ""

    # Check invalid extensions (like images, scripts, or assets mistaken for email)
    if any(email.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.css', '.js', '.woff', '.ttf', '.json']):
        return ""

    user, domain = email.split('@', 1)

    # Normalize fused html tags onto common users (e.g., lilipsupport -> support)
    for tag in ['lilip', 'lip', 'li', 'p', 'span', 'div', 'br']:
        for cp in ['support', 'hello', 'contact', 'info', 'sales', 'team', 'jobs', 'careers', 'help', 'press', 'legal', 'billing']:
            if user == f"{tag}{cp}":
                user = cp
                email = f"{user}@{domain}"
                break

    # Strip newline prefix on info (e.g. ninfo -> info)
    if user in ['ninfo', 'rinfo', 'tinfo']:
        user = 'info'
        email = f"info@{domain}"

    # Strip run-on concatenated page names from email domains (e.g. .comaccounts -> .com)
    runon_match = re.search(r'(\.(?:com|co\.in|org\.in|org|net|io|ai|app|dev|tech|in|co))(accounts|top|about|contact|terms|privacy|home|services|support|help|team|jobs|blog|press|login|signup|portal)$', domain)
    if runon_match:
        domain = domain[:runon_match.end(1)]
        email = f"{user}@{domain}"

    # Filter out dummy / placeholder usernames
    if user in ["you", "your", "yourname", "user", "username", "name", "email", "test", "demo", "sample", "sam", "fake", "admin", "null", "undefined"]:
        return ""

    # Filter out automated test accounts, QA runners, and stress-test addresses
    if any(bot in user for bot in ["automation", "sanity", "paralleluser", "testuser", "bot-", "perf@", "smoke-test"]):
        return ""

    # TLD must be purely alphabetic (rejects package versions like @1.11.3)
    if '.' not in domain:
        return ""
    tld = domain.split('.')[-1]
    if not re.match(r'^[a-z]{2,12}$', tld):
        return ""

    # Filter out code/cdn/library usernames
    if any(lib in user for lib in ['bootstrap', 'jquery', 'slick', 'carousel', 'swiper', 'fontawesome', 'webpack', 'react']):
        return ""

    # Filter out dummy / error-tracking / infrastructure domain signatures
    if any(ign in domain for ign in [
        "sentry.io", "ingest", "wixpress.com", "gravatar.com", "schema.org",
        "cloudflare.com", "example.com", "example.org", "dummy.com", "test.com",
        "domain.com", "yourdomain.com", "mycompany.com", "github.com", "kimchang.com",
        "google.com", "apple.com", "microsoft.com", "wikimedia.org", "work-email.com"
    ]):
        return ""

    # Filter out sentry hex token endpoints (e.g. 344003a8d11c41d8800fbad8383fdc50)
    if re.match(r'^[a-f0-9]{20,64}$', user):
        return ""

    # Filter out template placeholders and non-human inboxes
    if user in [
        "firstname.lastname", "first.last", "john.doe", "jane.doe", "name.surname",
        "dpo", "legal-notices", "abuse", "noc", "security", "privacy", "privacy-policy",
        "someone", "yourname", "username", "email", "mail", "your"
    ]:
        return ""

    # Filter out dummy domain roots (acme.*, example.*, etc.)
    root_domain = domain.split('.')[0].lower()
    if root_domain in DUMMY_DOMAIN_ROOTS:
        return ""

    if domain in IGNORED_EMAIL_DOMAINS:
        return ""
    if user in IGNORED_EMAIL_PREFIXES:
        return ""

    # Smart reconciliation if email domain was chopped relative to company_domain
    if company_domain:
        cdom = company_domain.lower()
        if cdom.startswith(domain) and len(cdom) == len(domain) + 1 and cdom.endswith('m'):
            domain = cdom
            email = f"{user}@{domain}"

    return email

STATUTORY_FAKE_PHONES = {
    "8009525210", "9164451254",  # California Department of Consumer Affairs (Civil Code 1789.3)
    "8002221222", "8007997233", "8002738255", "8004321000", "8005551212"
}

def clean_phone(phone: str) -> str:
    """Standardizes and strictly validates phone numbers (India & International)."""
    if not phone:
        return ""
    phone = phone.strip()
    digits = re.sub(r'\D', '', phone)

    # Outreach phone numbers MUST be between 10 and 15 digits
    if len(digits) < 10 or len(digits) > 15:
        return ""

    # Reject year timestamps or postal sequences
    if digits.startswith(('2020', '2021', '2022', '2023', '2024', '2025', '2026', '199', '198')):
        return ""

    # Reject statutory disclosure numbers (e.g., CA Dept of Consumer Affairs hotline in terms/privacy)
    norm_10 = digits[1:] if (len(digits) == 11 and digits.startswith('1')) else digits
    if norm_10 in STATUTORY_FAKE_PHONES or digits in STATUTORY_FAKE_PHONES or "55501" in digits:
        return ""

    # Indian Number (+91 or starting with 91)
    if phone.startswith('+91') or (digits.startswith('91') and len(digits) == 12):
        in_digits = digits[2:] if digits.startswith('91') else digits
        if len(in_digits) != 10:
            return ""  # Invalid truncated number
        return f"+91 {in_digits[:5]} {in_digits[5:]}"

    # General international with leading +
    if phone.startswith('+'):
        return phone

    # Standard 10-digit format (US/Intl)
    if len(digits) == 10:
        return f"+1 ({digits[:3]}) {digits[3:6]}-{digits[6:]}"

    return f"+{digits}"

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

    # 3. Regex across soup text (safely separated by spaces) and cleaned HTML with tags converted to spaces
    clean_text = soup.get_text(separator=' ')
    clean_html = re.sub(r'\\?u003[ce]|\\?x3[ce]|<[^>]*>|[<>]|\\n|\\r|\\t', ' ', html_content)
    combined_source = f"{clean_text} {clean_html}"

    raw_matches = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', combined_source)
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
            raw_phone = href.replace('tel:', '').split('?')[0].strip()
            raw_phone = urllib.parse.unquote(raw_phone)
            cleaned = clean_phone(raw_phone)
            if cleaned:
                phones.add(cleaned)

        # WhatsApp links
        elif 'wa.me/' in href or 'whatsapp.com/send' in href:
            match = re.search(r'(?:wa\.me/|phone=)(\d{10,15})', href)
            if match:
                cleaned = clean_phone(f"+{match.group(1)}")
                if cleaned:
                    phones.add(cleaned)

    # 2. Strict Indian Phone Regex (MUST explicitly have +91 or 91- prefix)
    indian_matches = re.findall(r'(?:\+91[\-\s]?|91[\-\s])[6-9]\d{4}[\-\s]?\d{5}\b', text)
    for p in indian_matches:
        cleaned = clean_phone(p)
        if cleaned:
            phones.add(cleaned)

    # 3. Formatted US/UK/International Phone Patterns
    us_matches = re.findall(r'(?:\+1[\s-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}\b', text)
    for p in us_matches:
        cleaned = clean_phone(p)
        if cleaned:
            phones.add(cleaned)

    # +44 (UK)
    uk_matches = re.findall(r'\+44[\s-]?[1-9]\d{1,4}[\s-]?\d{3,4}[\s-]?\d{3,4}\b', text)
    for p in uk_matches:
        cleaned = clean_phone(p)
        if cleaned:
            phones.add(cleaned)

    # Explicit labeled phones: e.g. "Call: +91 988...", "Phone: (555)..."
    labeled = re.findall(r'(?:phone|call us|mobile|contact no|helpline)[\s:]+([+0-9\s().-]{10,20})', text, re.IGNORECASE)
    for p in labeled:
        cleaned = clean_phone(p)
        if cleaned:
            phones.add(cleaned)

    return set(list(phones)[:3])

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
