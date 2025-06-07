# Content Writer AI Microservice

A Python-based microservice that offers article and blog writing capabilities using OpenRouter AI models.

## Features

- Article generation with customizable parameters:
  - Title
  - Details/instructions
  - Tone
  - Promotion content
  - Word count
  - Negative content filtering
  - LLM model selection
- Content validation with custom evaluation metrics
- Model cost calculation
- Available model listing with capabilities

## Setup

### Prerequisites

- Python 3.8+
- OpenRouter API key

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd ContentWriterAI

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env file with your OpenRouter API key
```

### Running the service

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The API will be available at http://localhost:8000

## API Documentation

Once the service is running, you can access the API documentation at http://localhost:8000/docs

## API Examples

Below are some example `curl` commands to interact with the API. Replace placeholders like `your_user_id_here` with actual values.

### 1. Get Available Models

This endpoint lists available AI models. The `id` returned is a `display_id` and not the actual model identifier.

```bash
curl -X GET "http://localhost:8000/models" -H "accept: application/json"
```

**Example Response:**

```json
{
  "models": [
    {
      "id": "generated_uuid_for_display_1",
      "name": "Qwen 4B",
      "description": "Compact 4B model with strong reasoning capabilities. Best for drafting articles up to 2000 words with logical structure and coherent arguments.",
      "context_length": 8192,
      "pricing": {
        "prompt": 0.22,
        "completion": 0.88
      },
      "capabilities": {
        "text": true,
        "image_input": false,
        "file_input": false
      },
      "recommended_for": [
        "Logical reasoning",
        "Structured content",
        "Efficient drafting"
      ],
      "is_free": true
    }
    // ... other models
  ]
}
```

### 2. Generate an Article

This endpoint generates an article. Use the model `name` (e.g., "Qwen 4B") for the `llm_model` field.

```bash
curl -X POST "http://localhost:8000/generate-article" \
-H "accept: application/json" \
-H "Content-Type: application/json" \
-d '{
  "user_id": "a_valid_uuid_v4_user_id",
  "title": "The Future of Renewable Energy",
  "details": "Discuss solar, wind, and geothermal energy. Focus on advancements in the last 5 years.",
  "tone": "Informative and optimistic",
  "promotion_content": "Mention 'GreenTech Solutions' as a leading innovator.",
  "llm_model": "Qwen 4B",
  "word_count": 500,
  "negative_content": "Avoid discussing political controversies."
}'
```

**Example Response:**

```json
{
  "article": "[Word Count Warning: Generated 490 words instead of requested 500 words]\n\nThe future of renewable energy is brighter than ever, with significant advancements... (rest of the article content) ...GreenTech Solutions is at the forefront...",
  "word_count": 490,
  "token_usage": {
    "input_tokens": 150,
    "output_tokens": 735,
    "total_tokens": 885
  }
}
```

**Note on `user_id`**: If you provide a `user_id` (it should be a valid UUID v4 string), usage will be tracked for that user. If `user_id` is `null` or omitted, a new anonymous user will be created internally.

### 3. Validate Content

```bash
curl -X POST "http://localhost:8000/validate-content" \
-H "accept: application/json" \
-H "Content-Type: application/json" \
-d '{
  "user_id": "a_valid_uuid_v4_user_id",
  "article_content": "Your previously generated article content here...",
  "evaluation_metrics": ["Clarity", "Coherence", "Factuality"],
  "llm_model": "Qwen 4B"
}'
```

### 4. Calculate Cost

This endpoint requires the actual model ID (not the `display_id`). This is typically for internal use or if you have access to the underlying model IDs.

```bash
curl -X POST "http://localhost:8000/calculate-cost" \
-H "accept: application/json" \
-H "Content-Type: application/json" \
-d '{
  "user_id": "a_valid_uuid_v4_user_id",
  "model_id": "openrouter/actual-model-id",
  "input_tokens": 150,
  "output_tokens": 750
}'
```

### 5. Get User Usage

```bash
curl -X GET "http://localhost:8000/user/a_valid_uuid_v4_user_id/usage" \
-H "accept: application/json"
```

## License

MIT
