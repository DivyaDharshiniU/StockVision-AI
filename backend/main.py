"""FastAPI application entry point for StockVision AI.

Start the server with:
    uvicorn backend.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .router import router
from .backtest_router import router as backtest_router

app = FastAPI(title="StockVision AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(backtest_router)
