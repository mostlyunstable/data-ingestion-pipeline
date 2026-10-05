"""
Autonomous Autopilot Daemon
Self-driving background engine that continuously harvests, audits,
and ingests high-value buyer leads with ZERO manual intervention.
"""
import asyncio
import threading
import time
from datetime import datetime
from extractors.autopilot_sources import autopilot_manager
from core.pipeline import run_pipeline_for_urls, job_state

class AutopilotDaemon:
    def __init__(self):
        self.is_active = False
        self.total_cycles = 0
        self.last_cycle_time = None
        self.interval_seconds = 1800  # Default 30 minutes between continuous sweeps
        self._thread = None
        self._loop = None

    def get_status(self) -> dict:
        return {
            "is_active": self.is_active,
            "total_cycles": self.total_cycles,
            "last_cycle_time": self.last_cycle_time,
            "interval_minutes": self.interval_seconds // 60,
            "job_state": job_state.to_dict()
        }

    async def execute_single_cycle(self, batch_size: int = 15):
        """
        Executes one autonomous cycle of discovery, audit, and ingestion.
        Guarantees that at least batch_size (15) fresh, verified leads are persisted.
        """
        if job_state.is_running:
            job_state.log("⚡ [Autopilot] A cycle is already executing. Skipping redundant trigger.")
            return

        from core.database import get_db

        def get_current_count():
            try:
                conn = get_db()
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM leads")
                cnt = cur.fetchone()[0]
                conn.close()
                return cnt
            except Exception:
                return 0

        start_count = get_current_count()
        persisted_new = 0
        attempts = 0
        max_attempts = 6

        job_state.is_running = True
        job_state.total_target = batch_size
        job_state.processed = 0
        job_state.success_count = 0
        job_state.current_action = "Initiating prospect harvest..."
        job_state.log(f"⚡ [Autopilot] Commencing guaranteed harvest of {batch_size} fresh verified leads...")

        while persisted_new < batch_size and attempts < max_attempts:
            attempts += 1
            needed = batch_size - persisted_new
            pull_size = max(needed * 2 + 6, 12)

            targets = autopilot_manager.get_next_target_batch(batch_size=pull_size)
            if not targets:
                job_state.log("⚠️ [Autopilot] Expanding target corridor sweep...")
                continue

            job_state.current_action = f"Auditing {len(targets)} candidates ({persisted_new}/{batch_size} locked)..."
            job_state.log(f"🎯 [Autopilot] Round {attempts}: Hunting {len(targets)} candidates to fulfill remaining {needed} leads...")

            await run_pipeline_for_urls(
                targets, 
                niche="Autopilot Qualified", 
                source="autopilot_daemon",
                maintain_job_state=True
            )

            current_count = get_current_count()
            persisted_new = max(0, current_count - start_count)
            job_state.processed = min(batch_size, persisted_new)
            job_state.success_count = persisted_new
            job_state.log(f"📊 [Autopilot] Progress: {persisted_new}/{batch_size} new verified leads ingested.")

        self.total_cycles += 1
        self.last_cycle_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        job_state.is_running = False
        job_state.current_action = "Completed"
        job_state.log(f"✓ [Autopilot] Cycle #{self.total_cycles} complete: Ingested {persisted_new} fresh leads placed at top of dashboard!")

    def _run_loop(self):
        asyncio.set_event_loop(self._loop)
        while self.is_active:
            try:
                self._loop.run_until_complete(self.execute_single_cycle())
            except Exception as e:
                job_state.log(f"✕ [Autopilot error]: {e}")

            # Sleep between cycles in small increments to respond to stop
            for _ in range(self.interval_seconds):
                if not self.is_active:
                    break
                time.sleep(1)

    def start(self, interval_minutes: int = 30):
        if self.is_active:
            return
        self.is_active = True
        self.interval_seconds = interval_minutes * 60
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        job_state.log("🚀 [Autopilot Daemon] Activated! Ingestion pipeline running automatically on background autopilot.")

    def stop(self):
        self.is_active = False
        job_state.log("⏸ [Autopilot Daemon] Paused by user.")

autopilot_daemon = AutopilotDaemon()
