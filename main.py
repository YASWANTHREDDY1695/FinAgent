from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import auth, profile, analysis
import uvicorn

app = FastAPI(
    title="FinAgent Pro",
    description="Multi-Agent AI Powered Personalized Financial Advisor Backend",
    version="1.0.0"
)

# CORS middleware for allowing frontend to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(analysis.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to FinAgent Pro API"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
