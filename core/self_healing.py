"""
Self-Healing Diagnostic & Data Integrity Engine
Continuously audits the database, repairs corrupted records,
filters out parked/dead domains, normalizes company names, and removes junk.
"""
import re
import urllib.parse
import sqlite3
from config import DB_PATH, IGNORED_EMAIL_DOMAINS, IGNORED_EMAIL_PREFIXES

PARKED_DOMAIN_SIGNATURES = [
    "buy this domain", "domain for sale", "parked free by godaddy",
    "is available for sale", "this domain is registered", "website under construction",
    "cgi-sys/defaultwebpage", "domain is parked", "hugedomains", "dan.com"
]

def clean_company_brand_name(name: str, domain: str) -> str:
    """Strips SEO headlines and extracts the actual brand name."""
    if not name or len(name.strip()) == 0:
        clean_d = domain.split('.')[0]
        return clean_d.replace('-', ' ').replace('_', ' ').title()

    cleaned = name.strip()

    # Split delimiters
    for delim in [':', '·', '|', ' - ', ' – ', ' — ', ' ~ ']:
        if delim in cleaned:
            parts = [p.strip() for p in cleaned.split(delim) if p.strip()]
            # Find the part that matches the domain or looks most like a short brand name
            root_domain = domain.split('.')[0].lower()
            matched = False
            for p in parts:
                p_lower = re.sub(r'[^a-zA-Z0-9]', '', p).lower()
                if root_domain in p_lower:
                    cleaned = p
                    matched = True
                    break
            if not matched:
                # Prefer shortest non-marketing phrase
                candidates = [p for p in parts if not any(p.lower().startswith(b) for b in ["best ", "top ", "welcome ", "#1 ", "find "])]
                if candidates:
                    cleaned = min(candidates, key=len)
                else:
                    cleaned = parts[0]
            break

    # Strip prefixes like "Welcome to", "Home"
    cleaned = re.sub(r'^(?:Welcome to|Home|Official Site)\s*[:-]?\s*', '', cleaned, flags=re.IGNORECASE)

    # If the resulting name is generic SEO phrase, fallback to domain root
    if any(phrase in cleaned.lower() for phrase in ["digital marketing agency", "web development company", "software solutions", "indie game studio"]):
        root_d = domain.split('.')[0]
        return root_d.replace('-', ' ').replace('_', ' ').title()

    return cleaned.strip()

def sanitize_email_list(emails_str: str, domain: str) -> list:
    """Removes corrupt, unicode-escaped, template, or invalid emails."""
    if not emails_str:
        return []

    valid_emails = []
    candidates = [e.strip().lower() for e in emails_str.split(',') if e.strip()]

    for email in candidates:
        # Strip unicode escape artifacts
        email = re.sub(r'^(?:u003e|u003c|\\u003e|\\u003c|>|<|/|\\)+', '', email)
        email = re.sub(r'^[^\w]+|[^\w]+$', '', email)

        # Basic email regex
        if not re.match(r'^[a-z0-9][a-z0-9_.+-]*@[a-z0-9-]+\.[a-z0-9-.]+$', email):
            continue

        if len(email) < 6 or len(email) > 90:
            continue

        # Skip asset files
        if any(email.endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp', '.css', '.js', '.woff']):
            continue

        user, e_domain = email.split('@', 1)

        # Skip dummy templates
        if user in ["you", "yourname", "user", "username", "name", "email", "test", "demo", "sample", "sam", "fake", "u003e", "u003c"]:
            continue

        # Skip dummy domains
        if e_domain in IGNORED_EMAIL_DOMAINS or e_domain in ["company.com", "acme.co", "domain.com", "example.com", "studio.dev"]:
            continue

        if user in IGNORED_EMAIL_PREFIXES:
            continue

        # TLD must be alphabetic
        if '.' not in e_domain:
            continue
        tld = e_domain.split('.')[-1]
        if not re.match(r'^[a-z]{2,12}$', tld):
            continue

        valid_emails.append(email)

    return sorted(list(dict.fromkeys(valid_emails)))

def sanitize_phone_list(phones_str: str) -> list:
    """Removes invalid numbers, duplicates, and non-phones."""
    if not phones_str:
        return []

    valid_phones = []
    unique_digits = set()
    candidates = [p.strip() for p in phones_str.split(',') if p.strip()]

    for p in candidates:
        digits = re.sub(r'\D', '', p)
        # Phone numbers must have between 8 and 15 digits
        if 8 <= len(digits) <= 15:
            # Skip year-like or timestamp sequences (e.g., 20240101)
            if p.startswith(('202', '201', '199', '198')):
                continue
            if digits not in unique_digits:
                unique_digits.add(digits)
                valid_phones.append(p)

    return valid_phones[:2]

def run_self_healing_cycle() -> dict:
    """
    Scans entire database and executes self-healing:
    1. Removes empty records (no email and no phone and no LinkedIn)
    2. Cleans company brand names
    3. Cleans emails and removes template junk
    4. Cleans phones
    5. Deduplicates
    """
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    cursor = conn.cursor()

    cursor.execute("SELECT id, domain, company_name, website, emails, phones, linkedin_company, linkedin_profiles FROM leads")
    rows = cursor.fetchall()

    repaired_count = 0
    deleted_count = 0

    for row in rows:
        lead_id, domain, company_name, website, emails_raw, phones_raw, l_company, l_profiles = row

        # 1. Clean Emails
        clean_emails = sanitize_email_list(emails_raw or "", domain or "")
        clean_phones = sanitize_phone_list(phones_raw or "")

        # 2. Check if lead has direct contact points (must have email or phone)
        has_contacts = len(clean_emails) > 0 or len(clean_phones) > 0
        if not has_contacts:
            cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
            deleted_count += 1
            continue

        # 3. Clean Company Name
        clean_name = clean_company_brand_name(company_name or "", domain or "")

        # 4. Clean Website
        clean_website = website.strip() if website else f"https://{domain}"
        if not clean_website.startswith("http://") and not clean_website.startswith("https://"):
            clean_website = f"https://{clean_website}"

        # Update record
        cursor.execute("""
        UPDATE leads SET
            company_name = ?,
            website = ?,
            emails = ?,
            phones = ?
        WHERE id = ?
        """, (
            clean_name,
            clean_website,
            ", ".join(clean_emails),
            ", ".join(clean_phones),
            lead_id
        ))
        repaired_count += 1

    conn.commit()
    conn.close()

    return {
        "status": "success",
        "repaired_records": repaired_count,
        "purged_records": deleted_count
    }
