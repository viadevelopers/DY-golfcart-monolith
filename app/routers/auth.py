from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse
from app.services.keycloak import keycloak_service
from app.config import get_settings


router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/login")
async def login(redirect_uri: str = Query(...)):
    login_url = keycloak_service.get_login_url(redirect_uri)
    return RedirectResponse(url=login_url)


@router.get("/callback")
async def callback(code: str = Query(...), redirect_uri: str = Query(...)):
    try:
        token_response = await keycloak_service.exchange_code_for_token(code, redirect_uri)
        return {
            "access_token": token_response["access_token"],
            "refresh_token": token_response["refresh_token"],
            "token_type": "Bearer",
            "expires_in": token_response["expires_in"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    try:
        token_response = await keycloak_service.refresh_token(refresh_token)
        return {
            "access_token": token_response["access_token"],
            "refresh_token": token_response["refresh_token"],
            "token_type": "Bearer",
            "expires_in": token_response["expires_in"]
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/logout")
async def logout(refresh_token: str):
    try:
        await keycloak_service.logout(refresh_token)
        return {"message": "Successfully logged out"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))