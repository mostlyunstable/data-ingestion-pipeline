#!/usr/bin/env python3
"""
OmniLead Pipeline - One-Click Launcher
Initializes the database, spins up the server, and automatically opens your web browser.
"""
import sys
import os
import time
import webbrowser
import uvicorn

# Ensure the project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.database import init_db

def main():
    print("=" * 60)
    print("⚡  OMNILEAD - AGGRESSIVE CLIENT & BUSINESS INGESTION PIPELINE  ⚡")
    print("=" * 60)
    print("» Initializing local SQLite database warehouse...")
    init_db()
    print("✓ Database ready at: data/leads.db")

    port = 8000
    host = "127.0.0.1"
    url = f"http://{host}:{port}"

    print(f"» Starting Web Control Center on {url}...")
    print("» Launching your web browser automatically in 1.5 seconds...")

    def open_browser():
        time.sleep(1.5)
        webbrowser.open(url)

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    print("=" * 60)
    print(f"🚀 DASHBOARD ONLINE: Open {url} if your browser didn't launch")
    print("Press Ctrl + C anytime to stop the server.")
    print("=" * 60)

    uvicorn.run("web.server:app", host=host, port=port, reload=False, log_level="warning")

if __name__ == "__main__":
    main()
