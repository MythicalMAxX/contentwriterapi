import tiktoken
from typing import Dict, List, Any, Optional


# Token counting utilities
def count_tokens(text: str, model: str = "gpt-3.5-turbo") -> int:
    """
    Count the number of tokens in a text string for a specific model.

    Args:
        text: The text to count tokens for
        model: The model to use for token counting

    Returns:
        int: The number of tokens in the text
    """
    try:
        # Try to use the tiktoken library for accurate token counting
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(text))
    except Exception:
        # Fallback to approximate token count (1 token ≈ 4 characters)
        return len(text) // 4


# Model recommendation utilities
def get_model_recommendations(model_id: str) -> List[str]:
    """
    Return recommendations for what each model is good at.

    Args:
        model_id: The ID of the model

    Returns:
        List[str]: A list of recommendations for the model
    """
    recommendations = {
        "anthropic/claude-3-opus": [
            "Detailed research articles",
            "Complex analysis",
            "Academic writing",
        ],
        "anthropic/claude-3-sonnet": [
            "Balanced quality and efficiency",
            "Professional blog posts",
            "Technical writing",
        ],
        "anthropic/claude-3-haiku": [
            "Fast content generation",
            "Short-form content",
            "Efficient drafting",
        ],
        "google/gemini-pro": [
            "Creative writing",
            "Balanced reasoning",
            "Versatile content",
        ],
        "meta-llama/llama-3-70b-instruct": [
            "Long-form content",
            "Detailed explanations",
            "Comprehensive articles",
        ],
        "meta-llama/llama-3-8b-instruct": [
            "Efficient content generation",
            "Straightforward articles",
            "Quick drafts",
        ],
        "mistralai/mistral-7b-instruct": [
            "Efficient writing",
            "Straightforward content",
            "Quick drafts",
        ],
        "mistralai/mixtral-8x7b-instruct": [
            "Versatile content",
            "Balanced quality",
            "General-purpose writing",
        ],
        "openai/gpt-4o": [
            "High-quality content",
            "Complex reasoning",
            "Versatile writing styles",
        ],
        "openai/gpt-4-turbo": [
            "Premium content",
            "Advanced reasoning",
            "Nuanced writing",
        ],
        "openai/gpt-3.5-turbo": [
            "Efficient content generation",
            "Blog posts",
            "General writing",
        ],
    }

    # Return generic recommendations if model not in our list
    return recommendations.get(
        model_id, ["General content creation", "Article writing"]
    )


# Prompt construction utilities
def create_article_prompt(
    title: str,
    details: str,
    tone: str,
    word_count: int,
    promotion_content: Optional[str] = None,
    negative_content: Optional[str] = None,
) -> Dict[str, str]:
    """
    Create system and user prompts for article generation.

    Args:
        title: The title of the article
        details: Additional instructions for the article
        tone: The writing tone to use
        word_count: Target word count
        promotion_content: Optional content to promote
        negative_content: Optional content to avoid

    Returns:
        Dict[str, str]: Dictionary with system_prompt and user_prompt
    """
    system_prompt = (
        "You are an expert content writer specializing in creating high-quality articles and blog posts. "
        "Your primary responsibility is to generate content that EXACTLY matches the requested word count. "
        "Follow these strict guidelines:\n"
        "1. Count words carefully before submitting your response\n"
        "2. Ensure the article is exactly the requested length - no more, no less\n"
        "3. Maintain high quality while meeting the word count requirement\n"
        "4. Use proper formatting and structure with Markdown\n"
        "5. Follow the specified tone and style\n"
        "6. Create content with a clear structure: introduction, main sections with headers, and conclusion\n"
        "7. Use headers (## and ###) to organize content into logical sections\n"
        "8. Incorporate bullet points or numbered lists where appropriate\n"
        "9. Use emphasis (bold, italic) to highlight important points\n"
        "Always adhere to ethical guidelines and produce factual, well-researched content."
    )

    # Build user prompt with all the requirements
    user_prompt = f"""Write an article in Markdown format that meets these specific requirements:

Title: # {title}

Details: {details}

Tone: {tone}

EXACT Word Count Required: {word_count} words
(This is a strict requirement - the article must be exactly {word_count} words)"""

    # Add promotion content if provided
    if promotion_content:
        user_prompt += f"\n\nNaturally incorporate mentions of the following while maintaining the exact word count: {promotion_content}"

    # Add negative content filtering if provided
    if negative_content:
        user_prompt += f"\n\nImportant: Do not mention or reference the following in the article: {negative_content}"

    # Add quality and structure guidelines
    user_prompt += "\n\nStructure and Formatting Requirements:\n"
    user_prompt += "1. Start with a compelling introduction that hooks the reader\n"
    user_prompt += "2. Organize content into logical sections with clear Markdown headers (## for main sections, ### for subsections)\n"
    user_prompt += "3. Use bullet points or numbered lists to present information where appropriate\n"
    user_prompt += (
        "4. Include **bold** and *italic* formatting to emphasize key points\n"
    )
    user_prompt += "5. End with a strong conclusion or call-to-action\n"
    user_prompt += "6. Ensure smooth transitions between sections\n"
    user_prompt += (
        f"7. Double-check that the final article is EXACTLY {word_count} words"
    )

    return {"system_prompt": system_prompt, "user_prompt": user_prompt}


