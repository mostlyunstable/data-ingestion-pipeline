"""
Personalized Freelancer Pitch Generator
Analyzes company tech stack, location, and niche to craft tailored cold-outreach hooks.
"""

def generate_pitch_hook(company_name: str, tech_stack: list, niche: str, country: str, meta_desc: str) -> str:
    """Creates a custom, high-converting cold pitch opening tailored to the business."""
    name = company_name or "your team"
    techs = [t.lower() for t in (tech_stack or [])]

    # Hook based on Tech Stack
    if "shopify" in techs:
        return f"Hi {name} team! Noticed your store is powered by Shopify. As an e-commerce specialist, I help optimize mobile speed, build custom product sections, and increase conversions."

    if "webflow" in techs:
        return f"Hey {name}! Impressive setup on Webflow. I specialize in building custom interactive animations, CMS integrations, and high-performance landing pages for growing agencies."

    if "wordpress" in techs or "woocommerce" in techs:
        return f"Hello {name}! Saw your site runs on WordPress. I help businesses revamp UI/UX, boost core web vitals, and build custom workflow automations."

    if "next.js" in techs or "react" in techs:
        return f"Hi {name} team! Love the modern architecture with Next.js/React. As a freelance full-stack developer, I help engineering teams ship rapid frontend features and robust API integrations."

    # Hook based on Niche
    if "marketing" in niche.lower() or "agency" in niche.lower():
        return f"Hi {name}! As a freelancer supporting high-growth agencies, I can act as your on-demand technical/design partner to help deliver client projects faster without hiring full-time overhead."

    if "saas" in niche.lower() or "tech" in niche.lower() or "ai" in niche.lower():
        return f"Hey {name} team! Followed your work in {niche}. As a specialist freelancer, I help fast-moving startups build MVPs, optimize workflows, and scale user onboarding."

    # General High-Impact Outreach Hook
    if country == "India":
        return f"Namaste {name} team! I'm a developer & digital specialist based in India. I noticed what you're building and would love to support your upcoming product launches and client deliverables."

    return f"Hi {name}! Found your business while researching top {niche or 'businesses'}. I help brands streamline digital operations, upgrade their web presence, and execute high-priority freelance deliverables."
