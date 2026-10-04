"""
Autonomous Business & Technical Opportunity Auditor
Performs in-depth analysis to answer 5 critical prospecting questions:
1. What does the business actually do?
2. Who is the decision maker / contact?
3. Where are they good? (Specific strengths to genuinely praise)
4. Where are they lacking? (Exact technical flaw: Chatbot, Web, App, Automation, Pipeline)
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
    "manager", "founder", "co-founder", "president", "partner", "member", "all"
}

def extract_decision_maker_name(soup: BeautifulSoup, text: str) -> str:
    """Extracts founder, CEO, or owner name from schema or page content."""
    # 1. Try JSON-LD Schema
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "{}")
            if isinstance(data, list):
                data = data[0] if data else {}

            for key in ["founder", "author", "creator"]:
                if key in data:
                    val = data[key]
                    if isinstance(val, dict) and "name" in val:
                        name_cand = val["name"]
                    elif isinstance(val, str):
                        name_cand = val
                    else:
                        continue
                    words = name_cand.lower().split()
                    if 1 <= len(words) <= 3 and not any(w in STOP_WORDS_AND_TITLES for w in words):
                        return name_cand.strip()
        except Exception:
            pass

    # 2. Text heuristics for Founders & Leadership (Case-sensitive names)
    founder_matches = re.findall(
        r'(?i:founded by|co-founder & ceo|founder & ceo|founder:?|ceo:?|co-founder:?)\s+([A-Z][a-z]{1,15}\s+[A-Z][a-z]{1,15})',
        text
    )
    for candidate in founder_matches:
        words = candidate.lower().split()
        if len(words) == 2 and not any(w in STOP_WORDS_AND_TITLES for w in words):
            if not any(w.endswith("ing") or w.endswith("tion") or w.endswith("ly") or w.endswith("ed") for w in words):
                return candidate.strip()

    return ""

def generate_business_summary(meta_desc: str, title: str, niche: str, tech_stack: list) -> str:
    """Creates a concise, plain-English summary of what the business actually does."""
    desc = meta_desc.strip()
    if desc and len(desc) > 20:
        # Take first sentence or up to 140 chars
        first_sentence = desc.split(".")[0].strip()
        if len(first_sentence) > 15:
            return first_sentence[:140]

    # Heuristic based on tech and niche
    techs = [t.lower() for t in tech_stack]
    if "shopify" in techs or "woocommerce" in techs:
        return f"E-commerce & Direct-to-Consumer brand operating in the {niche or 'retail'} market"
    if "agency" in (niche or "").lower():
        return f"Professional service agency specializing in {niche}"
    if "saas" in (niche or "").lower():
        return f"B2B software & technology platform"

    return f"Active digital business operating in {niche or 'commercial services'}"

def audit_business_for_services(html_content: str, soup: BeautifulSoup, company_name: str, tech_stack: list, niche: str) -> dict:
    """
    Performs full intelligence audit to determine:
    - business_summary
    - contact_name
    - where_they_are_good (strengths)
    - where_they_are_lacking (flaws)
    - confident_pitch (the outreach weapon)
    """
    lower_html = html_content.lower()
    text = soup.get_text()
    techs = [t.lower() for t in (tech_stack or [])]

    # Extract Decision Maker Name
    contact_name = extract_decision_maker_name(soup, text)
    if contact_name and len(contact_name.split()[0]) >= 2 and contact_name.split()[0].lower() not in STOP_WORDS_AND_TITLES:
        display_greeting = f"Hi {contact_name.split()[0]}"
    else:
        contact_name = ""
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

    # 2. What they are GOOD at (Strengths to praise)
    strengths = []
    if is_modern_web or "webflow" in techs:
        strengths.append("Sleek visual branding and modern UI typography")
    else:
        strengths.append("Clear product positioning and strong business offering")

    if has_socials:
        strengths.append("Active brand presence across digital social channels")

    if has_ecommerce:
        strengths.append("Structured digital product catalog with direct purchasing")
    elif len(soup.find_all("a")) > 15:
        strengths.append("Comprehensive content coverage explaining their services")

    where_they_are_good = " • ".join(strengths)

    # 3. What they are LACKING (Flaws to fix)
    weaknesses = []
    service_match = "Web Development"
    opportunity_type = "Web Performance Revamp"
    lead_score = "HIGH"

    # Priority A: Chatbot missing on customer-heavy or lead-heavy site
    if not has_chatbot and (has_ecommerce or "agency" in niche.lower() or "saas" in niche.lower() or "services" in lower_html or has_multiple_forms):
        service_match = "Chatbots"
        opportunity_type = "No 24/7 AI Chatbot (Visitor Lead Loss)"
        weaknesses.append("No automated 24/7 AI chatbot or live support; visitors leave without instant answers or lead capture")
        lead_score = "HOT"
        pitch_body = (
            f"noticed your website doesn't currently have an AI chatbot or 24/7 lead qualification widget. "
            f"Right now, high-intent visitors who browse after hours leave without getting answered. "
            f"I build automated conversational AI chatbots that answer customer FAQs, capture verified emails/phones, and book calls 24/7 without extra team overhead."
        )

    # Priority B: Mobile App missing on recurring platform / e-commerce
    elif not has_mobile_app and (has_ecommerce or "saas" in niche.lower() or "platform" in lower_html):
        service_match = "App Development"
        opportunity_type = "No iOS/Android Mobile App (Low Retention)"
        weaknesses.append("No native iOS App Store or Google Play apps; missing out on mobile push notifications & repeat customer loyalty")
        lead_score = "HOT"
        pitch_body = (
            f"saw the experience you've built on web. However, you don't currently have a native mobile app on iOS or Google Play. "
            f"For brands like yours, over 70% of traffic is mobile, and having a dedicated app drastically increases customer lifetime value with push notifications. "
            f"I develop cross-platform Flutter & React Native apps that sync directly with your web database."
        )

    # Priority C: Automation & Custom Pipeline Bottlenecks
    elif has_multiple_forms or has_ecommerce or "agency" in niche.lower():
        service_match = "Automation & Pipelines"
        opportunity_type = "Manual Lead & Data Workflows"
        weaknesses.append("Static lead capture forms with no automated instant WhatsApp/SMS response or CRM pipeline sync")
        pitch_body = (
            f"noticed your lead forms currently require manual follow-up. "
            f"I build automated data ingestion pipelines and business automations that instantly route leads into your CRM, send immediate WhatsApp/SMS confirmations, and sync catalogs automatically—saving 15+ hours of manual admin work weekly."
        )

    # Priority D: Web Development Upgrade
    elif is_legacy_web:
        service_match = "Web Development"
        opportunity_type = "Legacy Web Architecture & Speed Lag"
        weaknesses.append("Site runs on legacy CMS/jQuery plugins with script bloat; slower mobile load speeds and higher bounce rates")
        pitch_body = (
            f"noticed a few frontend performance bottlenecks on your mobile site that could be hurting Core Web Vitals and search rankings. "
            f"I modernize legacy websites into high-speed Next.js / React architectures with sub-second load times that convert more visitors into clients."
        )

    else:
        service_match = "Custom Pipelines & Web Dev"
        opportunity_type = "Full-Stack Integrations & Scale"
        weaknesses.append("Architecture lacks custom API integrations, real-time data sync, and high-performance microservices")
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
