"""
Development server launcher.
Run from patent-kg/backend/:
    python run_api.py
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["api", "src"],
        log_level="info",
    )