def create_validation_prompt(
    article_content: str, evaluation_metrics: List[str]
) -> Dict[str, str]:
    """
    Create system and user prompts for content validation.

    Args:
        article_content: The article content to validate
        evaluation_metrics: Metrics to use for evaluation

    Returns:
        Dict[str, str]: Dictionary with system_prompt and user_prompt
    """
    system_prompt = (
        "You are an expert content editor and evaluator. Your task is to analyze the provided article "
        "based on specific evaluation metrics and suggest improvements. "
        "Format your response in clean, properly structured markdown with clear headings, bullet points, "
        "and proper spacing between sections. Your response must be complete, thorough, and well-formatted."
    )

    # Construct the evaluation prompt
    metrics_text = "\n- ".join([""] + evaluation_metrics)
    user_prompt = f"""Please evaluate the following article based on these metrics:{metrics_text}

Article content:
```markdown
{article_content}
```

Provide a detailed evaluation for each metric and suggest specific improvements to enhance the article quality.

IMPORTANT INSTRUCTIONS:
1. Use proper markdown formatting with headings (# for main headings, ## for subheadings), bullet points, and emphasis (**bold**, *italic*)
2. Ensure your response is COMPLETE and NOT TRUNCATED
3. If you make specific edits to the article, include the COMPLETE edited article at the end
4. Place the edited article after a divider line (---) to separate it from your evaluation
5. Make sure the edited article preserves all markdown formatting and is properly structured
6. The edited article should be complete - do not truncate or abbreviate it
7. Start your evaluation with a clear heading (# Overall Evaluation)
8. Structure each metric evaluation under its own heading (## Metric Name)"""

    return {"system_prompt": system_prompt, "user_prompt": user_prompt}


# Model capability utilities
def enhance_model_info(model_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhance model information with additional details about capabilities.

    Args:
        model_data: Raw model data from OpenRouter API

    Returns:
        Dict[str, Any]: Enhanced model information
    """
    model_id = model_data.get("id", "")
    recommendations = get_model_recommendations(model_id)

    # Create a concise description based on model capabilities
    model_name = (
        model_data.get("name", "").split(":")[0]
        if ":" in model_data.get("name", "")
        else model_data.get("name", "")
    )
    context_length = model_data.get("context_length", 4096)
    word_estimate = min(context_length // 3, 3000)  # Rough estimate of word capacity

    # Determine if model has reasoning capabilities based on name or recommendations
    has_reasoning = any(
        term in model_id.lower()
        for term in ["gpt-4", "claude", "gemini", "llama-3", "mixtral", "qwen"]
    )
    reasoning_text = (
        "strong reasoning capabilities"
        if has_reasoning
        else "basic reasoning capabilities"
    )

    # Create concise description
    description = f"Best for {recommendations[0].lower() if recommendations else 'general content creation'}. "
    description += (
        f"Can write approximately {word_estimate} words with {reasoning_text}."
    )

    return {
        "id": model_id,
        "name": model_name,
        "description": description,
        "context_length": context_length,
        "pricing": model_data.get("pricing", {}),
        "capabilities": {
            "text": True,  # All models support text
            "image_input": "image" in model_data.get("modalities", []),
            "file_input": "file" in model_data.get("modalities", []),
        },
        "recommended_for": recommendations,
        "is_free": False,  # Default value, will be updated by the service if needed
    }
