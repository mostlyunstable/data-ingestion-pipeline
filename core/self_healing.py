import re
import sqlite3
from config import DB_PATH
from transformers.cleaner import clean_company_brand_name
from extractors.contact_miner import clean_email, clean_phone

from transformers.opportunity_auditor import STOP_WORDS_AND_TITLES

def sanitize_email_list(emails_str: str, domain: str) -> list:
    """Uses canonical email cleaner to filter list."""
    if not emails_str:
        return []
    clean_emails = []
    for e in emails_str.split(','):
        c = clean_email(e.strip(), domain)
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
    1. Removes empty records lacking verified email or phone
    2. Cleans company brand names
    3. Cleans emails and removes template junk
    4. Cleans phones and strips truncated numbers
    5. Purifies contact decision-maker names and greetings
    6. Repairs outreach pitches to match cleaned brand names
    """
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, domain, company_name, website, emails, phones,
           confident_pitch, pitch_hook, contact_name
    FROM leads
    """)
    rows = cursor.fetchall()

    repaired_count = 0
    deleted_count = 0

    for row in rows:
        lead_id, domain, company_name, website, emails_raw, phones_raw, pitch, hook, contact_raw = row

        # 1. Clean Emails & Phones
        clean_emails = sanitize_email_list(emails_raw or "", domain or "")
        clean_phones = sanitize_phone_list(phones_raw or "")

        # 2. Check if lead has direct contact points (must have email or phone)
        if not (clean_emails or clean_phones):
            cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
            deleted_count += 1
            continue

        # 3. Clean Company Name
        clean_name = clean_company_brand_name(company_name or "", domain or "")

        # 4. Clean Contact Decision Maker Name
        clean_contact = (contact_raw or "").strip()
        if clean_contact:
            words = clean_contact.lower().split()
            if any(w in STOP_WORDS_AND_TITLES for w in words) or len(words) > 3 or len(words) == 0:
                clean_contact = ""

        # 5. Clean Website
        clean_website = website.strip() if website else f"https://{domain}"
        if not clean_website.startswith("http://") and not clean_website.startswith("https://"):
            clean_website = f"https://{clean_website}"

        # 6. Repair Pitch & Hook greetings
        clean_pitch = pitch or ""
        clean_hook = hook or ""
        if clean_name:
            if clean_pitch:
                clean_pitch = re.sub(r'^(Hi\s+).*?(\s+team!)', rf'\g<1>{clean_name}\g<2>', clean_pitch)
                clean_pitch = re.sub(r'(Love what you\'re doing with\s+).*?(—especially)', rf'\g<1>{clean_name}\g<2>', clean_pitch)
                clean_pitch = re.sub(r'^Hi\s+(?:and|the|our|best|a|an)!\s*', f'Hi {clean_name} team! ', clean_pitch)
            if clean_hook:
                clean_hook = re.sub(r'^(Hi\s+).*?(\s+team!)', rf'\g<1>{clean_name}\g<2>', clean_hook)
                clean_hook = re.sub(r'(Love what you\'re doing with\s+).*?(—especially)', rf'\g<1>{clean_name}\g<2>', clean_hook)
                clean_hook = re.sub(r'^Hi\s+(?:and|the|our|best|a|an)!\s*', f'Hi {clean_name} team! ', clean_hook)

        # Update record
        cursor.execute("""
        UPDATE leads SET
            company_name = ?,
            website = ?,
            emails = ?,
            phones = ?,
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
