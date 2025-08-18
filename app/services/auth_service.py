from typing import Optional
from app.schemas import User
from app.core.security import get_password_hash, verify_password

# ===================================================================
#  Mock Database for Sandbox Environment
# =================================p==================================
# In a real application, this data would be in your database.
# We are mocking it here to simulate user lookup.
# The password for 'admin@example.com' is 'password123'
MOCK_USERS_DB = {
    "admin@example.com": {
        "id": "user_admin_01",
        "email": "admin@example.com",
        "name": "Admin User",
        "hashed_password": get_password_hash("password123"),
        "role": "ADMIN",
        "status": "ACTIVE",
        "phone": "123-456-7890",
        "department": "IT",
        "golfCourseId": None,
        "lastLoginAt": None,
        "createdAt": "2023-01-01T00:00:00Z"
    }
}
# ===================================================================

async def get_user_by_email(email: str) -> Optional[dict]:
    """
    Retrieves a user by email from the mock database.
    In a real app, this would be: await db.execute(select(models.User).where(models.User.email == email))
    """
    if email in MOCK_USERS_DB:
        return MOCK_USERS_DB[email]
    return None

async def authenticate_user(email: str, password: str) -> Optional[dict]:
    """
    Authenticates a user.
    - Looks up the user by email.
    - Verifies the provided password against the stored hash.
    Returns the user object if authentication is successful, otherwise None.
    """
    user = await get_user_by_email(email)
    if not user:
        return None
    if not verify_password(password, user["hashed_password"]):
        return None
    return user
