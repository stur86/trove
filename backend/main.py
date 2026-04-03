from fastapi import FastAPI

app = FastAPI(title="Trove", version="0.1.0")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
