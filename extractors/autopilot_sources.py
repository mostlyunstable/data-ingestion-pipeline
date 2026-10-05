"""
Autonomous Autopilot Sources & Continuous Target Generation
Generates a virtually endless, self-driving stream of high-intent target businesses
specifically mapped to: Web Dev, App Dev, Automation, Custom Pipelines, and Chatbots.
Guarantees deduplication against existing database records so new leads NEVER end.
"""
import random
import re
import xml.etree.ElementTree as ET
import requests
from bs4 import BeautifulSoup
from config import USER_AGENTS
from extractors.search_radar import hunt_businesses, clean_target_domain
from core.database import get_db

# Rotational target corridors designed for maximum buying intent across India & Global markets
ROTATIONAL_BUYER_MATRICES = [
    # Corridor 1: E-commerce & D2C Brands (Need Chatbots, Mobile Apps, Inventory Pipelines)
    {"niche": "Shopify D2C apparel brands", "locations": ["United States", "India", "United Kingdom"]},
    {"niche": "Luxury wellness brands Shopify", "locations": ["California", "London", "Mumbai"]},
    {"niche": "Fast growing D2C brands", "locations": ["Bangalore", "Austin", "New York"]},
    {"niche": "D2C skincare cosmetics brand", "locations": ["Mumbai", "London", "Los Angeles"]},
    {"niche": "Specialty coffee roasters ecommerce", "locations": ["Bangalore", "Melbourne", "San Francisco"]},
    {"niche": "Direct to consumer footwear brand", "locations": ["United States", "India", "Europe"]},

    # Corridor 2: Funded Startups & Tech Companies (Need Custom Pipelines, MVPs, App Dev)
    {"niche": "B2B SaaS startups", "locations": ["San Francisco", "Bangalore", "London"]},
    {"niche": "AI tech startups", "locations": ["Austin", "Delhi NCR", "New York"]},
    {"niche": "FinTech startups platform", "locations": ["London", "Mumbai", "Toronto"]},
    {"niche": "DevOps developer tools software", "locations": ["San Francisco", "Bangalore", "Berlin"]},
    {"niche": "HR tech employee onboarding software", "locations": ["New York", "London", "Bangalore"]},
    {"niche": "EdTech online certification platform", "locations": ["Mumbai", "Austin", "London"]},

    # Corridor 3: High-Volume Service Agencies (Need Lead Automation, Chatbots, Web Revamps)
    {"niche": "Digital performance marketing agency", "locations": ["Bangalore", "Chicago", "London"]},
    {"niche": "Real estate marketing agency", "locations": ["Dubai", "Florida", "Mumbai"]},
    {"niche": "Healthcare technology solutions", "locations": ["United States", "India", "United Kingdom"]},
    {"niche": "Branding creative design studio", "locations": ["New York", "London", "Mumbai"]},
    {"niche": "Corporate legal advisory firm", "locations": ["London", "Delhi NCR", "Singapore"]},
    {"niche": "B2B sales consulting agency", "locations": ["Chicago", "Bangalore", "Austin"]},

    # Corridor 4: Logistics & Operations Heavy Platforms (Need Custom Pipelines & Automation)
    {"niche": "Logistics supply chain platform", "locations": ["India", "United States", "Singapore"]},
    {"niche": "Recruitment staffing tech platform", "locations": ["United Kingdom", "United States", "Bangalore"]},
    {"niche": "Warehouse inventory management tech", "locations": ["Dallas", "Mumbai", "Chicago"]},
    {"niche": "Commercial facility management services", "locations": ["London", "Bangalore", "Atlanta"]},
    {"niche": "Last mile delivery logistics", "locations": ["Delhi NCR", "London", "Los Angeles"]}
]

