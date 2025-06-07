import os
import uuid
import re
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from fastapi.exception_handlers import http_exception_handler
from dotenv import load_dotenv
from sqlalchemy.orm import Session
import json
from typing import Optional, List, Dict, Any

# Import models and services
from .database import get_db, get_or_create_user, get_user_usage_stats
from .models import (
    ArticleRequest,
    ValidationRequest,
    ModelCostRequest,
    ArticleResponse,
    ValidationResponse,
    ModelCostResponse,
    ModelsResponse,
    UserUsageResponse,
)
from .services import OpenRouterService, ArticleService, CostService

# Initialize FastAPI app
app = FastAPI(
    title="Content Writer AI API",
    description="API for generating and validating content using LLMs",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Configure JSONResponse to preserve newlines and markdown formatting in responses
class MarkdownJSONResponse(JSONResponse):
    media_type = "application/json"

    def __init__(
        self,
        content: Any,
        status_code: int = 200,
        headers: Optional[Dict[str, str]] = None,
        media_type: Optional[str] = None,
        background: Optional[Any] = None,
    ) -> None:
        headers = headers or {}
        headers["Content-Type"] = "application/json; charset=utf-8"
        super().__init__(content, status_code, headers, media_type, background)

    def render(self, content: Any) -> bytes:
        # Custom JSON encoder that preserves newlines and markdown formatting
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=True,
            indent=None,
            separators=(",", ":"),
        ).encode("utf-8")


