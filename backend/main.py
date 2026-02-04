"""
FX Simple - Currency Monitor Backend
A simplified FX monitoring application with AI analysis
"""

from dotenv import load_dotenv
import os

# Load .env file from parent directory
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

from backend.routes import rates, interest, ai

app = FastAPI(
    title="FX Simple API",
    description="Simple FX monitoring with AI analysis",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(rates.router, prefix="/api/rates", tags=["Rates"])
app.include_router(interest.router, prefix="/api/interest-rates", tags=["Interest Rates"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI Analysis"])

# Serve frontend
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")

@app.get("/")
async def serve_frontend():
    return FileResponse(os.path.join(frontend_path, "index.html"))

# Mount static files
app.mount("/css", StaticFiles(directory=os.path.join(frontend_path, "css")), name="css")
app.mount("/js", StaticFiles(directory=os.path.join(frontend_path, "js")), name="js")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
