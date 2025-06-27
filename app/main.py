# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import analyze

app = FastAPI(
    title="Accessibility Analyzer API",
    description="API for analyzing web page accessibility and providing fix suggestions.",
    version="0.1.0"
)

# Configure CORS
# Ensure this list explicitly includes the origin of your frontend application.
# http://localhost:5173 is the default for Vite dev server.
origins = [
    "http://localhost",
    "http://localhost:3000", # Still useful if you switch to Create React App or other port
    "http://localhost:5173", # CRITICAL: This line must be present for Vite frontend
    # Add your Vercel frontend URL here when deployed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"], # Allows all standard HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"], # Allows all headers from the client
)

# Include API routers
app.include_router(analyze.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Accessibility Analyzer API is running!"}
