# backend/app/auth/auth_dependency.py

from fastapi import Header, HTTPException, status
from typing import Optional
import firebase_admin
from firebase_admin import auth
import logging
import traceback

logger = logging.getLogger("accessibility_analyzer_backend.auth.dependency")

async def get_current_user_firebase(authorization: Optional[str] = Header(None)):
    """
    FastAPI dependency to authenticate a user by verifying the Firebase ID token
    from the 'Authorization: Bearer <token>' header.
    Returns a dictionary containing the user's UID and the full decoded token.
    """
    # Check if Firebase Admin SDK is initialized.
    # It should be initialized in main.py's startup event.
    if not firebase_admin._apps:
        logger.error("Firebase Admin SDK not initialized. Cannot verify token. Please check backend startup logs.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication service not available. Please try again later."
        )

    if not authorization:
        logger.warning("Missing Authorization header in request.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing. Please provide a Firebase ID token."
        )

    try:
        scheme, token = authorization.split(" ")
        if scheme.lower() != "bearer":
            logger.warning(f"Invalid Authorization scheme: '{scheme}'. Expected 'Bearer'.")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme. Must be 'Bearer'."
            )
        
        logger.debug(f"Attempting to verify token (first 50 chars): {token[:50]}...")
        
        decoded_token = auth.verify_id_token(token)
        uid = decoded_token["uid"]

        logger.info(f"Firebase token successfully verified for user: {uid}")
        logger.debug(f"Decoded Token Payload for {uid}: {decoded_token}")
        
        return {"uid": uid, "decoded_token": decoded_token}

    except ValueError as ve:
        logger.warning(f"Invalid Authorization header format: {authorization}. Detail: {ve}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid Authorization header format. Detail: {ve}"
        )
    except auth.InvalidIdTokenError as firebase_auth_error:
        logger.warning(f"Invalid or expired Firebase ID token received. Firebase Error: {firebase_auth_error}")
        if "expired" in str(firebase_auth_error).lower():
            detail_message = "Your authentication session has expired. Please log in again."
        elif "signature" in str(firebase_auth_error).lower():
            detail_message = "Authentication token signature is invalid. Please ensure correct service account configuration."
        else:
            detail_message = f"Invalid or expired authentication token. Please log in again. Detail: {firebase_auth_error}"

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail_message
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred during Firebase token verification: {e}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during authentication. Detail: {e}"
        )