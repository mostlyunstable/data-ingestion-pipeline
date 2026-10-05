"""
FastAPI Server & Web Dashboard Backend
Serves real-time REST endpoints and the interactive visual dashboard.
"""
import io
import csv
import asyncio
from fastapi import FastAPI, BackgroundTasks, UploadFile, File, Form, Query
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from config import BASE_DIR
from core.database import (
    init_db, get_leads, get_lead_stats, delete_lead,
    update_lead_status, export_to_csv
)
from core.pipeline import (
    job_state, run_niche_radar_pipeline, run_pipeline_for_urls
)
from core.autopilot_daemon import autopilot_daemon
from core.self_healing import run_self_healing_cycle

app = FastAPI(title="OmniLead Pipeline", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    init_db()
    run_self_healing_cycle()
    autopilot_daemon.start(interval_minutes=30)

@app.post("/api/self-heal")
async def api_trigger_self_heal():
    res = run_self_healing_cycle()
    return res

@app.get("/", response_class=HTMLResponse)
async def serve_dashboard():
    template_path = f"{BASE_DIR}/web/templates/index.html"
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/stats")
async def api_get_stats():
    return get_lead_stats()

@app.get("/api/job-status")
async def api_get_job_status():
    return job_state.to_dict()

@app.get("/api/autopilot/status")
async def api_get_autopilot_status():
    return autopilot_daemon.get_status()

@app.post("/api/autopilot/toggle")
async def api_toggle_autopilot(enable: bool = Query(...), interval_minutes: int = Query(30)):
    if enable:
        autopilot_daemon.start(interval_minutes=interval_minutes)
        return {"status": "success", "message": "Autopilot pipeline is now RUNNING 24/7 in background."}
    else:
        autopilot_daemon.stop()
        return {"status": "success", "message": "Autopilot pipeline is PAUSED."}

@app.post("/api/autopilot/run-now")
async def api_autopilot_run_now(background_tasks: BackgroundTasks, batch_size: int = Query(15)):
    if job_state.is_running:
        return JSONResponse({"status": "error", "message": "A pipeline sweep is already active!"}, status_code=400)
    background_tasks.add_task(autopilot_daemon.execute_single_cycle, batch_size)
    return {"status": "started", "message": f"Autonomous sweep initiated for {batch_size} targets with ZERO manual input."}

@app.get("/api/leads")
async def api_get_leads(
    search: str = Query("", description="Keyword search"),
    country: str = Query("", description="Country filter"),
    service_match: str = Query("", description="Filter by service match"),
    has_email: bool = Query(False, description="Filter leads with email only"),
    has_phone: bool = Query(False, description="Filter leads with phone only"),
    has_linkedin: bool = Query(False, description="Filter leads with linkedin only"),
    status: str = Query("", description="Lead status filter"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    leads = get_leads(
        search=search,
        country=country,
        service_match=service_match,
        has_email=has_email,
        has_phone=has_phone,
        has_linkedin=has_linkedin,
        status=status,
        limit=limit,
        offset=offset
    )
    return {"leads": leads}

@app.post("/api/start-hunt")
async def api_start_hunt(
    background_tasks: BackgroundTasks,
    niche: str = Form(...),
    location: str = Form(""),
    limit: int = Form(20)
):
    if job_state.is_running:
        return JSONResponse({"status": "error", "message": "A pipeline job is already active!"}, status_code=400)

    background_tasks.add_task(run_niche_radar_pipeline, niche, location, limit)
    return {"status": "started", "message": f"Radar launched for '{niche}' in '{location}'"}

@app.post("/api/ingest-urls")
async def api_ingest_urls(
    background_tasks: BackgroundTasks,
    urls_text: str = Form(...),
    niche: str = Form("Direct Batch")
):
    if job_state.is_running:
        return JSONResponse({"status": "error", "message": "A pipeline job is already active!"}, status_code=400)

    url_list = [u.strip() for u in urls_text.splitlines() if u.strip()]
    if not url_list:
        return JSONResponse({"status": "error", "message": "No valid URLs provided!"}, status_code=400)

    background_tasks.add_task(run_pipeline_for_urls, url_list, niche, "direct_urls")
    return {"status": "started", "message": f"Processing {len(url_list)} target URLs..."}

@app.post("/api/upload-file")
async def api_upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    niche: str = Form("Imported")
):
    if job_state.is_running:
        return JSONResponse({"status": "error", "message": "A pipeline job is already active!"}, status_code=400)

    contents = await file.read()
    text = contents.decode("utf-8", errors="ignore")

    discovered_urls = []
    # If CSV, scan for URL-like columns
    if file.filename.endswith(".csv"):
        reader = csv.reader(io.StringIO(text))
        for row in reader:
            for cell in row:
                cell_s = cell.strip()
                if "." in cell_s and not "@" in cell_s and ("http" in cell_s or "www" in cell_s or ".com" in cell_s or ".in" in cell_s or ".co" in cell_s):
                    discovered_urls.append(cell_s)
    else:
        # Line-by-line
        for line in text.splitlines():
            line_s = line.strip()
            if line_s:
                discovered_urls.append(line_s)

    discovered_urls = list(dict.fromkeys(discovered_urls))
    if not discovered_urls:
        return JSONResponse({"status": "error", "message": "No valid domains/URLs detected in file!"}, status_code=400)

    background_tasks.add_task(run_pipeline_for_urls, discovered_urls, niche, f"file:{file.filename}")
    return {"status": "started", "message": f"Discovered {len(discovered_urls)} targets from {file.filename}!"}

@app.patch("/api/leads/{lead_id}/status")
async def api_update_status(lead_id: int, status: str = Query(...)):
    update_lead_status(lead_id, status)
    return {"status": "success", "lead_id": lead_id, "new_status": status}

@app.post("/api/leads/{lead_id}/toggle-status")
async def api_toggle_status(lead_id: int):
    from core.database import get_db
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM leads WHERE id = ?", (lead_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return JSONResponse({"status": "error", "message": "Lead not found"}, status_code=404)
    current_status = row[0] or "Yet to Explore"
    new_status = "Contacted" if current_status == "Yet to Explore" else "Yet to Explore"
    update_lead_status(lead_id, new_status)
    return {"status": "success", "lead_id": lead_id, "new_status": new_status}

@app.delete("/api/leads/{lead_id}")
async def api_delete_lead(lead_id: int):
    delete_lead(lead_id)
    return {"status": "success", "lead_id": lead_id}

@app.get("/api/export-csv")
async def api_export_csv():
    filepath = export_to_csv()
    return FileResponse(filepath, filename="extracted_client_leads.csv", media_type="text/csv")
