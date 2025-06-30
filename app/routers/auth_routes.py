# backend/app/routers/auth_routes.py

from fastapi import APIRouter, Depends, HTTPException, status
from firebase_admin import auth
from firebase_admin.exceptions import FirebaseError
import logging

# Assuming get_current_user_firebase is defined in auth_dependency.py
# and is needed for protected routes
from app.auth.auth_dependency import get_current_user_firebase

logger = logging.getLogger("accessibility_analyzer_backend.auth_routes")

# Initialize APIRouter
router = APIRouter()

# Example: A simple test endpoint to verify Firebase token
@router.get("/me", summary="Get current authenticated user's Firebase UID and email")
async def read_current_user(current_user: dict = Depends(get_current_user_firebase)):
    """
    Retrieves the authenticated user's UID and email.
    Requires a valid Firebase ID Token in the Authorization header.
    """
    logger.info(f"Access granted for user: {current_user.get('uid')}")
    return {"message": "Authenticated successfully", "user": current_user}

# Example: Endpoint for token verification (often not needed as a direct endpoint,
# but good for explicit testing or if you had a custom login flow)
@router.post("/verify-token", summary="Verify a Firebase ID Token")
async def verify_firebase_token(id_token: str):
    """
    Verifies a Firebase ID Token and returns the decoded token payload.
    """
    try:
        decoded_token = auth.verify_id_token(id_token)
        logger.info(f"Token verified for user: {decoded_token.get('uid')}")
        return {"message": "Token verified successfully", "decoded_token": decoded_token}
    except FirebaseError as e:
        logger.error(f"Firebase token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}"
        )
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during token verification."
        )

# Add other authentication-related endpoints here as needed (e.g., password reset, email verification, if not handled by Firebase client-side)