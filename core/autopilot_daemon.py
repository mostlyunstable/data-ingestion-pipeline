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
        """Executes one autonomous cycle of discovery, audit, and ingestion."""
        if job_state.is_running:
            job_state.log("⚡ [Autopilot] A cycle is already executing. Skipping redundant trigger.")
            return

        job_state.log("⚡ [Autopilot] Commencing autonomous prospect discovery...")
        targets = autopilot_manager.get_next_target_batch(batch_size=batch_size)

        if not targets:
            job_state.log("⚠️ [Autopilot] No new targets discovered in current cycle.")
            return

        job_state.log(f"🎯 [Autopilot] Locked onto {len(targets)} high-intent businesses! Launching deep audits...")
        await run_pipeline_for_urls(targets, niche="Autopilot Qualified", source="autopilot_daemon")

        self.total_cycles += 1
        self.last_cycle_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        job_state.log(f"✓ [Autopilot] Cycle #{self.total_cycles} complete. Leads audited & stored.")

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
