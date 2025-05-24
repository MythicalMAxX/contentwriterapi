import os
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment variables
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost/contentwriterai"
)
print(f"Using database URL: {DATABASE_URL}")

# Create SQLAlchemy engine and session with SSL requirements for cloud databases
engine = sa.create_engine(
    DATABASE_URL, pool_size=5, max_overflow=10, pool_timeout=30, pool_recycle=1800
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()


# Database models
class User(Base):
    """User model for tracking API usage"""

    __tablename__ = "users"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = sa.Column(sa.String, unique=True, index=True)
    name = sa.Column(sa.String)
    created_at = sa.Column(sa.DateTime, server_default=func.now())
    updated_at = sa.Column(sa.DateTime, onupdate=func.now())


class AIModel(Base):
    """Model for storing AI model information"""

    __tablename__ = "ai_models"

    id = sa.Column(sa.String, primary_key=True)  # Model ID from OpenRouter
    name = sa.Column(sa.String, nullable=False)
    description = sa.Column(sa.Text)
    context_length = sa.Column(sa.Integer)
    input_price = sa.Column(sa.Float, default=0.0)  # Price per million tokens
    output_price = sa.Column(sa.Float, default=0.0)  # Price per million tokens
    is_free = sa.Column(sa.Boolean, default=False)
    capabilities = sa.Column(sa.JSON)
    recommended_for = sa.Column(sa.JSON)
    created_at = sa.Column(sa.DateTime, server_default=func.now())
    updated_at = sa.Column(sa.DateTime, onupdate=func.now())


class ModelIDMapping(Base):
    """Model for mapping display IDs to actual model IDs"""

    __tablename__ = "model_id_mappings"

    display_id = sa.Column(sa.String, primary_key=True)
    model_id = sa.Column(sa.String, sa.ForeignKey("ai_models.id"), nullable=False)
    created_at = sa.Column(sa.DateTime, server_default=func.now())


class APIUsage(Base):
    """Model for tracking API usage"""

    __tablename__ = "api_usage"

    id = sa.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = sa.Column(UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False)
    model_id = sa.Column(sa.String, sa.ForeignKey("ai_models.id"), nullable=False)
    endpoint = sa.Column(sa.String, nullable=False)  # Which API endpoint was called
    input_tokens = sa.Column(sa.Integer, default=0)
    output_tokens = sa.Column(sa.Integer, default=0)
    total_tokens = sa.Column(sa.Integer, default=0)
    input_cost = sa.Column(sa.Float, default=0.0)
    output_cost = sa.Column(sa.Float, default=0.0)
    total_cost = sa.Column(sa.Float, default=0.0)
    status = sa.Column(sa.String, default="success")  # success, error
    created_at = sa.Column(sa.DateTime, server_default=func.now())


# Database dependency
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Database initialization
def init_db():
    """Initialize database with tables"""
    Base.metadata.create_all(bind=engine)


# Seed initial model data
def seed_models(db: Session):
    """Seed initial model data"""
    # Check if models already exist
    if db.query(AIModel).count() > 0:
        return

    # Add initial free model - using Gemma instead of Qwen
    gemma_model = AIModel(
        id="google/gemma-3n-e4b-it:free",
        name="Gemma 3n 4B",
        description="Optimized for efficient execution on low-resource devices. Supports text generation with strong reasoning capabilities up to 2000 words.",
        context_length=8192,
        input_price=0.0,  # Free model
        output_price=0.0,  # Free model
        is_free=True,
        capabilities={"text": True, "image_input": False, "file_input": False},
        recommended_for=["Article writing", "Content creation", "Efficient drafting"],
    )

    db.add(gemma_model)
    db.commit()


# User management functions
def get_or_create_user(
    db: Session, user_id: Optional[str] = None, email: Optional[str] = None
) -> User:
    """Get or create a user"""
    # First, try to find an existing anonymous user
    # This handles the case where multiple anonymous users try to access at once
    if not user_id and not email:
        existing_anonymous = (
            db.query(User).filter(User.email == "anonymous@example.com").first()
        )
        if existing_anonymous:
            return existing_anonymous

    # Then try to get a user by ID if provided
    if user_id:
        try:
            user_uuid = uuid.UUID(user_id)
            user = db.query(User).filter(User.id == user_uuid).first()
            if user:
                return user
        except (ValueError, TypeError):
            # Invalid UUID format
            pass

    # Then try to get a user by email if provided
    if email:
        user = db.query(User).filter(User.email == email).first()
        if user:
            return user

    # Create new user with a unique email
    try:
        # For anonymous users, create a unique email to avoid conflicts
        if not email:
            unique_email = f"anon_{uuid.uuid4().hex[:8]}@example.com"
        else:
            unique_email = email

        new_user = User(email=unique_email)
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
        return new_user
    except Exception as e:
        db.rollback()
        # If creating a user fails, make a final attempt to get the anonymous user
        if not email:
            existing_anonymous = (
                db.query(User).filter(User.email.like("anon_%@example.com")).first()
            )
            if existing_anonymous:
                return existing_anonymous

        # If all else fails, raise the exception
        raise e


# API usage tracking
def log_api_usage(
    db: Session,
    user_id: uuid.UUID,
    model_id: str,
    endpoint: str,
    input_tokens: int,
    output_tokens: int,
    status: str = "success",
) -> APIUsage:
    """Log API usage"""
    # Get model pricing
    model = db.query(AIModel).filter(AIModel.id == model_id).first()
    if not model:
        # Use default pricing if model not found
        input_price = 0.0
        output_price = 0.0
    else:
        input_price = model.input_price
        output_price = model.output_price

    # Calculate costs
    input_cost = (
        input_tokens * input_price / 1000000
    )  # Convert from price per million tokens
    output_cost = (
        output_tokens * output_price / 1000000
    )  # Convert from price per million tokens
    total_cost = input_cost + output_cost

    # Create usage record
    usage = APIUsage(
        user_id=user_id,
        model_id=model_id,
        endpoint=endpoint,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=total_cost,
        status=status,
    )

    db.add(usage)
    db.commit()
    db.refresh(usage)
    return usage


# Model management
def get_free_models(db: Session) -> List[Dict[str, Any]]:
    """Get all free models"""
    models = db.query(AIModel).filter(AIModel.is_free == True).all()
    return [
        {
            "id": model.id,
            "name": model.name,
            "description": model.description,
            "context_length": model.context_length,
            "pricing": {"prompt": model.input_price, "completion": model.output_price},
            "capabilities": model.capabilities,
            "recommended_for": model.recommended_for,
        }
        for model in models
    ]


def get_model_by_id(db: Session, model_id: str) -> Optional[AIModel]:
    """Get model by ID"""
    return db.query(AIModel).filter(AIModel.id == model_id).first()


def get_model_by_display_id(db: Session, display_id: str) -> Optional[AIModel]:
    """Get model by display ID"""
    # Try to find in the mapping table
    mapping = (
        db.query(ModelIDMapping).filter(ModelIDMapping.display_id == display_id).first()
    )
    if mapping:
        return db.query(AIModel).filter(AIModel.id == mapping.model_id).first()

    # If not found, try to find directly in the models table (for backward compatibility)
    return db.query(AIModel).filter(AIModel.id == display_id).first()


def create_model_id_mapping(
    db: Session, display_id: str, model_id: str
) -> ModelIDMapping:
    """Create a mapping between display ID and actual model ID"""
    mapping = ModelIDMapping(display_id=display_id, model_id=model_id)
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


# Usage statistics
def get_user_usage_stats(db: Session, user_id: uuid.UUID) -> Dict[str, Any]:
    """Get usage statistics for a user"""
    # Get all usage records for the user
    usage_records = db.query(APIUsage).filter(APIUsage.user_id == user_id).all()

    # Calculate total usage
    total_tokens = sum(record.total_tokens for record in usage_records)
    total_cost = sum(record.total_cost for record in usage_records)

    # Group usage by model
    model_usage = {}
    for record in usage_records:
        if record.model_id not in model_usage:
            model_usage[record.model_id] = {
                "total_tokens": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "total_cost": 0.0,
            }

        model_usage[record.model_id]["total_tokens"] += record.total_tokens
        model_usage[record.model_id]["input_tokens"] += record.input_tokens
        model_usage[record.model_id]["output_tokens"] += record.output_tokens
        model_usage[record.model_id]["total_cost"] += record.total_cost

    # Add model names and display IDs
    result_model_usage = []
    for model_id, usage in model_usage.items():
        model = db.query(AIModel).filter(AIModel.id == model_id).first()

        # Find a display ID for this model
        mapping = (
            db.query(ModelIDMapping).filter(ModelIDMapping.model_id == model_id).first()
        )
        display_id = mapping.display_id if mapping else str(uuid.uuid4())

        # If model not found, use default name
        model_name = model.name if model else "Unknown Model"

        # Create result object with display ID instead of internal model ID
        result_usage = {
            "id": display_id,  # Use display ID for API responses
            "name": model_name,
            "total_tokens": usage["total_tokens"],
            "input_tokens": usage["input_tokens"],
            "output_tokens": usage["output_tokens"],
            "total_cost": usage["total_cost"],
        }
        result_model_usage.append(result_usage)

    return {
        "total_usage": {"total_tokens": total_tokens, "total_cost": total_cost},
        "model_usage": result_model_usage,
    }
