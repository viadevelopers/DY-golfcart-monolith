from keycloak import KeycloakOpenID
from jose import jwt, JWTError
from typing import Optional
import httpx
from app.config import get_settings


class KeycloakService:
    def __init__(self):
        settings = get_settings()
        self.keycloak_openid = KeycloakOpenID(
            server_url=settings.keycloak_server_url,
            client_id=settings.keycloak_client_id,
            realm_name=settings.keycloak_realm_name,
            client_secret_key=settings.keycloak_client_secret
        )
        self._public_key = None
    
    async def get_public_key(self):
        if not self._public_key:
            self._public_key = "-----BEGIN PUBLIC KEY-----\n" + \
                              self.keycloak_openid.public_key() + \
                              "\n-----END PUBLIC KEY-----"
        return self._public_key
    
    async def verify_token(self, token: str) -> Optional[dict]:
        try:
            public_key = await self.get_public_key()
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                audience=get_settings().keycloak_client_id,
                options={"verify_signature": True, "verify_aud": True, "verify_exp": True}
            )
            return payload
        except JWTError:
            return None
    
    def get_login_url(self, redirect_uri: str) -> str:
        return self.keycloak_openid.auth_url(redirect_uri=redirect_uri)
    
    async def exchange_code_for_token(self, code: str, redirect_uri: str) -> dict:
        return self.keycloak_openid.token(
            grant_type="authorization_code",
            code=code,
            redirect_uri=redirect_uri
        )
    
    async def refresh_token(self, refresh_token: str) -> dict:
        return self.keycloak_openid.refresh_token(refresh_token)
    
    async def logout(self, refresh_token: str):
        self.keycloak_openid.logout(refresh_token)


keycloak_service = KeycloakService()