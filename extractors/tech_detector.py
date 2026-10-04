"""
Tech Stack & Platform Detector
Identifies CMS, Frontend Frameworks, and Tools used by the target business.
Provides freelancers with concrete technical hooks for outreach.
"""
from bs4 import BeautifulSoup

TECH_SIGNATURES = {
    # CMS / E-commerce Platforms
    "Shopify": ["cdn.shopify.com", "myshopify.com", "shopify-features"],
    "WordPress": ["wp-content", "wp-includes", "wordpress"],
    "WooCommerce": ["woocommerce", "wc-blocks"],
    "Webflow": ["assets.webflow.com", "webflow.js", "w-nav"],
    "Squarespace": ["squarespace.com", "static1.squarespace.com"],
    "Wix": ["wix.com", "wix-code"],
    "Magento": ["mage/cookies", "static/_requirejs"],
    "Ghost": ["ghost-root", "ghost-portal"],

    # Frameworks
    "Next.js": ["/_next/", "__NEXT_DATA__"],
    "React": ["react.development.js", "react.production.min.js", "data-reactroot"],
    "Vue.js": ["vue.min.js", "data-v-"],
    "Nuxt": ["/_nuxt/", "__NUXT__"],
    "Tailwind CSS": ["tailwind", "tailwindcss"],
    "Bootstrap": ["bootstrap.min.css", "bootstrap.bundle"],

    # Marketing & Integrations
    "HubSpot": ["js.hs-scripts.com", "hbspt"],
    "Intercom": ["widget.intercom.io", "intercom-frame"],
    "Crisp Chat": ["client.crisp.chat"],
    "Stripe": ["js.stripe.com"],
    "Razorpay": ["checkout.razorpay.com"],
    "Google Analytics": ["googletagmanager.com/gtag", "analytics.js", "gtm.js"]
}

def detect_tech_stack(html_content: str, soup: BeautifulSoup) -> list:
    """Scans HTML markers, scripts, and links to detect underlying tech stack."""
    detected = []
    lower_html = html_content.lower()

    # Check meta generator
    for meta in soup.find_all("meta", attrs={"name": "generator"}):
        content = meta.get("content", "").lower()
        if "wordpress" in content:
            detected.append("WordPress")
        if "webflow" in content:
            detected.append("Webflow")
        if "shopify" in content:
            detected.append("Shopify")
        if "squarespace" in content:
            detected.append("Squarespace")
        if "ghost" in content:
            detected.append("Ghost")

    # Check known signatures
    for tech, signatures in TECH_SIGNATURES.items():
        if tech not in detected:
            for sig in signatures:
                if sig.lower() in lower_html:
                    detected.append(tech)
                    break

    return list(dict.fromkeys(detected))  # preserve order & unique
