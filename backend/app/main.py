"""
US Financial Statement Database API

Main FastAPI application.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import company, filings, statements, data_points
from app.core.config import settings
from app.core.database import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("Starting US Financial Statement Database API...")
    await init_db()
    print("Database initialized")
    yield
    # Shutdown
    print("Shutting down...")
    await close_db()
    print("Database connections closed")


# Create FastAPI app
app = FastAPI(
    title="US Financial Statement Database API",
    description="""
    RESTful API providing access to raw, as-reported financial statement data
    from 10-K and 10-Q filings for all actively traded US public companies.

    ## Features

    * **Raw Data**: All line items stored exactly as reported (no normalization)
    * **Comprehensive Coverage**: All NASDAQ, NYSE, and NYSE American companies
    * **Historical Data**: Up to 10 years of historical filings
    * **Three Statements**: Income Statement, Balance Sheet, Cash Flow Statement
    * **Time Series**: Track any metric over time

    ## Authentication

    All endpoints require an API key. Include your API key in the request header:

    ```
    X-API-Key: your-api-key-here
    ```

    ## Rate Limiting

    - Free tier: 100 requests/hour
    - Pro tier: 1000 requests/hour

    ## Data Freshness

    New filings are processed and available within 1 hour of publication on SEC EDGAR.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint (no auth required)
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "US Financial Statement Database API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }


# Include routers
app.include_router(
    company.router,
    prefix=f"{settings.API_V1_PREFIX}/company",
    tags=["Company"],
)

app.include_router(
    filings.router,
    prefix=f"{settings.API_V1_PREFIX}/filings",
    tags=["Filings"],
)

app.include_router(
    statements.router,
    prefix=f"{settings.API_V1_PREFIX}/statement",
    tags=["Statements"],
)

app.include_router(
    data_points.router,
    prefix=f"{settings.API_V1_PREFIX}/data_point",
    tags=["Data Points"],
)


# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler."""
    return JSONResponse(
        status_code=404,
        content={"detail": "Resource not found"},
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
        workers=1 if settings.DEBUG else settings.API_WORKERS,
    )
