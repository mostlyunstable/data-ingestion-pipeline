"""
Autonomous Business & Technical Opportunity Auditor
Performs in-depth analysis to answer 5 critical prospecting questions:
1. What does the business actually do?
2. Who is the decision maker / contact? (Doctors, Founders, Managing Partners, Inferred Names)
3. Where are they good? (Specific strengths to genuinely praise)
4. Where are they lacking? (Exact technical flaw: 24/7 WhatsApp AI Bot, Web Speed, Mobile App, Lead Automation)
5. The Confident Outreach Pitch (Ready to send via Gmail, Text, or WhatsApp)
"""
import re
import json
from bs4 import BeautifulSoup

KNOWN_CHATBOT_SIGNATURES = [
    "intercom", "crisp.chat", "drift.com", "tidio", "zendesk", "livechat",
    "freshchat", "chatra", "tawk.to", "hubspot-messages", "manychat", "chatbase", "botpress", "voiceflow"
]

APP_STORE_SIGNATURES = [
    "apps.apple.com", "play.google.com", "itunes.apple.com"
]

STOP_WORDS_AND_TITLES = {
    "the", "our", "best", "about", "team", "digital", "agency", "company", "media",
    "solutions", "insightful", "imparting", "services", "technologies", "studios",
    "and", "or", "in", "at", "for", "with", "is", "of", "to", "a", "an", "as",
    "cmo", "ceo", "cto", "coo", "cfo", "cio", "cro", "vp", "head", "lead", "director",
    "manager", "founder", "co-founder", "president", "partner", "member", "all",
    "dr", "doctor", "dentist", "clinic", "hospital", "office", "care", "consultant",
    "chief", "report", "associate", "officer", "executive", "advisor", "caffeine",
    "staff", "inquiry", "support", "sales", "general", "export", "exports", "import", "imports",
    "order", "orders", "shipping", "finance", "accounts", "warehouse", "store", "customercare",
    "llp", "pvt", "ltd", "corp", "inc", "gifting", "gift", "wholesale", "retail", "franchise"
}

COMMON_LOCATIONS = {
    "beograd", "belgrade", "delhi", "mumbai", "bangalore", "london", "dubai",
    "paris", "berlin", "tokyo", "beijing", "shanghai", "new york", "austin",
    "chicago", "san francisco", "toronto", "sydney", "central london", "koramangala",
    "indiranagar", "bandra", "juhu", "whitefield", "gurgaon", "noida"
}

def is_valid_name(cand: str, domain: str = "") -> bool:
    """Validates that a string is a genuine human name and not a title, role, city, or domain fragment."""
    if not cand or len(cand) < 3:
        return False
    domain_root = domain.split('.')[0].replace('-', '').replace('_', '').lower() if domain else ''
    clean_c = re.sub(r'[^a-zA-Z0-9]', '', cand).lower()
    if domain_root and (clean_c in domain_root or domain_root in clean_c or any(corp in clean_c for corp in ['llp', 'pvt', 'ltd', 'corp', 'inc'])):
        return False
    words = cand.lower().split()
    if any(w in STOP_WORDS_AND_TITLES or w in MEDICAL_CLINIC_STOP_WORDS or w in COMMON_LOCATIONS for w in words):
        return False
    return True

MEDICAL_CLINIC_STOP_WORDS = {
    "skin", "clinic", "clinics", "dental", "dentist", "dentists", "hospital", "hospitals",
    "care", "healthcare", "appointment", "appointments", "treatment", "treatments",
    "center", "centre", "cosmetic", "aesthetics", "aesthetic", "surgery", "surgeon",
    "specialist", "specialists", "laser", "hair", "derma", "dermatology", "smile", "smiles",
    "team", "office", "service", "services", "patient", "patients", "medical", "medicine",
    "wellness", "facial", "face", "body", "beauty", "teeth", "implants", "orthodontic", "orthodontics",
    "dermatologist", "consultant", "practitioner", "pediatric", "general", "lead", "head", "principal", "associate"
}

GENERIC_EMAIL_PREFIXES = {
    "info", "contact", "support", "admin", "sales", "care", "reception", "office",
    "hello", "help", "enquiries", "enquiry", "team", "booking", "appointments",
    "billing", "legal", "service", "services", "mail", "feedback", "pm", "dental",
    "frontdesk", "desk", "general", "press", "media", "jobs", "careers", "hr",
    "channel", "connect", "editor", "partnerships", "partnership", "collaborations",
    "newbusiness", "business", "projects", "trainings", "training", "corporate",
    "africa", "india", "japan", "qatar", "dubai", "london", "uk", "usa", "global",
    "gloucester", "goodge", "jubao", "cdoedge", "squawk", "logos", "report", "partner",
    "chief", "officer", "manager", "associate", "inbox", "compliance", "privacy",
    "investor", "investors", "relations", "export", "exports", "import", "imports",
    "order", "orders", "shipping", "finance", "accounts", "warehouse", "store",
    "customercare", "gifting", "gift", "wholesale", "retail", "franchise"
}

