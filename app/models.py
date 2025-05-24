from pydantic import BaseModel, Field, UUID4
from typing import List, Optional, Dict, Any
import uuid


# Request Models
class ArticleRequest(BaseModel):
    """Request model for article generation"""

    user_id: Optional[UUID4] = Field(
        None, description="UUID of the user making the request"
    )
    title: str = Field(..., description="The title of the article")
    details: str = Field(
        ..., description="Additional instructions regarding the article"
    )
    tone: str = Field(
        ..., description="Writing format/tone that the model should follow"
    )
    promotion_content: Optional[str] = Field(
        None, description="Service, product, or company to promote within the article"
    )
    id: str = Field(
        ..., description="The ID of the model to use for generating the article"
    )
    word_count: int = Field(
        ..., gt=0, description="The target word count for the article"
    )
    negative_content: Optional[str] = Field(
        None, description="Content to avoid mentioning in the article"
    )


class ValidationRequest(BaseModel):
    """Request model for content validation"""

    user_id: Optional[UUID4] = Field(
        None, description="UUID of the user making the request"
    )
    article_content: str = Field(
        ..., description="The generated article content to validate"
    )
    evaluation_metrics: List[str] = Field(
        ..., description="Metrics to use for evaluating the content"
    )
    id: str = Field(..., description="The ID of the model to use for validation")


class ModelCostRequest(BaseModel):
    """Request model for calculating model usage cost"""

    user_id: Optional[UUID4] = Field(
        None, description="UUID of the user making the request"
    )
    id: str = Field(..., description="The ID of the model to calculate cost for")
    input_tokens: int = Field(..., gt=0, description="Number of input tokens used")
    output_tokens: int = Field(
        ..., gt=0, description="Number of output tokens generated"
    )


# Response Models
class TokenUsage(BaseModel):
    """Token usage information"""

    input_tokens: int
    output_tokens: int
    total_tokens: int


class ArticleResponse(BaseModel):
    """Response model for article generation"""

    article: str
    word_count: int
    token_usage: TokenUsage


class ValidationResponse(BaseModel):
    """Response model for content validation"""

    evaluation: str
    edited_article: Optional[str] = Field(
        None, description="The complete edited article if available"
    )
    token_usage: TokenUsage


class ModelCostResponse(BaseModel):
    """Response model for model cost calculation"""

    id: str  # Display ID of the model
    name: str  # Name of the model
    input_tokens: int
    output_tokens: int
    total_tokens: int
    input_cost: float
    output_cost: float
    total_cost: float
    currency: str = "USD"


class ModelCapabilities(BaseModel):
    """Model capabilities information"""

    text: bool = True
    image_input: bool = False
    file_input: bool = False


class ModelInfo(BaseModel):
    """Enhanced model information"""

    id: str  # The public ID shown to users (actually the display_id internally)
    name: str
    description: Optional[str] = None
    context_length: Optional[int] = None
    pricing: Dict[str, float] = Field(default_factory=dict)
    capabilities: ModelCapabilities
    recommended_for: List[str] = Field(default_factory=list)
    is_free: bool = False


class ModelsResponse(BaseModel):
    """Response model for available models"""

    models: List[ModelInfo]


# User Models
class UserUsageResponse(BaseModel):
    """Response model for user usage statistics"""

    total_usage: Dict[str, Any]
    model_usage: List[Dict[str, Any]]
