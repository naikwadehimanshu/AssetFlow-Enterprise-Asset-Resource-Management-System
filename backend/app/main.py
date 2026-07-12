from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .config import settings
from .routers import auth, organization, assets, allocations, bookings, maintenance, audits, reports, notifications

# Create database tables automatically
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="Backend ERP API for AssetFlow - Enterprise Asset & Resource Management System"
)

# Enable wide CORS so frontend developers can open local HTML files (file:// or localhost) and call APIs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Modular Routers
app.include_router(auth.router)
app.include_router(organization.router)
app.include_router(assets.router)
app.include_router(allocations.router)
app.include_router(bookings.router)
app.include_router(maintenance.router)
app.include_router(audits.router)
app.include_router(reports.router)
app.include_router(notifications.router)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "project": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }
