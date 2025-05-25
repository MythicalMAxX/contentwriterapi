import os
import uuid
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
import httpx
import openai

from .utils import (
    count_tokens,
    create_article_prompt,
    create_validation_prompt,
    enhance_model_info,
)
from .database import (
    get_model_by_id,
    get_model_by_display_id,
    get_free_models,
    log_api_usage,
    get_or_create_user,
    create_model_id_mapping,
)

# Get OpenRouter API key from environment variables
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Base URL for OpenRouter API
OPENROUTER_API_URL = "https://openrouter.ai/api/v1"

# Configure OpenAI client for OpenRouter with increased timeout
try:
    client = openai.OpenAI(
        base_url=OPENROUTER_API_URL,
        api_key=OPENROUTER_API_KEY,
        default_headers={
            "HTTP-Referer": "https://cwapi-dmgma3hjf3becxhf.canadacentral-01.azurewebsites.net/",  # Replace with your actual domain
        },
        timeout=httpx.Timeout(
            300.0, connect=60.0
        ),  # 5 minutes total timeout, 60 seconds for connection
    )
except TypeError as e:
    # If there's a TypeError about unexpected keyword arguments, it might be related to proxies
    if "got an unexpected keyword argument 'proxies'" in str(e):
        # Create client without httpx parameters
        client = openai.OpenAI(
            base_url=OPENROUTER_API_URL,
            api_key=OPENROUTER_API_KEY,
            default_headers={
                "HTTP-Referer": "https://cwapi-dmgma3hjf3becxhf.canadacentral-01.azurewebsites.net/",
            },
        )
    else:
        # Re-raise if it's a different TypeError
        raise


