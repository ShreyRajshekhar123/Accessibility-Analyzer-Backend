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
from bson import ObjectId # Still import ObjectId, though app.json_encoders will be removed

# --- CRITICAL: Load environment variables at the very beginning ---
load_dotenv()

# Debug prints (keep these as they are not sensitive, but consider changing to logger.debug in production)
print(f"DEBUG: MONGODB_URI from env: {os.getenv('MONGODB_URI')}")
print(f"DEBUG: MONGODB_DB_NAME from env: {os.getenv('MONGODB_DB_NAME')}")
print(f"DEBUG: GEMINI_API_KEY from env: {os.getenv('GEMINI_API_KEY')}")

# --- IMPORTANT: Explicitly ensure Pydantic-settings sees these variables ---
# This step is crucial because Uvicorn's reloader or specific characters
# might prevent pydantic-settings from fully parsing the .env file directly.
# By assigning them to os.environ, we guarantee pydantic-settings finds them.
# This assumes settings.py reads from os.environ.
if os.getenv('MONGODB_URI'):
    os.environ['MONGODB_URI'] = os.getenv('MONGODB_URI') 
if os.getenv('MONGODB_DB_NAME'):
    os.environ['MONGODB_DB_NAME'] = os.getenv('MONGODB_DB_NAME')
if os.getenv('GEMINI_API_KEY'):
    os.environ['GEMINI_API_KEY'] = os.getenv('GEMINI_API_KEY')
if os.getenv('FIREBASE_SERVICE_ACCOUNT_BASE64'):
    os.environ['FIREBASE_SERVICE_ACCOUNT_BASE64'] = os.getenv('FIREBASE_SERVICE_ACCOUNT_BASE64')


# --- Local imports ---
from app.config import settings
from app.database.connection import close_mongo_connection, connect_to_mongo
from app.auth.auth_dependency import get_current_user_firebase # Keep this import, it's used as a dependency

# Explicitly import logging setup
try:
    from app.utils import setup_logging
    setup_logging() # Call your logging setup from utils.py once imported
except ImportError:
    logging.warning("Could not import setup_logging from app.utils. Basic logging will be used.")
    logging.basicConfig(level=logging.INFO) # Fallback to basic logging

# --- FIX START: Correct Router Imports ---
# Directly import the 'router' object from each router file
# This assumes each router file defines a variable named 'router' that is an APIRouter instance.
try:
    from app.api.analyze import router as analyze_router
except ImportError as e:
    logging.critical(f"CRITICAL ERROR: Could not import analyze_router from app.api.analyze: {e}")
    sys.exit(1) # This router is essential, fail startup if it's missing

try:
    from app.routers.auth_routes import router as auth_router 
except ImportError as e:
    logging.warning(f"Could not import auth_router from app.routers.auth_routes: {e}. Authentication routes will not be available.")
    auth_router = None # Set to None if import fails, for conditional inclusion

try:
    from app.routers.report_routes import router as report_router 
except ImportError as e:
    logging.warning(f"Could not import report_router from app.routers.report_routes: {e}. Report routes will not be available.")
    report_router = None # Set to None if import fails, for conditional inclusion

try:
    from app.routers.settings_routes import router as settings_router 
except ImportError as e:
    logging.warning(f"Could not import settings_router from app.routers.settings_routes: {e}. Settings routes will not be available.")
    settings_router = None # Set to None if import fails, for conditional inclusion
# --- FIX END: Correct Router Imports ---


# --- Global Logger Configuration ---
logger = logging.getLogger("accessibility_analyzer_backend.main") # Specific logger for main.py


# --- FastAPI App Definition ---
app = FastAPI(
    title="Accessibility Analyzer API",
    description="API for analyzing web page accessibility and providing fix suggestions.",
    version="1.0.0",
    response_model_by_alias=True # Crucial for Pydantic models using alias (like _id to id)
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS, # Directly uses list from settings
    allow_credentials=True,
    allow_methods=["*"], # Allows GET, POST, PUT, DELETE, OPTIONS, etc.
    allow_headers=["*"], # Allows all headers from the client
)

# --- REMOVED: Custom JSON Encoder for ObjectId is no longer necessary with PyObjectId in Pydantic v2 ---
# app.json_encoders = {
#     ObjectId: str
# }

# --- Startup and Shutdown Events ---

@app.on_event("startup")
async def startup_event():
    logger.info("Accessibility Analyzer API is starting up...")

    # --- Firebase Admin SDK Initialization using Base64 ENCODED ENV VARIABLE ---
    firebase_service_account_base64 = settings.FIREBASE_SERVICE_ACCOUNT_BASE64 

    try:
        if firebase_service_account_base64:
            decoded_string = base64.b64decode(firebase_service_account_base64).decode('utf-8')
            service_account_info = json.loads(decoded_string)
            
            cred = credentials.Certificate(service_account_info)
            firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully using Base64 environment variable.")
        elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            # Fallback for environments where GOOGLE_APPLICATION_CREDENTIALS is set
            firebase_admin.initialize_app()
            logger.info("Firebase Admin SDK initialized using GOOGLE_APPLICATION_CREDENTIALS.")
        else:
            logger.critical("CRITICAL - FIREBASE_SERVICE_ACCOUNT_BASE64 environment variable not found or empty. "
                             "Firebase Admin SDK will not be initialized with service account credentials. "
                             "Please ensure one of these environment variables is set.")
            raise RuntimeError("Firebase service account key not configured. Cannot initialize Firebase Admin SDK.")

    except (ValueError, json.JSONDecodeError) as e:
        logger.critical(f"CRITICAL - Firebase Service Account Error: Invalid Base64 or JSON format in environment variable: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
    except FirebaseError as e:
        logger.critical(f"CRITICAL - Failed to initialize Firebase Admin SDK due to Firebase error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
    except Exception as e:
        logger.critical(f"CRITICAL - An unexpected error occurred during Firebase initialization: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)

    # --- MongoDB Connection ---
    await connect_to_mongo()


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Accessibility Analyzer API is shutting down.")
    # --- MongoDB Disconnection ---
    await close_mongo_connection()

# --- Include API routers ---
app.include_router(analyze_router, prefix="/api", tags=["Analysis"])

# Only include other routers if they were successfully imported (i.e., not None)
if auth_router:
    app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
if report_router:
    app.include_router(report_router, prefix="/api", tags=["Reports"])
if settings_router:
    app.include_router(settings_router, prefix="/api", tags=["Settings"])


@app.get("/")
async def read_root():
    logger.info("API root endpoint hit.")
    return {"message": "Accessibility Analyzer API is running!"}