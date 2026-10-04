"""
Local Storage & Database Management (SQLite)
Handles persistence, fast indexing, deduplication, and 1-click CSV export.
"""
import sqlite3
import csv
import json
import os
from datetime import datetime
from config import DB_PATH, EXPORTS_DIR

def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        domain TEXT UNIQUE,
        company_name TEXT,
        website TEXT,
        emails TEXT,
        phones TEXT,
        linkedin_company TEXT,
        linkedin_profiles TEXT,
        twitter TEXT,
        instagram TEXT,
        facebook TEXT,
        github TEXT,
        country TEXT,
        city TEXT,
        industry_niche TEXT,
        tech_stack TEXT,
        meta_description TEXT,
        pitch_hook TEXT,
        service_match TEXT,
        opportunity_type TEXT,
        audit_notes TEXT,
        contact_name TEXT,
        business_summary TEXT,
        where_they_are_good TEXT,
        where_they_are_lacking TEXT,
        confident_pitch TEXT,
        lead_score TEXT DEFAULT 'HIGH',
        source TEXT,
        status TEXT DEFAULT 'New',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # Run safe column migrations for existing tables
    for col, col_type in [
        ("service_match", "TEXT"),
        ("opportunity_type", "TEXT"),
        ("audit_notes", "TEXT"),
        ("contact_name", "TEXT"),
        ("business_summary", "TEXT"),
        ("where_they_are_good", "TEXT"),
        ("where_they_are_lacking", "TEXT"),
        ("confident_pitch", "TEXT"),
        ("lead_score", "TEXT DEFAULT 'HIGH'")
    ]:
        try:
            cursor.execute(f"ALTER TABLE leads ADD COLUMN {col} {col_type};")
        except sqlite3.OperationalError:
            pass # Column already exists

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_domain ON leads(domain);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_country ON leads(country);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);")
    conn.commit()
    conn.close()

def save_or_update_lead(lead_data: dict) -> bool:
    """
    Saves lead or updates existing lead by domain.
    Returns True if newly inserted, False if updated.
    """
    domain = lead_data.get("domain", "").strip().lower()
    if not domain:
        return False

    conn = get_db()
    cursor = conn.cursor()

    # Convert list fields to comma-separated strings if needed
    for field in ["emails", "phones", "linkedin_profiles", "tech_stack"]:
        if isinstance(lead_data.get(field), list):
            lead_data[field] = ", ".join(filter(None, lead_data[field]))

    cursor.execute("SELECT id, emails, phones FROM leads WHERE domain = ?", (domain,))
    existing = cursor.fetchone()

    is_new = existing is None

    if is_new:
        cursor.execute("""
        INSERT INTO leads (
            domain, company_name, website, emails, phones,
            linkedin_company, linkedin_profiles, twitter, instagram, facebook, github,
            country, city, industry_niche, tech_stack, meta_description, pitch_hook,
            service_match, opportunity_type, audit_notes,
            contact_name, business_summary, where_they_are_good, where_they_are_lacking, confident_pitch,
            lead_score, source, status, created_at, updated_at
        ) VALUES (
            ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?, ?, ?,
            ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        )
        """, (
            domain,
            lead_data.get("company_name", ""),
            lead_data.get("website", ""),
            lead_data.get("emails", ""),
            lead_data.get("phones", ""),
            lead_data.get("linkedin_company", ""),
            lead_data.get("linkedin_profiles", ""),
            lead_data.get("twitter", ""),
            lead_data.get("instagram", ""),
            lead_data.get("facebook", ""),
            lead_data.get("github", ""),
            lead_data.get("country", ""),
            lead_data.get("city", ""),
            lead_data.get("industry_niche", ""),
            lead_data.get("tech_stack", ""),
            lead_data.get("meta_description", ""),
            lead_data.get("pitch_hook", ""),
            lead_data.get("service_match", "Web & Automation"),
            lead_data.get("opportunity_type", "General Digital Revamp"),
            lead_data.get("audit_notes", ""),
            lead_data.get("contact_name", ""),
            lead_data.get("business_summary", ""),
            lead_data.get("where_they_are_good", ""),
            lead_data.get("where_they_are_lacking", ""),
            lead_data.get("confident_pitch", ""),
            lead_data.get("lead_score", "HIGH"),
            lead_data.get("source", ""),
            lead_data.get("status", "New")
        ))
    else:
        # Merge new emails & phones with existing
        existing_emails = set(e.strip() for e in (existing["emails"] or "").split(",") if e.strip())
        new_emails = set(e.strip() for e in (lead_data.get("emails") or "").split(",") if e.strip())
        all_emails = ", ".join(sorted(existing_emails.union(new_emails)))

        existing_phones = set(p.strip() for p in (existing["phones"] or "").split(",") if p.strip())
        new_phones = set(p.strip() for p in (lead_data.get("phones") or "").split(",") if p.strip())
        all_phones = ", ".join(sorted(existing_phones.union(new_phones)))

        cursor.execute("""
        UPDATE leads SET
            company_name = COALESCE(NULLIF(?, ''), company_name),
            website = COALESCE(NULLIF(?, ''), website),
            emails = ?,
            phones = ?,
            linkedin_company = COALESCE(NULLIF(?, ''), linkedin_company),
            linkedin_profiles = COALESCE(NULLIF(?, ''), linkedin_profiles),
            twitter = COALESCE(NULLIF(?, ''), twitter),
            instagram = COALESCE(NULLIF(?, ''), instagram),
            facebook = COALESCE(NULLIF(?, ''), facebook),
            github = COALESCE(NULLIF(?, ''), github),
            country = COALESCE(NULLIF(?, ''), country),
            city = COALESCE(NULLIF(?, ''), city),
            industry_niche = COALESCE(NULLIF(?, ''), industry_niche),
            tech_stack = COALESCE(NULLIF(?, ''), tech_stack),
            meta_description = COALESCE(NULLIF(?, ''), meta_description),
            pitch_hook = COALESCE(NULLIF(?, ''), pitch_hook),
            service_match = COALESCE(NULLIF(?, ''), service_match),
            opportunity_type = COALESCE(NULLIF(?, ''), opportunity_type),
            audit_notes = COALESCE(NULLIF(?, ''), audit_notes),
            contact_name = COALESCE(NULLIF(?, ''), contact_name),
            business_summary = COALESCE(NULLIF(?, ''), business_summary),
            where_they_are_good = COALESCE(NULLIF(?, ''), where_they_are_good),
            where_they_are_lacking = COALESCE(NULLIF(?, ''), where_they_are_lacking),
            confident_pitch = COALESCE(NULLIF(?, ''), confident_pitch),
            lead_score = COALESCE(NULLIF(?, ''), lead_score),
            updated_at = CURRENT_TIMESTAMP
        WHERE domain = ?
        """, (
            lead_data.get("company_name", ""),
            lead_data.get("website", ""),
            all_emails,
            all_phones,
            lead_data.get("linkedin_company", ""),
            lead_data.get("linkedin_profiles", ""),
            lead_data.get("twitter", ""),
            lead_data.get("instagram", ""),
            lead_data.get("facebook", ""),
            lead_data.get("github", ""),
            lead_data.get("country", ""),
            lead_data.get("city", ""),
            lead_data.get("industry_niche", ""),
            lead_data.get("tech_stack", ""),
            lead_data.get("meta_description", ""),
            lead_data.get("pitch_hook", ""),
            lead_data.get("service_match", ""),
            lead_data.get("opportunity_type", ""),
            lead_data.get("audit_notes", ""),
            lead_data.get("contact_name", ""),
            lead_data.get("business_summary", ""),
            lead_data.get("where_they_are_good", ""),
            lead_data.get("where_they_are_lacking", ""),
            lead_data.get("confident_pitch", ""),
            lead_data.get("lead_score", ""),
            domain
        ))

    conn.commit()
    conn.close()
    return is_new

