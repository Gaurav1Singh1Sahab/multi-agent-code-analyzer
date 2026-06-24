from fastapi import FastAPI

from backend.routes.auth import router as auth_router

app = FastAPI(
    title="Multi-Agent Code Analyzer",
    version="1.0.0"
)


app.include_router(auth_router)


@app.get("/")
def health_check():
    return {
        "status": "running",
        "service": "multi-agent-code-analyzer"
    }