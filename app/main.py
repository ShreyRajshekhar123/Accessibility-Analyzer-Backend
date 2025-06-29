# backend/app/main.py (Updated by AI)

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient # This import might not be directly used here if connection is abstracted
from typing import List, Optional
import logging
import os
from dotenv import load_dotenv
import sys
import firebase_admin
from firebase_admin import credentials, auth
import traceback
from bson import ObjectId

# Load environment variables at the very beginning
load_dotenv()

# --- Local imports ---
# Assuming these modules exist in backend/app/
# config.py is correctly imported as it's directly in 'app/'
from app.config import settings

# IMPORTANT: Corrected the import for analyze_router as per your structure
from app.api.analyze import router as analyze_router

# --- AUTHENTICATION DEPENDENCY AND DATABASE HANDLERS ---
# We need to import the specific function from auth.auth_dependency
# and the global database connection handlers.

# Explicitly import the authentication function
try:
    from app.auth.auth_dependency import get_current_user_firebase
    # Assign it directly to `auth_dependency` which is used by Depends elsewhere
    # This needs to be a FastAPI Dependency, so it's `Depends(get_current_user_firebase)`
    # where it's used. We don't need a global `auth_dependency` variable here for that.
    # The `analyze.py` already directly uses `Depends(get_current_user_firebase)`.
    pass # No need for a direct assignment here anymore, just import it
except ImportError:
    logging.warning("Could not import get_current_user_firebase from app.auth.auth_dependency. This will cause issues if authentication is required.")
    # If it's truly critical and the app shouldn't start without it, sys.exit(1) here.


# Explicitly import database connection functions
try:
    from app.database.connection import close_mongo_connection, connect_to_mongo
except ImportError:
    logging.critical("CRITICAL: Could not import MongoDB connection handlers from app.database.connection. Database operations will fail.")
    # Define dummy functions to prevent app from crashing immediately, but alert developer
    async def connect_to_mongo(): logging.critical("Dummy connect_to_mongo called. MongoDB connection NOT established.")
    async def close_mongo_connection(): logging.warning("Dummy close_mongo_connection called.")


# Explicitly import logging setup
try:
    from app.utils import setup_logging
    setup_logging() # Call your logging setup from utils.py once imported
except ImportError:
    logging.warning("Could not import setup_logging from app.utils. Basic logging will be used.")
    logging.basicConfig(level=logging.INFO) # Fallback to basic logging


# Placeholder imports for other routers if they exist
auth_routes_router = None
report_routes_router = None
# --- NEW: Declare settings_routes_router here as None initially ---
settings_routes_router = None

try:
    from app.routers import auth_routes
    if hasattr(auth_routes, 'router'):
        auth_routes_router = auth_routes.router
    else:
        logging.warning("app.routers.auth_routes imported, but no 'router' attribute found. Skipping its inclusion.")
except ImportError as e:
    logging.warning(f"Could not import optional router 'auth_routes' from app.routers: {e}. If this is not yet created, ignore this warning.")

try:
    from app.routers import report_routes
    if hasattr(report_routes, 'router'):
        report_routes_router = report_routes.router
    else:
        logging.warning("app.routers.report_routes imported, but no 'router' attribute found. Skipping its inclusion.")
except ImportError as e:
    logging.warning(f"Could not import optional router 'report_routes' from app.routers: {e}. If this is not yet created, ignore this warning.")

# --- NEW: Import settings_routes ---
try:
    from app.routers import settings_routes
    if hasattr(settings_routes, 'router'):
        settings_routes_router = settings_routes.router
    else:
        logging.warning("app.routers.settings_routes imported, but no 'router' attribute found. Skipping its inclusion.")
except ImportError as e:
    logging.warning(f"Could not import optional router 'settings_routes' from app.routers: {e}. If this is not yet created, ignore this warning.")


# --- Global Logger Configuration ---
# Logger for the main application file
logger = logging.getLogger("accessibility_analyzer_backend.main") # Specific logger for main.py


# --- FastAPI App Definition ---
app = FastAPI(
    title="Accessibility Analyzer API",
    description="API for analyzing web page accessibility and providing fix suggestions.",
    version="1.0.0",
    response_model_by_alias=True
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS, # Directly uses list from settings
    allow_credentials=True,
    allow_methods=["*"], # Allows GET, POST, PUT, DELETE, OPTIONS, etc.
    allow_headers=["*"], # Allows all headers from the client
)

# --- Custom JSON Encoder for ObjectId ---
# This ensures that any ObjectId that escapes Pydantic models (e.g., in a raw dict response)
# is properly converted to a string. Pydantic's handling via PyObjectId is preferred,
# but this is a good safety net.
app.json_encoders = {
    ObjectId: str
}

# --- Startup and Shutdown Events ---

@app.on_event("startup")
async def startup_event():
    logger.info("Accessibility Analyzer API is starting up...")

    # --- Firebase Admin SDK Initialization ---
    firebase_service_account_path_env = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
    app_directory = os.path.dirname(os.path.abspath(__file__))
    backend_root_dir = os.path.dirname(app_directory) # This is `backend/`

    full_service_account_path = ""

    if firebase_service_account_path_env:
        # Path specified in .env is relative to the backend root (where uvicorn is often run from)
        full_service_account_path = os.path.join(backend_root_dir, firebase_service_account_path_env)
    else:
        # Default: assume it's in the 'app' directory (where main.py resides)
        full_service_account_path = os.path.join(app_directory, "firebase-service-account.json")

    full_service_account_path = os.path.normpath(full_service_account_path)

    logger.info(f"Attempting to load Firebase service account from: {full_service_account_path}")

    try:
        if not os.path.exists(full_service_account_path):
            raise FileNotFoundError(f"Firebase service account file not found at: {full_service_account_path}. "
                                     "Please ensure it's in the 'backend/app/' directory or update FIREBASE_SERVICE_ACCOUNT_PATH "
                                     "in .env to a correct relative path from the 'backend/' directory.")

        cred = credentials.Certificate(full_service_account_path)
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized successfully.")
    except FileNotFoundError as e:
        logger.critical(f"CRITICAL - Firebase Service Account File Error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1) # Exit application if Firebase init fails
    except Exception as e:
        logger.critical(f"CRITICAL - Failed to initialize Firebase Admin SDK: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1) # Exit application if Firebase init fails

    # --- MongoDB Connection ---
    await connect_to_mongo()


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Accessibility Analyzer API is shutting down.")
    # --- MongoDB Disconnection ---
    await close_mongo_connection()

# --- Include API routers ---
# These are the routers that define your API endpoints

# Always include the analyze_router as it is provided and essential
app.include_router(analyze_router, prefix="/api", tags=["Analysis"])

# Only include other routers if they were successfully imported and have a 'router' attribute
if auth_routes_router:
    app.include_router(auth_routes_router, prefix="/api/auth", tags=["Authentication"])
if report_routes_router:
    app.include_router(report_routes_router, prefix="/api", tags=["Reports"])
# --- NEW: Include settings_routes_router ---
if settings_routes_router:
    app.include_router(settings_routes_router, prefix="/api", tags=["Settings"])


@app.get("/")
async def read_root():
    logger.info("API root endpoint hit.")
    return {"message": "Accessibility Analyzer API is running!"}