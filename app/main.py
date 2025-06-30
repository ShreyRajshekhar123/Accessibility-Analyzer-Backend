# backend/app/main.py

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient 
from typing import List, Optional
import logging
import os
from dotenv import load_dotenv
import sys
import base64 
import json 
import firebase_admin
from firebase_admin import credentials, auth
from firebase_admin.exceptions import FirebaseError
import traceback
from bson import ObjectId

# --- CRITICAL: Load environment variables at the very beginning ---
load_dotenv()

# Debug prints (keep these as they are not sensitive)
print(f"DEBUG: MONGO_URI from env: {os.getenv('MONGODB_URI')}")
print(f"DEBUG: MONGO_DB_NAME from env: {os.getenv('MONGODB_DB_NAME')}")
print(f"DEBUG: GEMINI_API_KEY from env: {os.getenv('GEMINI_API_KEY')}")
# Removed the debug print for FIREBASE_SERVICE_ACCOUNT_BASE64 for security


# --- IMPORTANT: Explicitly ensure Pydantic-settings sees these variables ---
# This step is crucial because Uvicorn's reloader or specific characters
# might prevent pydantic-settings from fully parsing the .env file directly.
# By assigning them to os.environ, we guarantee pydantic-settings finds them.
if os.getenv('MONGO_URI'):
    # Note: MONGO_URI in .env maps to MONGODB_URI in config.py
    os.environ['MONGODB_URI'] = os.getenv('MONGO_URI') 
if os.getenv('MONGO_DB_NAME'):
    os.environ['MONGODB_DB_NAME'] = os.getenv('MONGO_DB_NAME')
if os.getenv('GEMINI_API_KEY'):
    os.environ['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY')
if os.getenv('FIREBASE_SERVICE_ACCOUNT_BASE64'):
    os.environ['FIREBASE_SERVICE_ACCOUNT_BASE64'] = os.getenv('FIREBASE_SERVICE_ACCOUNT_BASE64')


# --- Local imports ---
# config.py is correctly imported as it's directly in 'app/'
from app.config import settings

# Corrected the import for analyze_router as per your structure
from app.api.analyze import router as analyze_router

# --- AUTHENTICATION DEPENDENCY AND DATABASE HANDLERS ---
# We need to import the specific function from auth.auth_dependency
# and the global database connection handlers.

# Explicitly import the authentication function
try:
    from app.auth.auth_dependency import get_current_user_firebase
    # No need for a direct assignment here anymore, just import it
    pass
except ImportError:
    logging.warning("Could not import get_current_user_firebase from app.auth.auth_dependency. This will cause issues if authentication is required.")


# Explicitly import database connection functions
# --- START OF CHANGE ---
# REMOVED THE try...except ImportError BLOCK HERE
# The assumption is that app.database.connection is now importable
from app.database.connection import close_mongo_connection, connect_to_mongo
# --- END OF CHANGE ---

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
settings_routes_router = None # Declare settings_routes_router here as None initially

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

# --- Import settings_routes ---
try:
    from app.routers import settings_routes
    if hasattr(settings_routes, 'router'):
        settings_routes_router = settings_routes.router
    else:
        logging.warning("app.routers.settings_routes imported, but no 'router' attribute found. Skipping its inclusion.")
except ImportError as e:
    logging.warning(f"Could not import optional router 'settings_routes' from app.routers: {e}. If this is not yet created, ignore this warning.")


# --- Global Logger Configuration ---
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
app.json_encoders = {
    ObjectId: str
}

# --- Startup and Shutdown Events ---

@app.on_event("startup")
async def startup_event():
    logger.info("Accessibility Analyzer API is starting up...")

    # --- Firebase Admin SDK Initialization using Base64 ENCODED ENV VARIABLE ---
    # Now reading from settings, which relies on os.environ being correctly populated
    firebase_service_account_base64 = settings.FIREBASE_SERVICE_ACCOUNT_BASE64 

    try:
        if firebase_service_account_base64:
            # Decode the Base64 string
            decoded_string = base64.b64decode(firebase_service_account_base64).decode('utf-8')
            # Parse the JSON string
            service_account_info = json.loads(decoded_string)
            
            # Initialize Firebase Admin SDK with the service account
            cred = credentials.Certificate(service_account_info)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully using Base64 environment variable.")
        elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            # This path is for Google Cloud environments or local dev with GOOGLE_APPLICATION_CREDENTIALS path
            firebase_admin.initialize_app() # Uses application default credentials
            logger.info("Firebase Admin SDK initialized using GOOGLE_APPLICATION_CREDENTIALS.")
        else:
            logger.critical("CRITICAL - FIREBASE_SERVICE_ACCOUNT_BASE64 environment variable not found or empty. "
                             "Firebase Admin SDK will not be initialized with service account credentials.")
            # It's usually better to raise an exception and let FastAPI handle startup failure
            raise RuntimeError("Firebase service account key not configured. Cannot initialize Firebase Admin SDK.")

    except (ValueError, json.JSONDecodeError) as e:
        logger.critical(f"CRITICAL - Firebase Service Account Error: Invalid Base64 or JSON format in environment variable: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1) # Exit application if Firebase init fails
    except FirebaseError as e:
        logger.critical(f"CRITICAL - Failed to initialize Firebase Admin SDK due to Firebase error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1) # Exit application if Firebase init fails
    except Exception as e:
        logger.critical(f"CRITICAL - An unexpected error occurred during Firebase initialization: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1) # Exit application if Firebase init fails

    # --- MongoDB Connection ---
    # --- START OF CHANGE ---
    # connect_to_mongo in connection.py gets its values from os.getenv, so no arguments are needed here.
    await connect_to_mongo() # This is the correct call
    # --- END OF CHANGE ---


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
# Include settings_routes_router
if settings_routes_router:
    app.include_router(settings_routes_router, prefix="/api", tags=["Settings"])


@app.get("/")
async def read_root():
    logger.info("API root endpoint hit.")
    return {"message": "Accessibility Analyzer API is running!"}