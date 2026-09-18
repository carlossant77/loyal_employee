from __future__ import annotations
import os
from fastapi import Request
from fastapi.responses import JSONResponse

API_KEY_HEADER = "X-API-Key"
PUBLIC_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}

async def api_key_middleware(request: Request, call_next):
    if request.url.path not in PUBLIC_PATHS:
        expected = os.getenv("BACKEND_API_KEY")
        supplied = request.headers.get(API_KEY_HEADER)
        if not expected or supplied != expected:
            return JSONResponse({"detail": "API key ausente ou inválida"}, status_code=401)
    return await call_next(request)
