from fastapi import FastAPI

app = FastAPI(
    title="Content Writer AI API",
    description="API for generating and validating content using LLMs",
    version="1.0.0",
)

@app.get("/")
async def root():
    """Root endpoint - API info"""
    return {
        "message": "Content Writer AI API is running on Vercel!",
        "status": "success",
        "version": "1.0.0",
        "endpoints": {
            "root": "/",
            "models": "/models",
            "generate": "/generate-article",
            "validate": "/validate-content",
            "cost": "/calculate-cost",
            "usage": "/user-usage"
        }
    }

@app.get("/models")
async def get_models():
    """Get available models"""
    return {
        "models": [
            "openai/gpt-4o-mini",
            "openai/gpt-4o", 
            "anthropic/claude-3.5-sonnet",
            "google/gemini-pro-1.5"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "API is running"}
