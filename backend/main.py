from fastapi import FastAPI

from backend.config.router import router as config_router

app = FastAPI(title="Trove", version="0.1.0")

app.include_router(config_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
