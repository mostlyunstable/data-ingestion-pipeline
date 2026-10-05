import re
from extractors.contact_miner import clean_email, clean_phone

def clean_text(text: str) -> str:
    """Removes weird encoding artifacts, excessive whitespace, and newlines."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

GENERIC_BRAND_STOP_WORDS = {
    'near me', 'near you', 'home', 'homepage', 'welcome', 'official site', 'login',
    'contact us', 'about us', 'services', 'find a dentist', 'find a doctor',
    'compare 250+ practices', 'compare practices', 'reviews', 'ratings', 'open today',
    'best dentist near me', 'best clinic near me', 'affordable dentist', 'find a lawyer'
}

COMMON_LOCATIONS = {
    'koramangala', 'indiranagar', 'bandra', 'juhu', 'whitefield', 'gurgaon', 'noida',
    'bangalore', 'mumbai', 'delhi', 'hyderabad', 'chennai', 'pune', 'london', 'dubai',
    'new york', 'austin', 'central london', 'manchester', 'birmingham', 'chicago'
}

def format_domain_brand(domain: str) -> str:
    raw = domain.split('.')[0].lower()
    if raw.startswith('dr') and len(raw) >= 5:
        keywords = ['cosmetic', 'dermatology', 'dental', 'clinic', 'skin', 'care', 'health', 'aesthetics', 'surgery']
        rest = raw[2:]
        for kw in keywords:
            if kw in rest:
                rest = rest.replace(kw, f' {kw} ')
        parts = [p.capitalize() for p in rest.split() if p]
        return f"Dr. {' '.join(parts)}"
    return domain.split('.')[0].replace('-', ' ').replace('_', ' ').title()

def clean_company_brand_name(title: str, domain: str) -> str:
    """Strips SEO headlines and extracts the authentic brand name."""
    fallback_name = format_domain_brand(domain)
    if not title or title.lower().strip() in COMMON_LOCATIONS:
        return fallback_name

    cleaned = title.strip()
    # Strip phone numbers from titles
    cleaned = re.sub(r'(\+?\d[\d\s\-\(\)]{7,}\d)', '', cleaned)
    # Strip emojis and symbol clutter
    cleaned = re.sub(r'[\u2700-\u27bf\U0001f300-\U0001f9ff\u2600-\u26ff✦★☆•·~™®©]+', '', cleaned).strip()

    # Split on common separators: pipe, dash, bullet, colon, comma, slash
    parts = [p.strip() for p in re.split(r'[:|·•~,]|\s[-–—]\s', cleaned) if p.strip()]

    valid_parts = []
    for p in parts:
        p_clean = re.sub(r'^(?:Welcome to|Home|Home Page|Official Site)\s*[:-]?\s*', '', p, flags=re.IGNORECASE).strip()
        p_lower = p_clean.lower()
        if any(stop == p_lower or stop in p_lower for stop in GENERIC_BRAND_STOP_WORDS) or p_lower in COMMON_LOCATIONS:
            continue
        if len(re.sub(r'[^a-zA-Z]', '', p_clean)) < 3:
            continue
        valid_parts.append(p_clean)

    if not valid_parts:
        return fallback_name

    root_domain = domain.split('.')[0].replace('-', '').replace('_', '').lower()
    clean_parts = [(p, re.sub(r'[^a-zA-Z0-9]', '', p).lower()) for p in valid_parts]

    def finalize_name(s: str) -> str:
        s = re.sub(r'\s*\([^)]*$', '', s)
        s = re.sub(r'[\u2700-\u27bf\U0001f300-\U0001f9ff\u2600-\u26ff✦★☆•·~™®©]+', '', s).strip()
        return s.rstrip(' .,-_/:;|✦★☆([{')

    # 1. Match against domain name
    for p, p_sub in clean_parts:
        if p_sub == root_domain or (len(p_sub) >= 4 and p_sub in root_domain) or (len(root_domain) >= 4 and root_domain in p_sub):
            res = finalize_name(p)
            if res:
                return res

    # 2. Pick candidate that doesn't start with generic SEO prefixes
    candidates = [p for p in valid_parts if not any(p.lower().startswith(b) for b in ["best ", "top ", "welcome ", "#1 ", "find ", "cheap "])]
    if candidates:
        best = min(candidates, key=lambda c: abs(len(c.split()) - 3))
        res = finalize_name(best)
        if res:
            return res

    res = finalize_name(valid_parts[0])
    return res or fallback_name

def clean_lead_payload(raw_lead: dict) -> dict:
    """Normalizes all fields before database entry."""
    cleaned = dict(raw_lead)
    domain = cleaned.get("domain", "").strip().lower()

    # Clean brand name
    raw_name = cleaned.get("company_name", "")
    cleaned["company_name"] = clean_company_brand_name(raw_name, domain)
    cleaned["meta_description"] = clean_text(cleaned.get("meta_description", ""))
    cleaned["industry_niche"] = clean_text(cleaned.get("industry_niche", "")).title()
    cleaned["contact_name"] = clean_text(cleaned.get("contact_name", ""))
    cleaned["business_summary"] = clean_text(cleaned.get("business_summary", ""))
    cleaned["where_they_are_good"] = clean_text(cleaned.get("where_they_are_good", ""))
    cleaned["where_they_are_lacking"] = clean_text(cleaned.get("where_they_are_lacking", ""))

    # Clean emails with canonical sanitizer
    if isinstance(cleaned.get("emails"), (list, set)):
        cleaned_emails = []
        for e in cleaned["emails"]:
            e_clean = clean_email(str(e), domain)
            if e_clean:
                cleaned_emails.append(e_clean)
        cleaned["emails"] = sorted(list(dict.fromkeys(cleaned_emails)))

    # Clean phones with canonical sanitizer
    if isinstance(cleaned.get("phones"), (list, set)):
        cleaned_phones = []
        for p in cleaned["phones"]:
            p_clean = clean_phone(str(p))
            if p_clean:
                cleaned_phones.append(p_clean)
        cleaned["phones"] = sorted(list(dict.fromkeys(cleaned_phones)))

    if isinstance(cleaned.get("tech_stack"), (list, set)):
        cleaned["tech_stack"] = list(dict.fromkeys(filter(None, [t.strip() for t in cleaned["tech_stack"]])))

    return cleaned