def infer_name_from_email(emails: list, domain: str = "") -> str:
    """Infers human decision maker name from validated personal email usernames."""
    if not emails:
        return ""
    domain_root = domain.split('.')[0].replace('-', '').replace('_', '').lower() if domain else ''

    for email in emails:
        if not email or '@' not in email:
            continue
        user = email.split('@')[0].lower()
        if user in GENERIC_EMAIL_PREFIXES:
            continue
        clean_u = re.sub(r'[^a-zA-Z0-9]', '', user)
        if domain_root and (clean_u in domain_root or domain_root in clean_u or any(corp in clean_u for corp in ['llp', 'pvt', 'ltd', 'corp', 'inc'])):
            continue
        if any(stop in user for stop in MEDICAL_CLINIC_STOP_WORDS):
            continue

        # Check Dr prefix in email username (e.g. drkothiwala@..., drdixit@...)
        if user.startswith('dr.') or user.startswith('dr_'):
            surname = user[3:].title()
            if surname.isalpha() and len(surname) >= 3:
                return f"Dr. {surname}"
        elif user.startswith('dr') and len(user) >= 5 and user[2:].isalpha():
            surname = user[2:].title()
            return f"Dr. {surname}"
        elif '.' in user:
            parts = user.split('.')
            if len(parts) == 2 and all(p.isalpha() and len(p) >= 2 for p in parts) and parts[0] not in GENERIC_EMAIL_PREFIXES:
                return f"{parts[0].title()} {parts[1].title()}"
        elif '_' in user:
            parts = user.split('_')
            if len(parts) == 2 and all(p.isalpha() and len(p) >= 2 for p in parts) and parts[0] not in GENERIC_EMAIL_PREFIXES:
                return f"{parts[0].title()} {parts[1].title()}"
        elif user.isalpha() and 3 <= len(user) <= 12 and user not in GENERIC_EMAIL_PREFIXES:
            return user.title()

    return ""