class OpenRouterService:
    """Service for interacting with OpenRouter API"""

    @staticmethod
    def calculate_max_tokens(model_id: str, word_count: int) -> int:
        """Calculate appropriate max_tokens based on model and word count"""
        # Base multiplier - tokens per word
        tokens_per_word = 2.5

        # Additional buffer for formatting and instructions
        base_buffer = 200

        # Calculate tokens based on word count
        calculated_tokens = int(word_count * tokens_per_word) + base_buffer

        # Set minimum token threshold to ensure complete responses
        min_tokens = 4000

        # Get model context limit if available
        model_context_limit = 8192  # Default for most models

        # Model-specific adjustments
        if "gemma" in model_id.lower():
            model_context_limit = 8192
        elif "claude-3" in model_id.lower():
            model_context_limit = 200000  # Claude 3 has a very large context
        elif "gpt-4" in model_id.lower():
            model_context_limit = 128000  # GPT-4 Turbo has large context
        elif "mistral" in model_id.lower() or "mixtral" in model_id.lower():
            model_context_limit = 32000

        # Ensure we don't exceed model's context limit
        # Reserve 1/3 of context for input, 2/3 for output
        max_output_tokens = int(model_context_limit * 2 / 3)

        # Return the appropriate token limit
        return max(min_tokens, min(calculated_tokens, max_output_tokens))

    @staticmethod
    async def make_request(
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        db: Optional[Session] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Make a request to the OpenRouter API using OpenAI SDK"""
        if not OPENROUTER_API_KEY:
            raise ValueError("OpenRouter API key not configured")

        try:
            # Make the request using OpenAI SDK
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Convert response to dict for consistent handling
            result = {
                "choices": [
                    {"message": {"content": response.choices[0].message.content}}
                ],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            }

            # Log API usage if database session is provided
            if db and user_id and response.usage:
                log_api_usage(
                    db=db,
                    user_id=user_id,
                    model_id=model,
                    endpoint="chat/completions",
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    status="success",
                )

            return result
        except Exception as e:
            error_str = str(e)

            # Log error if possible
            if db and user_id:
                # Don't include the raw error message in the database log
                log_api_usage(
                    db=db,
                    user_id=user_id,
                    model_id=model,
                    endpoint="chat/completions",
                    input_tokens=0,
                    output_tokens=0,
                    status="error",
                )

            # Format the error message for better client handling
            if (
                "model_not_found" in error_str.lower()
                or "no endpoints found" in error_str.lower()
            ):
                raise ValueError(
                    f"Error code: 404 - {{'error': {{'message': 'No endpoints found for the selected model.', 'code': 404}}, 'user_id': '{user_id}'}}"
                )
            elif (
                "not enabled" in error_str.lower() or "permission" in error_str.lower()
            ):
                raise ValueError(
                    f"Error code: 400 - {{'error': {{'message': 'The selected model does not support this feature', 'code': 400}}, 'user_id': '{user_id}'}}"
                )
            elif "rate limit" in error_str.lower():
                raise ValueError(
                    f"Error code: 429 - {{'error': {{'message': 'Rate limit exceeded. Please try again later.', 'code': 429}}, 'user_id': '{user_id}'}}"
                )
            elif (
                "context length" in error_str.lower()
                or "token limit" in error_str.lower()
            ):
                raise ValueError(
                    f"Error code: 400 - {{'error': {{'message': 'Input is too long for the selected model. Please reduce the content length.', 'code': 400}}, 'user_id': '{user_id}'}}"
                )
            else:
                # Generic error message that doesn't expose model details
                raise ValueError(
                    f"Error code: 400 - {{'error': {{'message': 'Provider returned error', 'code': 400}}, 'user_id': '{user_id}'}}"
                )

    @staticmethod
    async def get_models(db: Optional[Session] = None) -> List[Dict[str, Any]]:
        """Get available models from OpenRouter or database, returning display IDs instead of actual model IDs."""
        models_to_return = []
        # If database is provided, get models from database
        if db:
            db_models = get_free_models(db)
            for model_data in db_models:
                # Ensure model_data is a dictionary, as returned by get_free_models
                if isinstance(model_data, dict):
                    # Generate a UUID for display and replace internal model_id with it
                    display_id = str(uuid.uuid4())
                    # Store original model ID for mapping
                    internal_id = model_data.pop("id", None)
                    # Set display ID as the id for API response
                    model_data["id"] = display_id

                    # Save the mapping in the database
                    if internal_id:
                        create_model_id_mapping(db, display_id, internal_id)
                elif hasattr(model_data, "__dict__"):  # If it's an ORM object
                    model_dict = model_data.__dict__.copy()
                    display_id = str(uuid.uuid4())
                    # Store original model ID for mapping
                    internal_id = model_dict.pop("id", None)
                    # Set display ID as the id for API response
                    model_dict["id"] = display_id
                    model_data = model_dict

                    # Save the mapping in the database
                    if internal_id:
                        create_model_id_mapping(db, display_id, internal_id)
                models_to_return.append(model_data)

            # If we got models from the database, return them - don't try API
            if models_to_return:
                return models_to_return

        # Otherwise, fetch from OpenRouter API
        try:
            # Use OpenAI SDK to list models
            response = client.models.list()
            models_data = {"data": [model.model_dump() for model in response.data]}

            # Process and enhance model information, filtering for free models
            enhanced_models = []
            for model in models_data.get("data", []):
                # For development, we're considering models with very low pricing as "free"
                pricing = model.get("pricing", {})
                is_free = (
                    pricing.get("prompt", 0) < 0.5
                    and pricing.get("completion", 0) < 1.0
                )

                if is_free:
                    enhanced_model = enhance_model_info(model)
                    enhanced_model["is_free"] = True
                    # Store original model ID for mapping
                    internal_id = enhanced_model.pop("id", None)
                    # Set display ID as the id for API response
                    display_id = str(uuid.uuid4())
                    enhanced_model["id"] = display_id

                    # Save the mapping in the database if database is provided
                    if db and internal_id:
                        create_model_id_mapping(db, display_id, internal_id)

                    enhanced_models.append(enhanced_model)

            return enhanced_models
        except Exception as e:
            # If API call fails and we have no models from database, raise the error
            if not models_to_return:
                raise ValueError(f"Failed to fetch models: {str(e)}")

            # If we have models from database, return those instead of failing
            return models_to_return


class ArticleService:
    """Service for article generation and validation"""

    @staticmethod
    async def generate_article(
        title: str,
        details: str,
        tone: str,
        llm_model: str,
        word_count: int,
        promotion_content: Optional[str] = None,
        negative_content: Optional[str] = None,
        db: Optional[Session] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Generate an article using OpenRouter API"""
        # Get model ID from display ID if db is provided
        internal_model_id = None
        if db:
            # Try to get the model by display ID first
            model = get_model_by_display_id(db, llm_model)
            if model:
                internal_model_id = model.id
            else:
                # Fall back to direct model ID for backward compatibility
                model = get_model_by_id(db, llm_model)
                if model:
                    internal_model_id = model.id
                else:
                    # If model is not found, get the first available model from the database
                    models = get_free_models(db)
                    if models and len(models) > 0:
                        internal_model_id = models[0]["id"]
                    else:
                        raise ValueError(
                            f"Model with ID {llm_model} not found and no fallback models available"
                        )

        if not internal_model_id:
            raise ValueError(f"Model with ID {llm_model} not found")

        # Create prompts for article generation with strict word count control and markdown format
        prompts = create_article_prompt(
            title=title,
            details=details,
            tone=tone,
            word_count=word_count,
            promotion_content=promotion_content,
            negative_content=negative_content,
        )

        # Prepare messages for OpenAI SDK
        messages = [
            {"role": "system", "content": prompts["system_prompt"]},
            {"role": "user", "content": prompts["user_prompt"]},
        ]

        # Add additional guidance for Markdown formatting and word count
        system_message = messages[0]["content"]
        system_message += f"""
IMPORTANT: You MUST generate exactly {word_count} words. No more, no less. Count words carefully before completing the response.

FORMATTING: You MUST format your response in Markdown. Use appropriate headers, paragraphs, bullet points, and emphasis where needed. Ensure the content is well-structured and readable.

GUIDANCE FOR QUALITY CONTENT:
1. Start with a compelling introduction that hooks the reader
2. Include clear section headers to organize the content (use # for main headers, ## for subheaders)
3. Support main points with evidence, examples, or data
4. Maintain a consistent {tone} tone throughout
5. End with a strong conclusion and call-to-action if appropriate
6. Ensure the content provides actual value to the reader
7. Use appropriate transitions between paragraphs and sections
8. Use markdown formatting like **bold**, *italic*, and bullet points where appropriate

DO NOT stop your response prematurely - you MUST complete the full article with all necessary content and sections.
"""
        messages[0]["content"] = system_message

        # Calculate appropriate max_tokens based on model and word count
        max_tokens = OpenRouterService.calculate_max_tokens(
            internal_model_id, word_count
        )

        # Make the API request using the new approach
        response = await OpenRouterService.make_request(
            model=internal_model_id,
            messages=messages,
            temperature=0.7,  # Balanced creativity and coherence
            max_tokens=max_tokens,
            db=db,
            user_id=user_id,
        )

        # Extract the generated content
        generated_content = (
            response.get("choices", [{}])[0].get("message", {}).get("content", "")
        )

        # Check if the response seems incomplete (less than 75% of requested word count)
        actual_word_count = len(generated_content.split())
        if actual_word_count < (word_count * 0.75):
            # Try again with even more tokens
            max_tokens = max_tokens * 2

            # Make a second API request with increased tokens
            response = await OpenRouterService.make_request(
                model=internal_model_id,
                messages=messages,
                temperature=0.7,  # Balanced creativity and coherence
                max_tokens=max_tokens,
                db=db,
                user_id=user_id,
            )

            # Extract the generated content
            generated_content = (
                response.get("choices", [{}])[0].get("message", {}).get("content", "")
            )
            actual_word_count = len(generated_content.split())

        # Verify word count and adjust if needed
        if actual_word_count < (word_count * 0.9) or actual_word_count > (
            word_count * 1.1
        ):
            # Add word count warning to the content
            generated_content = (
                f"[Word Count Warning: Generated {actual_word_count} words instead of requested {word_count} words]\n\n"
                + generated_content
            )

        # Calculate token usage from response
        usage_data = response.get("usage", {})
        input_tokens = usage_data.get("prompt_tokens", 0)
        output_tokens = usage_data.get("completion_tokens", 0)

        # Process markdown for proper rendering (no escaping)
        # We'll let FastAPI handle the response formatting with our custom JSON encoder

        return {
            "article": generated_content,
            "word_count": actual_word_count,
            "token_usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
        }

    @staticmethod
    async def validate_content(
        article_content: str,
        evaluation_metrics: List[str],
        llm_model: str,
        db: Optional[Session] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Validate and provide feedback on article content"""
        # Get model ID from display ID if db is provided
        internal_model_id = None
        if db:
            # Try to get the model by display ID first
            model = get_model_by_display_id(db, llm_model)
            if model:
                internal_model_id = model.id
            else:
                # Fall back to direct model ID for backward compatibility
                model = get_model_by_id(db, llm_model)
                if model:
                    internal_model_id = model.id
                else:
                    # If model is not found, get the first available model from the database
                    models = get_free_models(db)
                    if models and len(models) > 0:
                        internal_model_id = models[0]["id"]
                    else:
                        raise ValueError(
                            f"Model with ID {llm_model} not found and no fallback models available"
                        )

        if not internal_model_id:
            raise ValueError(f"Model with ID {llm_model} not found")

        # Create prompt for content validation
        prompts = create_validation_prompt(article_content, evaluation_metrics)

        # Prepare messages for OpenAI SDK
        messages = [
            {"role": "system", "content": prompts["system_prompt"]},
            {"role": "user", "content": prompts["user_prompt"]},
        ]

        # Update system prompt to request improved markdown formatting and complete responses
        system_message = messages[0]["content"]
        system_message += """
IMPORTANT: Format your evaluation in clean, readable markdown. Use proper headers (# and ##), bullet points, and emphasis (**bold**, *italic*) where appropriate.

Your response MUST include:
1. An overall evaluation summary
2. Specific feedback for each requested evaluation metric
3. Suggested improvements clearly formatted with markdown

If you're making edits to the article, return the ENTIRE edited article at the end of your response, properly formatted in markdown and separated by a clear divider (---).

DO NOT truncate or abbreviate your response. Ensure your complete evaluation and the edited article (if applicable) are included in full.
"""
        messages[0]["content"] = system_message

        # Calculate appropriate max_tokens for validation response
        max_tokens = OpenRouterService.calculate_max_tokens(
            internal_model_id, len(article_content.split()) * 2
        )

        # Make the API request using the new approach
        response = await OpenRouterService.make_request(
            model=internal_model_id,
            messages=messages,
            temperature=0.3,  # Lower temperature for more focused feedback
            max_tokens=max_tokens,
            db=db,
            user_id=user_id,
        )

        # Extract the validation feedback
        validation_feedback = (
            response.get("choices", [{}])[0].get("message", {}).get("content", "")
        )

        # Check if response seems incomplete and retry with more tokens if needed
        if len(validation_feedback.split()) < (len(article_content.split()) * 0.2):
            # Response seems too short compared to original - retry with more tokens
            max_tokens = max_tokens * 2

            # Second attempt with increased tokens
            response = await OpenRouterService.make_request(
                model=internal_model_id,
                messages=messages,
                temperature=0.3,
                max_tokens=max_tokens,
                db=db,
                user_id=user_id,
            )

            # Extract the validation feedback
            validation_feedback = (
                response.get("choices", [{}])[0].get("message", {}).get("content", "")
            )

        # Calculate token usage from response
        usage_data = response.get("usage", {})
        input_tokens = usage_data.get("prompt_tokens", 0)
        output_tokens = usage_data.get("completion_tokens", 0)

        # Parse the feedback to extract the edited article if present
        edited_article = None
        feedback_only = validation_feedback

        # Check if the response contains a divider indicating an edited article
        if "---" in validation_feedback:
            parts = validation_feedback.split("---", 1)
            if len(parts) == 2:
                feedback_only = parts[0].strip()
                edited_article = parts[1].strip()

        # Ensure both parts are properly formatted
        if not feedback_only.startswith("#"):
            feedback_only = "# Content Evaluation\n\n" + feedback_only

        return {
            "evaluation": feedback_only,  # The evaluation part
            "edited_article": edited_article,  # The edited article if present
            "token_usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
            },
        }


class CostService:
    """Service for calculating model usage costs"""

    @staticmethod
    async def calculate_cost(
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        db: Optional[Session] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Calculate the cost of using a specific model based on token usage"""
        if not db:
            raise ValueError("Database session is required for cost calculation")

        # Get model by display ID first
        model = get_model_by_display_id(db, model_id)
        if not model:
            # Fall back to direct model ID for backward compatibility
            model = get_model_by_id(db, model_id)
            if not model:
                # If model is not found, get the first available model from the database
                models = get_free_models(db)
                if models and len(models) > 0:
                    # Get the first model from the database
                    first_model_id = models[0]["id"]
                    model = get_model_by_id(db, first_model_id)
                    if not model:
                        raise ValueError(
                            f"Model with ID {model_id} not found and no fallback models available"
                        )
                else:
                    raise ValueError(
                        f"Model with ID {model_id} not found and no fallback models available"
                    )

        # Calculate costs
        input_cost = (
            input_tokens * model.input_price / 1000000
        )  # Convert from price per million tokens
        output_cost = (
            output_tokens * model.output_price / 1000000
        )  # Convert from price per million tokens
        total_cost = input_cost + output_cost

        # Log usage if user ID is provided
        if user_id:
            log_api_usage(
                db=db,
                user_id=user_id,
                model_id=model.id,
                endpoint="calculate_cost",
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                status="success",
            )

        return {
            "id": model_id,  # Return the display ID that was passed in
            "name": model.name,  # Include the model name in the response
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "input_cost": input_cost,
            "output_cost": output_cost,
            "total_cost": total_cost,
            "currency": "USD",
        }
