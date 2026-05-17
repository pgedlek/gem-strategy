"""
server.py
─────────
Entry point for running the GEM API server.
 
Usage:
    python server.py                  # development (auto-reload)
    uvicorn server:app --host 0.0.0.0 --port 8000   # production
"""
 
import uvicorn
from api.app import app  # re-export so uvicorn can find it
 
if __name__ == "__main__":
    uvicorn.run(
        "api.app:app",
        host="0.0.0.0",
        port=8000,
        reload=True,          # auto-reload on file changes (dev mode)
        log_level="info",
    )
 