def extract_decision_maker_name(soup: BeautifulSoup, text: str, emails: list = None, domain: str = "") -> str:
    """Extracts doctor, founder, partner, or owner name from text, schema, or emails."""
    # 1. Doctor & Medical Specialist Names (Private clinics, dental, aesthetics)
    dr_matches = re.findall(r'\b(?:Dr\.|Doctor)[ \t]+([A-Z][a-z]{2,15}(?:[ \t]+[A-Z][a-z]{2,15}){1,2})', text)
    for cand in dr_matches:
        if is_valid_name(cand, domain):
            return f"Dr. {cand.strip()}"

    # 2. Leadership, Founders, and Principal Partners
    leader_matches = re.findall(
        r'(?i:\b(?:Principal Dentist|Clinical Director|Medical Director|Lead Dermatologist|Lead Consultant|Managing Partner|Senior Partner|Founder & CEO|Founder|Co-Founder|Creative Director|Principal Architect)\s*[:\-–]?\s*(?:(?:Dr\.|Doctor|Mr\.|Ms\.|Mrs\.)\s+)?([A-Z][a-z]{2,15}\s+[A-Z][a-z]{2,15}))',
        text
    )
    for candidate in leader_matches:
        words = candidate.lower().split()
        if len(words) == 2 and is_valid_name(candidate, domain):
            return candidate.strip()

    # 3. JSON-LD Schema
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
            items = data if isinstance(data, list) else [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                # Direct Person / Physician / Dentist
                if item.get("@type") in ["Person", "Physician", "Dentist"]:
                    if "name" in item and isinstance(item["name"], str):
                        words = item["name"].lower().split()
                        if 1 <= len(words) <= 3 and is_valid_name(item["name"], domain):
                            return item["name"].strip()
                # Subfields on Organization / MedicalBusiness
                for key in ["founder", "author", "creator", "employee", "physician"]:
                    if key in item:
                        val = item[key]
                        if isinstance(val, dict) and "name" in val:
                            name_cand = val["name"]
                        elif isinstance(val, str):
                            name_cand = val
                        else:
                            continue
                        words = name_cand.lower().split()
                        if 1 <= len(words) <= 3 and is_valid_name(name_cand, domain):
                            return name_cand.strip()
        except Exception:
            pass

    # 4. Verified Personal Email Username Inference Fallback
    if emails:
        inferred = infer_name_from_email(emails, domain)
        if inferred and is_valid_name(inferred, domain):
            return inferred

    return ""

def generate_business_summary(meta_desc: str, title: str, niche: str, tech_stack: list) -> str:
    """Creates a concise, plain-English summary of what the business actually does."""
    desc = meta_desc.strip()
    if desc and len(desc) > 20:
        first_sentence = desc.split(".")[0].strip()
        if len(first_sentence) > 15:
            return first_sentence[:140]

    techs = [t.lower() for t in tech_stack]
    if "shopify" in techs or "woocommerce" in techs:
        return f"Independent e-commerce & retail brand operating in {niche or 'lifestyle'}"
    if any(k in (niche or "").lower() for k in ["clinic", "dental", "dermatology", "aesthetic"]):
        return f"Private healthcare & clinical practice specializing in {niche}"
    if any(k in (niche or "").lower() for k in ["law", "visa", "immigration", "consulting"]):
        return f"Boutique advisory consultancy specializing in {niche}"

    return f"Active commercial enterprise operating in {niche or 'professional services'}"

def audit_business_for_services(
    html_content: str,
    soup: BeautifulSoup,
    company_name: str,
    tech_stack: list,
    niche: str,
    combined_text: str = "",
    emails: list = None,
    domain: str = ""
) -> dict:
    """
    Performs full intelligence audit to determine:
    - business_summary
    - contact_name
    - where_they_are_good (strengths)
    - where_they_are_lacking (flaws)
    - confident_pitch (the outreach weapon)
    """
    lower_html = html_content.lower()
    full_text = (soup.get_text() + " " + (combined_text or "")).strip()
    techs = [t.lower() for t in (tech_stack or [])]

    # Extract Decision Maker Name
    contact_name = extract_decision_maker_name(soup, full_text, emails=emails, domain=domain)
    domain_root = domain.split('.')[0].replace('-', '').replace('_', '').lower() if domain else ''
    if contact_name and (contact_name.lower() == company_name.lower() or contact_name.lower() == domain_root):
        contact_name = ""

    if contact_name:
        if contact_name.startswith("Dr."):
            display_greeting = f"Hi {contact_name}"
        else:
            display_greeting = f"Hi {contact_name.split()[0]}"
    else:
        display_greeting = f"Hi {company_name} team"

    # Meta description
    meta_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
    meta_desc = meta_tag.get("content", "") if meta_tag else ""
    business_summary = generate_business_summary(meta_desc, company_name, niche, tech_stack)

    # 1. Technical Audit Findings
    has_chatbot = any(sig in lower_html for sig in KNOWN_CHATBOT_SIGNATURES)
    has_mobile_app = any(sig in lower_html for sig in APP_STORE_SIGNATURES)
    has_ecommerce = any(t in techs for t in ["shopify", "woocommerce", "magento"])
    is_legacy_web = any(t in techs for t in ["wordpress", "wix", "squarespace", "magento"]) or ("jquery" in lower_html and "next.js" not in techs)
    is_modern_web = any(t in techs for t in ["next.js", "react", "vue.js", "webflow", "tailwind css"])
    has_multiple_forms = len(soup.find_all("form")) >= 2
    has_socials = any(s in lower_html for s in ["instagram.com", "linkedin.com", "twitter.com", "x.com"])

    is_high_ticket_practice = any(k in (niche or "").lower() for k in [
        "clinic", "dental", "dermatology", "aesthetic", "doctor", "cosmetic",
        "law", "visa", "immigration", "real estate", "interior", "architecture"
    ])

    # 2. What they are GOOD at (Strengths to praise)
    strengths = []
    if is_modern_web or "webflow" in techs:
        strengths.append("Sleek visual branding and modern UI typography")
    elif is_high_ticket_practice:
        strengths.append("Comprehensive treatment portfolio and strong local reputation")
    else:
        strengths.append("Clear service positioning and strong digital presence")

    if has_socials:
        strengths.append("Active patient & client engagement across digital channels")

    if has_ecommerce:
        strengths.append("Structured digital catalog with streamlined purchasing")
    elif len(soup.find_all("a")) > 15:
        strengths.append("Detailed educational content explaining their procedures")

    where_they_are_good = " • ".join(strengths)

    # 3. What they are LACKING (Flaws to fix)
    weaknesses = []
    service_match = "Chatbots"
    opportunity_type = "No 24/7 AI WhatsApp Booking Bot"
    lead_score = "HOT"

    # Priority 1: High-Ticket Clinic / Practice / Consultancy without Chatbot
    # (High urgency: they lose 40% of patient inquiries after 7 PM)
    if not has_chatbot and (is_high_ticket_practice or has_ecommerce or has_multiple_forms or "booking" in lower_html or "appointment" in lower_html):
        service_match = "Chatbots"
        opportunity_type = "No 24/7 AI WhatsApp Booking Bot (Visitor Lead Loss)"
        weaknesses.append("No automated 24/7 AI WhatsApp booking assistant; visitors and patients browsing after hours leave without instant slot confirmation")
        lead_score = "HOT"
        pitch_body = (
            f"noticed your website doesn't currently have a 24/7 AI WhatsApp booking assistant. "
            f"In {niche.lower() if niche else 'private practice'}, over 40% of prospective clients browse on mobile after hours (7 PM–midnight) and leave without booking if they can't get instant slot confirmation. "
            f"I build automated 24/7 AI WhatsApp booking bots that answer patient procedure FAQs, qualify inquiries, and directly lock in consultation appointments into your calendar without extra front-desk overhead."
        )

    # Priority 2: Legacy Web / Outdated Tech Stack (Speed lag & bounce rate)
    elif is_legacy_web:
        service_match = "Web Development"
        opportunity_type = "Legacy Web Architecture & Speed Lag"
        weaknesses.append("Site runs on legacy CMS/jQuery plugins with script bloat; slower mobile load speeds and higher bounce rates")
        lead_score = "HOT"
        pitch_body = (
            f"noticed a few frontend performance bottlenecks on your mobile site that could be hurting Core Web Vitals and search rankings. "
            f"I modernize legacy websites into high-speed Next.js / React architectures with sub-second load times that give prospective clients a premium experience and convert more visitors into booked consultations."
        )

    # Priority 3: Independent E-Commerce / Shopify without mobile app
    elif not has_mobile_app and (has_ecommerce or "retail" in niche.lower() or "store" in lower_html):
        service_match = "App Development"
        opportunity_type = "No iOS/Android Mobile App (Low Retention)"
        weaknesses.append("No native iOS App Store or Google Play apps; missing out on mobile push notifications & repeat customer loyalty")
        lead_score = "HOT"
        pitch_body = (
            f"saw the brand experience you've built on web. However, you don't currently have a native mobile app on iOS or Google Play. "
            f"For brands in your space, over 70% of transactions happen on mobile, and having a dedicated app drastically increases repeat customer retention via push notifications. "
            f"I develop cross-platform Flutter & React Native apps that sync directly with your web catalog."
        )

    # Priority 4: Lead-heavy consultancies / agencies with manual forms
    elif has_multiple_forms or "agency" in niche.lower() or "consult" in niche.lower():
        service_match = "Automation"
        opportunity_type = "Manual Lead Intake & Delayed Follow-up"
        weaknesses.append("Static lead capture forms with no automated instant WhatsApp/SMS confirmation or CRM pipeline sync")
        lead_score = "HIGH"
        pitch_body = (
            f"noticed your consultation inquiry forms currently require manual staff follow-up. "
            f"I build automated lead qualification pipelines that instantly route inbound inquiries into your CRM, fire immediate WhatsApp confirmations to the client, and notify your team in real time—cutting lead response time from hours to under 60 seconds."
        )

    else:
        service_match = "Custom Pipelines"
        opportunity_type = "Full-Stack Integrations & Scale"
        weaknesses.append("Architecture lacks custom API integrations, real-time data sync, and high-performance microservices")
        lead_score = "HIGH"
        pitch_body = (
            f"as a full-stack engineer specializing in custom data pipelines and modern web engineering, "
            f"I help teams build bespoke backend integrations, automated scrapers, and frontend feature modules on-demand without hiring full-time overhead."
        )

    where_they_are_lacking = " • ".join(weaknesses)

    # 4. Confident Outreach Pitch (Praise + Specific Flaw + Fix)
    praise_point = strengths[0].lower() if strengths else "your work online"
    confident_pitch = (
        f"{display_greeting}! Love what you're doing with {company_name}—especially {praise_point}.\n\n"
        f"I was doing a quick technical audit of your digital infrastructure and {pitch_body}\n\n"
        f"I put together a couple of quick ideas on how we can implement this in a few days. "
        f"Would you be open to a 2-minute video walkthrough or a quick chat this week?"
    )

    return {
        "service_match": service_match,
        "opportunity_type": opportunity_type,
        "audit_notes": where_they_are_lacking,
        "contact_name": contact_name,
        "business_summary": business_summary,
        "where_they_are_good": where_they_are_good,
        "where_they_are_lacking": where_they_are_lacking,
        "lead_score": lead_score,
        "confident_pitch": confident_pitch,
        "pitch_hook": confident_pitch
    }
