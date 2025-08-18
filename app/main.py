from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.routers import auth, golf_course, cart, map as map_router, user, address

app = FastAPI(
    title="골프카트 관리 백오피스 API",
    version="1.0.0",
    description="DY 골프카트 관리 백오피스 시스템의 REST API 명세서입니다."
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to your frontend's domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": f"An unexpected error occurred: {exc}",
            },
        },
    )

@app.get("/", tags=["Health Check"])
def read_root():
    """Health check endpoint to confirm the server is running."""
    return {"status": "ok", "message": "Welcome to the Golf Cart API"}

# The routers will be included here
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(golf_course.router, prefix="/api/golf-courses", tags=["Golf Courses"])
app.include_router(cart.router, prefix="/api/carts", tags=["Carts"])
app.include_router(map_router.router, prefix="/api/maps", tags=["Maps"])
app.include_router(user.router, prefix="/api/users", tags=["Users"])
app.include_router(address.router, prefix="/api/address", tags=["Address"])
