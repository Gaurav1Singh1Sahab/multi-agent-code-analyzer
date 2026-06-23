from fastapi import FastAPI

app = FastAPI(
    title="Multi-Agent Code Analyzer",
    version="1.0.0"
)

@app.get("/")
def health_check():
    return {
        "status": "running",
        "service": "multi-agent-code-analyzer"
    }