def get_leads(search="", country="", has_email=False, service_match="", status="", limit=100, offset=0):
    conn = get_db()
    cursor = conn.cursor()

    query = "SELECT * FROM leads WHERE 1=1"
    params = []

    if search:
        query += " AND (company_name LIKE ? OR domain LIKE ? OR meta_description LIKE ? OR industry_niche LIKE ? OR audit_notes LIKE ?)"
        s = f"%{search}%"
        params.extend([s, s, s, s, s])

    if country:
        query += " AND country LIKE ?"
        params.append(f"%{country}%")

    if service_match:
        query += " AND service_match LIKE ?"
        params.append(f"%{service_match}%")

    if has_email:
        query += " AND emails != '' AND emails IS NOT NULL"

    if status:
        query += " AND status = ?"
        params.append(status)

    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_lead_stats():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM leads")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM leads WHERE emails != '' AND emails IS NOT NULL")
    with_email = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM leads WHERE phones != '' AND phones IS NOT NULL")
    with_phone = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM leads WHERE linkedin_company != '' OR linkedin_profiles != ''")
    with_linkedin = cursor.fetchone()[0]

    cursor.execute("SELECT DISTINCT country FROM leads WHERE country != ''")
    countries = [r[0] for r in cursor.fetchall()]

    # Service breakdown counts
    service_counts = {}
    for svc in ["Chatbots", "Web Development", "App Development", "Automation", "Custom Pipelines"]:
        cursor.execute("SELECT COUNT(*) FROM leads WHERE service_match LIKE ?", (f"%{svc}%",))
        service_counts[svc] = cursor.fetchone()[0]

    conn.close()
    return {
        "total_leads": total,
        "with_email": with_email,
        "with_phone": with_phone,
        "with_linkedin": with_linkedin,
        "country_count": len(countries),
        "countries": countries[:10],
        "services": service_counts
    }

def delete_lead(lead_id: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM leads WHERE id = ?", (lead_id,))
    conn.commit()
    conn.close()

def update_lead_status(lead_id: int, status: str):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE leads SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (status, lead_id))
    conn.commit()
    conn.close()

def export_to_csv(filepath=None) -> str:
    """Exports all leads to a clean CSV ready for outreach or spreadsheet import."""
    if not filepath:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(EXPORTS_DIR, f"leads_export_{timestamp}.csv")

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT 
        company_name, contact_name, domain, website, service_match, opportunity_type,
        business_summary, where_they_are_good, where_they_are_lacking, confident_pitch,
        emails, phones, linkedin_company, linkedin_profiles, twitter, instagram,
        country, city, industry_niche, tech_stack, lead_score,
        audit_notes, source, status, created_at
    FROM leads ORDER BY id DESC
    """)
    rows = cursor.fetchall()
    headers = [d[0] for d in cursor.description]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(headers)
        for r in rows:
            writer.writerow(list(r))

    conn.close()
    return filepath

# Auto-initialize and migrate database on import
init_db()
