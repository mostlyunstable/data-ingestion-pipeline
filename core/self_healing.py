import re
import sqlite3
from config import DB_PATH
from transformers.cleaner import clean_company_brand_name
from extractors.contact_miner import clean_email, clean_phone

from transformers.opportunity_auditor import STOP_WORDS_AND_TITLES, infer_name_from_email, is_valid_name

from extractors.search_radar import SKIP_DOMAINS, clean_target_domain

def sanitize_email_list(emails_str: str, domain: str) -> list:
    """Uses canonical email cleaner to filter list (fast regex/string sanitation without repeat DNS MX calls)."""
    if not emails_str:
        return []
    clean_emails = []
    for e in emails_str.split(','):
        c = clean_email(e.strip(), domain, check_mx=False)
        if c:
            clean_emails.append(c)
    return sorted(list(dict.fromkeys(clean_emails)))

def sanitize_phone_list(phones_str: str) -> list:
    """Uses canonical phone cleaner to filter list."""
    if not phones_str:
        return []
    clean_phones = []
    for p in phones_str.split(','):
        c = clean_phone(p.strip())
        if c:
            clean_phones.append(c)
    return sorted(list(dict.fromkeys(clean_phones)))[:2]

def run_self_healing_cycle() -> dict:
    """
    Scans entire database and executes self-healing:
    1. Removes blacklisted non-business / news / media / hobby domains
    2. Removes empty records lacking verified email or phone
    3. Cleans company brand names
    4. Cleans emails and removes template junk or error tracking tokens
    5. Cleans phones and strips truncated numbers
    6. Purifies contact decision-maker names and greetings
    7. Repairs outreach pitches to match cleaned brand names
    """
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, domain, company_name, website, emails, phones,
           confident_pitch, pitch_hook, contact_name,
           country, city, meta_description
    FROM leads
    """)
    rows = cursor.fetchall()

    repaired_count = 0
    deleted_count = 0

    for row in rows:
        (
            lead_id, domain, company_name, website, emails_raw, phones_raw,
            pitch, hook, contact_raw, l_country, l_city, l_desc
        ) = row

        # 0. Check if domain is qualified commercial prospect
        if not clean_target_domain(f"https://{domain}"):
            cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
            deleted_count += 1
            continue

        # Check for spam, gambling, satta matka, or news publisher keywords
        c_lower = (company_name or "").lower()
        d_lower = (domain or "").lower()
        if any(spam in c_lower or spam in d_lower for spam in [
            "satta", "matka", "dpboss", "kalyan", "bazar", "bazaar", "result",
            "gambling", "lottery", "betting", "pedia", "freepress", "newslaundry",
            "medicalnewstoday", "iadvl.org", "editorial", "journal"
        ]):
            cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
            deleted_count += 1
            continue

        # 1. Clean Emails & Phones
        clean_emails = sanitize_email_list(emails_raw or "", domain or "")
        clean_phones = sanitize_phone_list(phones_raw or "")

        # 2. Check if lead has direct contact points (must have verified email or phone)
        if not (clean_emails or clean_phones):
            cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
            deleted_count += 1
            continue

        # 3. Clean Company Name
        clean_name = clean_company_brand_name(company_name or "", domain or "")
        if not clean_name or len(clean_name) < 2:
            cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
            deleted_count += 1
            continue

        # 4. Indian Commercial Client Verification Gate (Purges international/non-Indian leads)
        l_country_str = l_country or ""
        l_city_str = l_city or ""
        l_desc_str = l_desc or ""

        phones_str = " ".join(clean_phones)
        is_indian = (
            l_country_str == "India" or
            "+91" in phones_str or
            domain.endswith(".in") or
            domain.endswith(".co.in") or
            any(k in (l_city_str + " " + l_desc_str).lower() for k in [
                "bangalore", "bengaluru", "mumbai", "delhi", "gurgaon", "gurugram", "noida",
                "hyderabad", "pune", "chennai", "kolkata", "ahmedabad", "jaipur", "kochi",
                "chandigarh", "indore", "surat", "lucknow", "coimbatore", "goa", "india"
            ])
        )
        if not is_indian:
            cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
            deleted_count += 1
            continue

        # 5. Clean Contact Decision Maker Name & Infer from email
        clean_contact = (contact_raw or "").strip()
        if clean_contact and not is_valid_name(clean_contact, domain or ""):
            clean_contact = ""

        if not clean_contact and clean_emails:
            clean_contact = infer_name_from_email(clean_emails, domain or "")
            if not is_valid_name(clean_contact, domain or ""):
                clean_contact = ""

        # 6. Clean Website
        clean_website = website.strip() if website else f"https://{domain}"
        if not clean_website.startswith("http://") and not clean_website.startswith("https://"):
            clean_website = f"https://{clean_website}"

        # 7. Repair Pitch & Hook greetings
        clean_pitch = pitch or ""
        clean_hook = hook or ""

        if clean_contact:
            if clean_contact.startswith("Dr."):
                greeting = f"Hi {clean_contact}"
            else:
                greeting = f"Hi {clean_contact.split()[0]}"
        else:
            greeting = f"Hi {clean_name} team"

        if clean_pitch:
            clean_pitch = re.sub(r'^(?:Hi|Hello|Hey)\s+[^!\n]+[!\n]\s*', f'{greeting}! ', clean_pitch)
            clean_pitch = re.sub(r'(Love what you\'re doing with\s+).*?(—especially)', rf'\g<1>{clean_name}\g<2>', clean_pitch)
        if clean_hook:
            clean_hook = re.sub(r'^(?:Hi|Hello|Hey)\s+[^!\n]+[!\n]\s*', f'{greeting}! ', clean_hook)
            clean_hook = re.sub(r'(Love what you\'re doing with\s+).*?(—especially)', rf'\g<1>{clean_name}\g<2>', clean_hook)

        # Update record (including verified country = 'India' in single statement)
        cursor.execute("""
        UPDATE leads SET
            company_name = ?,
            website = ?,
            emails = ?,
            phones = ?,
            country = 'India',
            contact_name = ?,
            confident_pitch = ?,
            pitch_hook = ?
        WHERE id = ?
        """, (
            clean_name,
            clean_website,
            ", ".join(clean_emails),
            ", ".join(clean_phones),
            clean_contact,
            clean_pitch,
            clean_hook,
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
