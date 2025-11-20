#!/usr/bin/env python3
"""
Simplified Render Web Service for Testing
Minimal FastAPI app to verify deployment works
"""
import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse

# FastAPI app
app = FastAPI(title="NeoLight Render Service", version="1.0.0")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "NeoLight Render Service",
        "status": "running",
        "message": "Simplified version for testing",
    }


@app.get("/health")
async def health():
    """Health check endpoint for Render"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "service": "NeoLight SmartTrader",
            "port": int(os.getenv("PORT", "8080")),
        },
    )
