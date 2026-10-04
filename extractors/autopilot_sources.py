"""
Autonomous Autopilot Sources & Target Generation
Generates a continuous, self-driving stream of high-intent target businesses
specifically mapped to: Web Dev, App Dev, Automation, Custom Pipelines, and Chatbots.
No user typing required.
"""
import random
import re
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup
from config import USER_AGENTS
from extractors.search_radar import hunt_businesses, clean_target_domain

# Pre-compiled rotational target corridors designed for maximum buying intent
ROTATIONAL_BUYER_MATRICES = [
    # Corridor 1: E-commerce & D2C Brands (Need Chatbots, Mobile Apps, Inventory Pipelines)
    {"niche": "Shopify D2C apparel brands", "locations": ["United States", "India", "United Kingdom"]},
    {"niche": "Luxury wellness brands Shopify", "locations": ["California", "London", "Mumbai"]},
    {"niche": "Fast growing D2C brands", "locations": ["Bangalore", "Austin", "New York"]},

    # Corridor 2: Funded Startups & Tech Companies (Need Custom Pipelines, MVPs, App Dev)
    {"niche": "B2B SaaS startups", "locations": ["San Francisco", "Bangalore", "London"]},
    {"niche": "AI tech startups", "locations": ["Austin", "Delhi NCR", "New York"]},
    {"niche": "FinTech startups platform", "locations": ["London", "Mumbai", "Toronto"]},

    # Corridor 3: High-Volume Service Agencies (Need Lead Automation, Chatbots, Web Revamps)
    {"niche": "Digital performance marketing agency", "locations": ["Bangalore", "Chicago", "London"]},
    {"niche": "Real estate marketing agency", "locations": ["Dubai", "Florida", "Mumbai"]},
    {"niche": "Healthcare technology solutions", "locations": ["United States", "India", "United Kingdom"]},

    # Corridor 4: Logistics & Operations Heavy Platforms (Need Custom Pipelines & Automation)
    {"niche": "Logistics supply chain platform", "locations": ["India", "United States", "Singapore"]},
    {"niche": "Recruitment staffing tech platform", "locations": ["United Kingdom", "United States", "Bangalore"]}
]

def fetch_rss_startup_launches() -> list:
    """
    Autonomously harvests newly launched startups and software products from RSS feeds.
    These companies literally just launched and urgently need web improvements, mobile apps, or chatbots.
    """
    discovered_urls = []
    feeds = [
        "https://hnrss.org/show?points=20",   # Show HN: launches by founders
        "https://hnrss.org/jobs"              # HN Hiring: companies with budget actively seeking engineering
    ]

    headers = {"User-Agent": random.choice(USER_AGENTS)}

    for feed_url in feeds:
        try:
            resp = requests.get(feed_url, headers=headers, timeout=8)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                for item in root.findall(".//item"):
                    link = item.find("link")
                    desc = item.find("description")
                    desc_text = desc.text if desc is not None else ""
                    
                    # Extract external URLs mentioned in the description or link
                    if link is not None and link.text:
                        domain = clean_target_domain(link.text)
                        if domain and "news.ycombinator" not in domain:
                            discovered_urls.append(f"https://{domain}")

                    # Find URLs in description
                    found_urls = re.findall(r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', desc_text)
                    for u in found_urls:
                        d = clean_target_domain(u)
                        if d and "github" not in d and "ycombinator" not in d:
                            discovered_urls.append(f"https://{d}")
        except Exception:
            pass

    return list(dict.fromkeys(discovered_urls))[:15]

class AutopilotRotationManager:
    def __init__(self):
        self.current_index = 0

    def get_next_target_batch(self, batch_size: int = 15) -> list:
        """
        Pulls a blended batch:
        1. Live newly launched startups from feeds
        2. High-intent rotational buyer corridor
        """
        targets = []

        # 1. Try live startup launches
        startup_targets = fetch_rss_startup_launches()
        targets.extend(startup_targets)

        # 2. Add from rotational buyer matrix
        corridor = ROTATIONAL_BUYER_MATRICES[self.current_index % len(ROTATIONAL_BUYER_MATRICES)]
        self.current_index += 1

        niche = corridor["niche"]
        location = random.choice(corridor["locations"])

        radar_targets = hunt_businesses(niche, location, limit=batch_size)
        targets.extend(radar_targets)

        # Deduplicate
        unique_targets = list(dict.fromkeys(targets))
        return unique_targets[:batch_size]

autopilot_manager = AutopilotRotationManager()
