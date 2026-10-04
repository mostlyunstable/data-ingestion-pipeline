"""
Data Cleaner & Normalizer
Ensures all extracted fields are formatted, standardized, and free from junk.
"""
import re

def clean_text(text: str) -> str:
    """Removes weird encoding artifacts, excessive whitespace, and newlines."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def clean_lead_payload(raw_lead: dict) -> dict:
    """Normalizes all fields before database entry."""
    cleaned = dict(raw_lead)

    cleaned["company_name"] = clean_text(cleaned.get("company_name", ""))
    cleaned["meta_description"] = clean_text(cleaned.get("meta_description", ""))
    cleaned["industry_niche"] = clean_text(cleaned.get("industry_niche", "")).title()
    cleaned["contact_name"] = clean_text(cleaned.get("contact_name", ""))
    cleaned["business_summary"] = clean_text(cleaned.get("business_summary", ""))
    cleaned["where_they_are_good"] = clean_text(cleaned.get("where_they_are_good", ""))
    cleaned["where_they_are_lacking"] = clean_text(cleaned.get("where_they_are_lacking", ""))

    # Format lists
    if isinstance(cleaned.get("emails"), list):
        cleaned_emails = []
        for e in cleaned["emails"]:
            e_clean = e.lower().strip()
            if e_clean and not any(e_clean.startswith(p) for p in ["you@", "test@", "demo@", "sample@", "dummy@", "user@", "username@", "john@", "jane@"]):
                cleaned_emails.append(e_clean)
        cleaned["emails"] = list(dict.fromkeys(cleaned_emails))

    if isinstance(cleaned.get("phones"), list):
        cleaned["phones"] = list(dict.fromkeys(filter(None, [p.strip() for p in cleaned["phones"]])))
    if isinstance(cleaned.get("tech_stack"), list):
        cleaned["tech_stack"] = list(dict.fromkeys(filter(None, [t.strip() for t in cleaned["tech_stack"]])))

    return cleaned
