"""Mock backend service for testing purposes."""
from fastapi import FastAPI, Request

app = FastAPI()


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
async def catch_all(path: str, request: Request):
    return {
        "service": "mock-backend",
        "method": request.method,
        "path": f"/{path}",
    }
