import re
from extractors.contact_miner import clean_email, clean_phone

def clean_text(text: str) -> str:
    """Removes weird encoding artifacts, excessive whitespace, and newlines."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def clean_company_brand_name(title: str, domain: str) -> str:
    """Strips SEO headlines and extracts the authentic brand name."""
    if not title:
        return domain.split('.')[0].replace('-', ' ').replace('_', ' ').title()

    cleaned = title.strip()
    parts = [p.strip() for p in re.split(r'[:|·•~]|\s[-–—]\s', cleaned) if p.strip()]
    root_domain = domain.split('.')[0].replace('-', '').replace('_', '').lower()
    clean_parts = [(p, re.sub(r'[^a-zA-Z0-9]', '', p).lower()) for p in parts]

    for p, p_sub in clean_parts:
        if (len(p_sub) >= 3 and p_sub in root_domain) or (len(root_domain) >= 4 and root_domain in p_sub):
            cleaned = p
            break
    else:
        candidates = [p for p in parts if not any(p.lower().startswith(b) for b in ["best ", "top ", "welcome ", "#1 ", "find "])]
        cleaned = min(candidates, key=len) if candidates else parts[0]

    cleaned = re.sub(r'^(?:Welcome to|Home|Home Page|Official Site)\s*[:-]?\s*', '', cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r'[\u2700-\u27bf\U0001f300-\U0001f9ff\u2600-\u26ff✦★☆•·~™®©]+', '', cleaned).strip()
    cleaned = cleaned.rstrip(' .,-_/:;|✦★☆')
    return cleaned or domain

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