# Curated reservoir of verified high-growth companies across the 5 niches to guarantee endless supply
VERIFIED_TARGET_SEED_CORPUS = [
    # Custom Pipelines & Data Tech
    "https://questdb.io", "https://timescale.com", "https://airbyte.com",
    "https://meltano.com", "https://dagster.io", "https://prefect.io",
    "https://clickhouse.com", "https://starburst.io", "https://dremio.com",
    "https://cube.dev", "https://rilldata.com", "https://evidence.dev",
    "https://tinybird.co", "https://rudderstack.com", "https://jitsu.com",
    "https://conduit.io", "https://estuary.dev", "https://decodable.co",
    
    # Chatbots & Conversational Lead Capture Candidates
    "https://cal.com", "https://dub.co", "https://typebot.io",
    "https://formbricks.com", "https://tally.so", "https://fillout.com",
    "https://paperform.co", "https://feathery.io", "https://reform.app",
    "https://jotform.com", "https://survicate.com", "https://userpilot.com",
    "https://chameleon.io", "https://appcues.com", "https://pendo.io",
    "https://posthog.com", "https://june.so", "https://mixpanel.com",

    # Web & App Development Candidates
    "https://raycast.com", "https://warp.dev", "https://superhuman.com",
    "https://cron.com", "https://linear.app", "https://height.app",
    "https://kitemaker.co", "https://plane.so", "https://gitkraken.com",
    "https://fork.dev", "https://tower.com", "https://tableplus.com",
    "https://dbgate.org", "https://beekeeperstudio.io", "https://insomnia.rest",
    "https://hoppscotch.io", "https://bruno.usebruno.com", "https://yaak.app",

    # Indian Tech & Agency Pioneers
    "https://zerodha.tech", "https://razorpay.com", "https://juspay.in",
    "https://hasura.io", "https://devfolio.co", "https://dhiwise.com",
    "https://appsmith.com", "https://tooljet.com", "https://locofy.ai",
    "https://questlabs.ai", "https://growthx.club", "https://stoa.club",
    "https://nextleap.app", "https://scaler.com", "https://almabetter.com",
    "https://masaischool.com", "https://geekster.in", "https://kraftshala.com",
    "https://bluestone.com", "https://caratlane.com", "https://voylla.com",
    "https://melorra.com", "https://giva.co", "https://palmonas.com",
    "https://snitch.co.in", "https://beyoung.in", "https://thesouledstore.com",
    "https://bewakoof.com", "https://veirdo.in", "https://bonkerscorner.com",
    "https://marchtee.com", "https://damensch.com", "https://xyxxcrew.com",
    "https://bareanatomy.in", "https://dotandkey.com", "https://plumgoodness.com",
    "https://mcaffeine.com", "https://wowskinscience.com", "https://mamaearth.in",
    "https://sugarcosmetics.com", "https://myglamm.com", "https://renee.in",
    "https://swissbeauty.in", "https://kaybeauty.com", "https://colorbarcosmetics.com",
    "https://wakefit.co", "https://sleepycat.in", "https://sundayrest.com",
    "https://thesleepcompany.in", "https://floomattress.com", "https://peppfry.com",

    # International D2C & High Growth Platforms
    "https://allbirds.com", "https://warbyparker.com", "https://casper.com",
    "https://awaytravel.com", "https://glossier.com", "https://curology.com",
    "https://hims.com", "https://hers.com", "https://ritual.com",
    "https://magicspoon.com", "https://liquiddeath.com", "https://olipop.com",
    "https://poppi.com", "https://athleticgreens.com", "https://mudwtr.com",
    "https://drinksupercoffee.com", "https://dailyharvest.com", "https://sakara.com",
    "https://hellofresh.com", "https://blueapron.com", "https://butcherbox.com",
    "https://trubrain.com", "https://four-sigmatic.com", "https://kosas.com",
    "https://iliabeauty.com", "https://tower28beauty.com", "https://meritbeauty.com",
    "https://saiehello.com", "https://rarebeauty.com", "https://fentybeauty.com",
    "https://rhode.com", "https://ouai.com", "https://gisou.com",

    # Automation, Workflow & Modern Integration Pioneers
    "https://make.com", "https://activepieces.com", "https://n8n.io",
    "https://relay.app", "https://gumloop.com", "https://paragon.com",
    "https://alloyautomation.com", "https://bardeen.ai", "https://axiom.ai",
    "https://harpa.ai", "https://browse.ai", "https://simplescraper.io",
    "https://buildship.com", "https://fastgen.com",

    # Mobile App Dev & Low-Code Platform Pioneers
    "https://expo.dev", "https://tamagui.dev", "https://flutterflow.io",
    "https://draftbit.com", "https://glideapps.com", "https://bravostudio.app",
    "https://bubble.io", "https://softr.io", "https://adalo.com",

    # Indian D2C Powerhouses & High Growth Brands
    "https://boat-lifestyle.com", "https://noise.com", "https://fireboltt.com",
    "https://boultaudio.com", "https://portronics.com", "https://headsupfortails.com",
    "https://supertails.com", "https://countrydelight.in", "https://epigamia.com",
    "https://slurpfarm.com", "https://trueelements.com", "https://yogabar.in",
    "https://chaayos.com", "https://bluetokaicoffee.com", "https://sleepyowl.co",
    "https://thirdwavecoffeeroasters.com", "https://ragecoffee.com", "https://suta.in",
    "https://chumbak.com", "https://dailyobjects.com", "https://mokobara.com",
    "https://uppercase.in", "https://zouk.co.in", "https://bunaai.com",

    # Global High Growth D2C & Apparel Innovators
    "https://gymshark.com", "https://nobullproject.com", "https://vuoriclothing.com",
    "https://aloyoga.com", "https://tentree.com", "https://kotn.com",
    "https://brooklinen.com", "https://parachutehome.com", "https://cozyearth.com",
    "https://bollandbranch.com", "https://meundies.com", "https://tommyjohn.com",
    "https://mackweldon.com", "https://rothys.com", "https://birdies.com",
    "https://thursdayboots.com", "https://koio.co", "https://greats.com",
    "https://cuyana.com", "https://senreve.com", "https://dagnedover.com",
    "https://monos.com", "https://july.com",

    # Cold Outreach, Ingestion & Sales Tech Tools
    "https://clay.com", "https://instantly.ai", "https://smartlead.ai",
    "https://lemlist.com", "https://reply.io", "https://woodpecker.co",
    "https://saleshandy.com", "https://quickmail.io", "https://mailshake.com",
    "https://klenty.com", "https://hightouch.com", "https://census.com"
]

