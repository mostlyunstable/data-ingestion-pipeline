"""
OmniLead Pipeline - Standard Root Entrypoint
Exports the FastAPI application from web.server for Vercel, Uvicorn, and standard runners.
"""
from web.server import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
