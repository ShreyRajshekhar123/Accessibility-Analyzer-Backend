from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import analyze

app = FastAPI(
    title="Accessibility Analyzer API",
    description="API for analyzing web page accessibility and providing fix suggestions.",
    version="0.1.0"
)

# Configure CORS
origins = [
    "http://localhost",
    "http://localhost:3000", # Assuming your frontend will run on port 3000
    # Add your Vercel frontend URL here when deployed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(analyze.router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Accessibility Analyzer API is running!"}