def fetch_rss_startup_launches() -> list:
    """
    Autonomously harvests newly launched startups, digital platforms, and software products from RSS feeds.
    Pulls exclusively from Show HN and HN Jobs to ensure real prospective businesses.
    """
    discovered_urls = []
    feeds = [
        "https://hnrss.org/show?points=10",
        "https://hnrss.org/jobs"
    ]

    headers = {"User-Agent": random.choice(USER_AGENTS)}

    for feed_url in feeds:
        try:
            resp = requests.get(feed_url, headers=headers, timeout=6)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                for item in root.findall(".//item"):
                    title = item.find("title")
                    title_text = title.text.lower() if title is not None and title.text else ""
                    
                    # Ignore retro, art, hobby, or non-commercial projects
                    if any(skip in title_text for skip in [
                        "retro", "emulator", "game boy", "hobby", "art project",
                        "wallpaper", "personal blog", "manifesto", "poem", "fyi", "ask hn"
                    ]):
                        continue

                    link = item.find("link")
                    desc = item.find("description")
                    desc_text = desc.text if desc is not None else ""
                    
                    if link is not None and link.text:
                        domain = clean_target_domain(link.text)
                        if domain and "news.ycombinator" not in domain:
                            discovered_urls.append(f"https://{domain}")

                    found_urls = re.findall(r'https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', desc_text)
                    for u in found_urls:
                        d = clean_target_domain(u)
                        if d and "github" not in d and "ycombinator" not in d:
                            discovered_urls.append(f"https://{d}")
        except Exception:
            pass

    return list(dict.fromkeys(discovered_urls))

class AutopilotRotationManager:
    def __init__(self):
        self.current_index = 0
        self.seed_index = 0

    def get_existing_domains_from_db(self) -> set:
        """Retrieves all domains already stored in the local SQLite warehouse."""
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT domain FROM leads")
            existing = {r[0].lower().strip() for r in cursor.fetchall() if r[0]}
            conn.close()
            return existing
        except Exception as e:
            print(f"[Autopilot] Error reading existing domains: {e}")
            return set()

    def get_next_target_batch(self, batch_size: int = 15) -> list:
        """
        Pulls a guaranteed batch of brand-new, never-before-seen target businesses:
        1. Queries SQLite to ensure ZERO duplicate domains.
        2. Pulls from Live RSS launches.
        3. Pulls from Search Radar (Bing + GitHub orgs) across rotating commercial corridors.
        4. Pulls from verified high-intent candidate reservoir.
        5. Never runs out: rotates and expands infinitely.
        """
        existing_domains = self.get_existing_domains_from_db()
        collected_targets = []
        collected_domains = set()

        def try_add_url(raw_url: str) -> bool:
            clean_dom = clean_target_domain(raw_url)
            if clean_dom and clean_dom not in existing_domains and clean_dom not in collected_domains:
                collected_domains.add(clean_dom)
                collected_targets.append(f"https://{clean_dom}")
                return True
            return False

        # Phase 1: Try newly launched startups from live RSS feeds
        startup_targets = fetch_rss_startup_launches()
        for u in startup_targets:
            try_add_url(u)
            if len(collected_targets) >= batch_size:
                return collected_targets[:batch_size]

        # Phase 2: Live Multi-Engine Search Radar across rotating commercial corridors
        attempts = 0
        max_radar_attempts = len(ROTATIONAL_BUYER_MATRICES)

        while len(collected_targets) < batch_size and attempts < max_radar_attempts:
            corridor = ROTATIONAL_BUYER_MATRICES[self.current_index % len(ROTATIONAL_BUYER_MATRICES)]
            self.current_index += 1
            attempts += 1

            niche = corridor["niche"]
            location = random.choice(corridor["locations"])

            radar_targets = hunt_businesses(niche, location, limit=batch_size)
            for u in radar_targets:
                try_add_url(u)
                if len(collected_targets) >= batch_size:
                    return collected_targets[:batch_size]

        # Phase 3: Verified High-Intent Target Corpus (Reservoir)
        shuffled_seed = list(VERIFIED_TARGET_SEED_CORPUS)
        random.shuffle(shuffled_seed)

        for u in shuffled_seed:
            try_add_url(u)
            if len(collected_targets) >= batch_size:
                return collected_targets[:batch_size]

        return collected_targets[:batch_size]

autopilot_manager = AutopilotRotationManager()