# Custom exception handler class to sanitize error messages
class SanitizedHTTPException(HTTPException):
    """
    A custom HTTP exception that sanitizes error messages to remove sensitive information
    like model IDs before sending to clients.
    """

    def __init__(
        self,
        status_code: int = 500,
        detail: Any = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> None:
        # Sanitize the error message if it's from OpenRouter
        if detail and isinstance(detail, str):
            # Check if this is an OpenRouter error
            if "Error code: " in detail:
                # Sanitize the error message to remove model IDs
                detail = self._sanitize_error(detail)

        super().__init__(status_code=status_code, detail=detail, headers=headers)

    def _sanitize_error(self, error_message: str) -> str:
        """
        Sanitize error messages to remove sensitive information like model IDs.
        """
        # Generic sanitized messages based on error types
        if "Developer instruction is not enabled" in error_message:
            return "The selected model does not support advanced instructions. Please try another model."

        if "No endpoints found" in error_message:
            return (
                "The selected model is currently unavailable. Please try another model."
            )

        if "not enabled for" in error_message and "models/" in error_message:
            return "This feature is not enabled for the selected model. Please try another model."

        # Remove any references to specific model IDs
        # Pattern to match model IDs like "models/xyz-123" or "model/gemma-123"
        model_id_pattern = r"models?/[a-zA-Z0-9_\-]+(?:[:/][a-zA-Z0-9_\-]+)*"
        sanitized = re.sub(model_id_pattern, "the selected model", error_message)

        # If we have JSON error messages, try to extract just the main error message
        if "{" in sanitized and "message" in sanitized:
            try:
                # Try to parse as JSON
                error_data = json.loads(sanitized)
                if isinstance(error_data, dict) and "error" in error_data:
                    if (
                        isinstance(error_data["error"], dict)
                        and "message" in error_data["error"]
                    ):
                        return error_data["error"]["message"]
            except:
                pass  # If JSON parsing fails, continue with the sanitized string

        # If we still have references to OpenRouter
        if "openrouter" in sanitized.lower() or "provider_name" in sanitized:
            return "An error occurred with the language model service. Please try again later or select a different model."

        return sanitized


# Check for OpenRouter API key
if not os.getenv("OPENROUTER_API_KEY"):
    print("Warning: OPENROUTER_API_KEY not found in environment variables")


# Initialize database and seed data on startup
@app.on_event("startup")
async def startup_db_client():
    from .database import init_db, seed_models

    init_db()
    db = next(get_db())
    try:
        seed_models(db)
    finally:
        db.close()
    print("Database initialized and seeded successfully")


# API endpoints are defined below


# API endpoints
@app.get("/")
async def root():
    """Root endpoint - API info"""
    return {"message": "Content Writer AI API"}


@app.get("/models", response_class=MarkdownJSONResponse)
async def get_models(db: Session = Depends(get_db)):
    """Get available models"""
    try:
        models = await OpenRouterService.get_models(db)
        return {"models": models}
    except Exception as e:
        raise SanitizedHTTPException(status_code=500, detail=str(e))


@app.post("/generate-article", response_class=MarkdownJSONResponse)
async def generate_article(request: ArticleRequest, db: Session = Depends(get_db)):
    """Generate an article based on title, details, tone, and other parameters"""
    try:
        # Get or create user
        user = get_or_create_user(
            db, user_id=str(request.user_id) if request.user_id else None
        )

        # Generate article
        result = await ArticleService.generate_article(
            title=request.title,
            details=request.details,
            tone=request.tone,
            llm_model=request.id,
            word_count=request.word_count,
            promotion_content=request.promotion_content,
            negative_content=request.negative_content,
            db=db,
            user_id=user.id,
        )
        return result
    except ValueError as e:
        raise SanitizedHTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise SanitizedHTTPException(status_code=500, detail=str(e))


@app.post("/validate-content", response_class=MarkdownJSONResponse)
async def validate_content(request: ValidationRequest, db: Session = Depends(get_db)):
    """Validate and improve article content based on evaluation metrics"""
    try:
        # Get or create user
        user = get_or_create_user(
            db, user_id=str(request.user_id) if request.user_id else None
        )

        result = await ArticleService.validate_content(
            article_content=request.article_content,
            evaluation_metrics=request.evaluation_metrics,
            llm_model=request.id,
            db=db,
            user_id=user.id,
        )

        # Ensure the response format matches ValidationResponse model
        response = {
            "evaluation": result.get("evaluation", ""),
            "edited_article": result.get("edited_article"),
            "token_usage": result.get(
                "token_usage",
                {"input_tokens": 0, "output_tokens": 0, "total_tokens": 0},
            ),
        }

        return response
    except ValueError as e:
        raise SanitizedHTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise SanitizedHTTPException(status_code=500, detail=str(e))


@app.post("/calculate-cost", response_class=MarkdownJSONResponse)
async def calculate_cost(request: ModelCostRequest, db: Session = Depends(get_db)):
    """Calculate the cost of using a model based on token usage"""
    try:
        # Get or create user
        user = get_or_create_user(
            db, user_id=str(request.user_id) if request.user_id else None
        )

        result = await CostService.calculate_cost(
            model_id=request.id,
            input_tokens=request.input_tokens,
            output_tokens=request.output_tokens,
            db=db,
            user_id=user.id,
        )
        return result
    except ValueError as e:
        raise SanitizedHTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise SanitizedHTTPException(status_code=500, detail=str(e))


@app.get("/user/{user_id}/usage", response_class=MarkdownJSONResponse)
async def get_user_usage(user_id: str, db: Session = Depends(get_db)):
    """Get usage statistics for a user"""
    try:
        usage_stats = get_user_usage_stats(db, user_id)
        return {"usage_stats": usage_stats}
    except ValueError as e:
        raise SanitizedHTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise SanitizedHTTPException(status_code=500, detail=str(e))


# Run the application
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


# Add global exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to catch any unhandled exceptions"""
    error_msg = str(exc)

    # Check for database connection errors
    if "OperationalError" in error_msg and any(
        db_error in error_msg for db_error in ["connection", "SSL", "timeout", "reset"]
    ):
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Database service temporarily unavailable. Please try again later."
            },
        )

    # For all other errors, use the SanitizedHTTPException
    sanitized_exc = SanitizedHTTPException(status_code=500, detail=error_msg)
    return JSONResponse(
        status_code=sanitized_exc.status_code,
        content={"detail": sanitized_exc.detail},
    )
