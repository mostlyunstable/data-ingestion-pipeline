"""
Master Pipeline Coordinator
Orchestrates:
  Extract (Search Radar / Direct URLs) -> Transform (Miner, Cleaner, Pitch Hook) -> Load (SQLite)
Maintains real-time job state and metrics for the visual dashboard.
"""
import asyncio
from datetime import datetime
from config import MAX_CONCURRENT_REQUESTS
from core.database import save_or_update_lead, get_lead_stats
from extractors.search_radar import hunt_businesses
from extractors.site_crawler import crawl_single_company
from transformers.cleaner import clean_lead_payload
from transformers.pitch_hook import generate_pitch_hook

class IngestionJobState:
    def __init__(self):
        self.is_running = False
        self.total_target = 0
        self.processed = 0
        self.success_count = 0
        self.emails_found = 0
        self.phones_found = 0
        self.current_action = "Idle"
        self.logs = []

    def log(self, message: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.logs.append(entry)
        if len(self.logs) > 100:
            self.logs.pop(0)

    def to_dict(self):
        pct = 0
        if self.total_target > 0:
            pct = min(100, int((self.processed / self.total_target) * 100))
        return {
            "is_running": self.is_running,
            "total_target": self.total_target,
            "processed": self.processed,
            "success_count": self.success_count,
            "emails_found": self.emails_found,
            "phones_found": self.phones_found,
            "progress_percent": pct,
            "current_action": self.current_action,
            "logs": self.logs[-15:]
        }

# Global job state singleton
job_state = IngestionJobState()

async def process_company_lead(url: str, niche: str, source: str) -> dict:
    """Extracts, transforms, and persists a single company lead."""
    try:
        raw_lead = await crawl_single_company(url, niche=niche, source=source)
        if not raw_lead or not raw_lead.get("domain"):
            return None

        # Clean
        cleaned = clean_lead_payload(raw_lead)

        # Blacklist massive directories and platforms
        dom = cleaned.get("domain", "").lower()
        if any(b in dom for b in [
            "ycombinator", "github", "apple", "google", "microsoft", "producthunt",
            "reddit", "twitter", "linkedin", "wikipedia", "shopify", "wordpress",
            "wix", "squarespace", "amazon", "stripe", "hubspot", "mailchimp"
        ]):
            return None

        # Quality Gate: Must have at least one direct contact method (Email or Phone)
        has_email = len(cleaned.get("emails", [])) > 0
        has_phone = len(cleaned.get("phones", [])) > 0

        if not (has_email or has_phone):
            return None

        # Generate Pitch Hook if not already tailored by opportunity auditor
        if not cleaned.get("pitch_hook"):
            pitch = generate_pitch_hook(
                cleaned.get("company_name", ""),
                cleaned.get("tech_stack", []),
                cleaned.get("industry_niche", niche),
                cleaned.get("country", ""),
                cleaned.get("meta_description", "")
            )
            cleaned["pitch_hook"] = pitch

        # Persist to Database
        is_new = save_or_update_lead(cleaned)

        return {
            "lead": cleaned,
            "is_new": is_new,
            "has_email": has_email,
            "has_phone": has_phone
        }
    except Exception as e:
        job_state.log(f"Error processing {url}: {e}")
        return None

async def run_pipeline_for_urls(urls: list, niche: str = "", source: str = "direct"):
    """Runs concurrent ingestion for a batch of target URLs."""
    global job_state
    job_state.is_running = True
    job_state.total_target = len(urls)
    job_state.processed = 0
    job_state.success_count = 0
    job_state.emails_found = 0
    job_state.phones_found = 0
    job_state.log(f"Initiating pipeline for {len(urls)} targets...")

    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

    async def sem_worker(target_url):
        async with semaphore:
            job_state.current_action = f"Scanning {target_url[:40]}..."
            res = await process_company_lead(target_url, niche=niche, source=source)
            job_state.processed += 1
            if res and res["lead"]:
                job_state.success_count += 1
                lead = res["lead"]
                emails = lead.get("emails", [])
                phones = lead.get("phones", [])
                if emails:
                    job_state.emails_found += len(emails)
                if phones:
                    job_state.phones_found += len(phones)

                job_state.log(f"✓ Sucked in: {lead.get('company_name')} ({lead.get('domain')}) | {len(emails)} emails")
            else:
                job_state.log(f"✕ Skipping unresolvable: {target_url}")

    tasks = [sem_worker(u) for u in urls]
    await asyncio.gather(*tasks, return_exceptions=True)

    job_state.is_running = False
    job_state.current_action = "Completed"
    job_state.log(f"Pipeline finished! Extracted {job_state.success_count} businesses.")

async def run_niche_radar_pipeline(niche: str, location: str, limit: int = 20):
    """
    Finds businesses by Niche + Location via Search Radar,
    then aggressively sucks all company data into the pipeline.
    """
    global job_state
    job_state.is_running = True
    job_state.current_action = f"Radar hunting '{niche}' in '{location}'..."
    job_state.log(f"Radar hunting for '{niche}' companies in '{location}'...")

    # Run blocking search in threadpool
    loop = asyncio.get_event_loop()
    discovered_urls = await loop.run_in_executor(None, hunt_businesses, niche, location, limit)

    if not discovered_urls:
        job_state.is_running = False
        job_state.current_action = "No domains found"
        job_state.log("Search radar found 0 new domains for this query.")
        return

    job_state.log(f"Radar locked onto {len(discovered_urls)} target companies! Launching deep extractors...")
    source_tag = f"radar:{niche}@{location}"
    await run_pipeline_for_urls(discovered_urls, niche=niche, source=source_tag)
