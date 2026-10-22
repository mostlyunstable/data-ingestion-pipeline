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

import socket

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.4)
        return s.connect_ex((host, port)) == 0

def select_active_port(preferred: int = 8000) -> int:
    env_port = os.environ.get("PORT")
    if env_port:
        try:
            return int(env_port)
        except ValueError:
            pass
    if not is_port_in_use(preferred):
        return preferred
    for candidate in [8001, 8080, 8081, 5000, 5050]:
        if not is_port_in_use(candidate):
            return candidate
    return preferred

def main():
    print("=" * 60)
    print("⚡  OMNILEAD - AGGRESSIVE CLIENT & BUSINESS INGESTION PIPELINE  ⚡")
    print("=" * 60)
    print("» Initializing local SQLite database warehouse...")
    init_db()
    print("✓ Database ready at: data/leads.db")

    port = select_active_port(8000)
    host = "0.0.0.0"
    url = f"http://127.0.0.1:{port}"

    if port != 8000 and not os.environ.get("PORT"):
        print(f"ℹ️  Notice: Port 8000 is occupied by another local service.")
        print(f"   OmniLead seamlessly shifted to port {port} to prevent conflict.")

    print(f"» Starting Web Control Center on {url} (listening on {host}:{port})...")
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
