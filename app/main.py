from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, protected, golf_carts
from app.config import get_settings
from app.database import engine
from app.models import golf_cart

# Create database tables
golf_cart.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Golf Cart Management System",
    description="FastAPI application with Keycloak authentication and golf cart management",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(protected.router)
app.include_router(golf_carts.router)


@app.get("/")
async def root():
    return {
        "message": "FastAPI Keycloak Integration",
        "docs": "/docs",
        "endpoints": {
            "login": "/auth/login?redirect_uri=<your-redirect-uri>",
            "callback": "/auth/callback?code=<code>&redirect_uri=<redirect-uri>",
            "refresh": "/auth/refresh",
            "logout": "/auth/logout",
            "me": "/api/me (requires Bearer token)",
            "admin": "/api/admin (requires Bearer token and admin role)",
            "user-data": "/api/user-data (requires Bearer token)"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}