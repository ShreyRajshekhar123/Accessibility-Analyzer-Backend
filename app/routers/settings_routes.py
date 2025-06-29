# backend/app/routers/settings_routes.py

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Dict, Optional

# Import the Firebase authentication dependency
from app.auth.auth_dependency import get_current_user_firebase
import logging

logger = logging.getLogger("accessibility_analyzer_backend.settings_routes")

router = APIRouter()

# --- Pydantic Models for Settings ---
class UserSettings(BaseModel):
    """
    Pydantic model for user-specific settings.
    Define all settings fields here with their types and default values.
    """
    emailNotifications: bool = Field(default=False, description="Whether the user wishes to receive email notifications.")
    theme: str = Field(default="System Default", description="The preferred display theme (Light, Dark, System Default).")
    # Add any other settings here, e.g.:
    # preferred_language: str = Field(default="en", description="User's preferred language.")
    # accessibility_mode: bool = Field(default=False, description="Enable high contrast or other accessibility features.")

# --- Temporary/Mock Database for User Settings ---
# IMPORTANT: In a real application, you would replace this with actual database queries
# (e.g., MongoDB operations via app.database.connection or a dedicated ORM).
# This dictionary simulates storing settings by user_id.
mock_user_settings_db: Dict[str, UserSettings] = {}

# --- API Endpoints for Settings ---

@router.get("/settings", response_model=UserSettings)
async def get_user_settings(current_user: dict = Depends(get_current_user_firebase)):
    """
    Retrieves the settings for the authenticated user.
    If no settings are found, default settings are returned.
    """
    user_id = current_user["uid"]
    logger.info(f"Fetching settings for user: {user_id}")

    # Simulate fetching from a database
    settings = mock_user_settings_db.get(user_id)

    if not settings:
        logger.info(f"No settings found for user {user_id}, returning defaults.")
        # If no settings exist for the user, return the default values from the Pydantic model
        return UserSettings() # This will create an instance with default values

    return settings

@router.put("/settings", response_model=UserSettings)
async def update_user_settings(
    settings_data: UserSettings, # FastAPI will automatically parse the request body into this Pydantic model
    current_user: dict = Depends(get_current_user_firebase)
):
    """
    Updates the settings for the authenticated user.
    """
    user_id = current_user["uid"]
    logger.info(f"Updating settings for user: {user_id} with data: {settings_data.dict()}")

    # Simulate saving to a database
    mock_user_settings_db[user_id] = settings_data

    logger.info(f"Settings for user {user_id} saved successfully.")
    return settings_data