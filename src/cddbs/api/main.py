from fastapi import FastAPI, HTTPException
from src.cddbs.pipeline.orchestrator import run_pipeline
from src.cddbs.database import init_db

app = FastAPI(title='CDDBS API')

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/")
def root():
    return {"service": "cddbs", "status": "ok"}

@app.get("/analyze/{outlet}/{country}")
def analyze(outlet: str, country: str):
    try:
        result = run_pipeline(outlet, country)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
