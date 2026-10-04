"""
Pipeline Configuration & Stealth Settings
Controls rotation, timeouts, page discovery targets, and noise filtering.
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
EXPORTS_DIR = os.path.join(BASE_DIR, "exports")
DB_PATH = os.path.join(DATA_DIR, "leads.db")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(EXPORTS_DIR, exist_ok=True)

# Common contact subpages to crawl on any company website
CONTACT_SUBPAGES = [
    "/contact",
    "/contact-us",
    "/about",
    "/about-us",
    "/team",
    "/our-team",
    "/meet-the-team",
    "/leadership",
    "/careers",
    "/privacy",
    "/privacy-policy",
    "/terms",
    "/imprint",
]

# Rotating stealth user-agents simulating real browsers
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
]

# Junk & template dummy email domains to ignore
IGNORED_EMAIL_DOMAINS = {
    "example.com", "domain.com", "yourdomain.com", "wixpress.com",
    "sentry.io", "cloudflare.com", "gravatar.com", "github.com",
    "mycompany.com", "email.com", "site.com", "schema.org",
    "company.com", "acme.co", "studio.dev", "website.com"
}

IGNORED_EMAIL_PREFIXES = {
    "abuse", "noreply", "no-reply", "mailer-daemon", "postmaster",
    "security", "privacy", "donotreply", "notification", "alert",
    "you", "yourname", "username", "user", "name", "email",
    "test", "demo", "sample", "placeholder"
}

# Network speed & timeouts
REQUEST_TIMEOUT = 10  # seconds
MAX_CONCURRENT_REQUESTS = 15
MAX_SEARCH_RESULTS = 30
