# Error Handling Improvements

## Problem

When the API encountered errors from the OpenRouter service, it would return detailed error messages that contained sensitive information:

1. Model IDs and provider names were exposed in error messages
2. Raw error responses from OpenRouter were passed directly to clients
3. Database errors revealed connection details and implementation specifics
4. Error messages were inconsistent across different endpoints

## Solution

We implemented a comprehensive error handling system with the following components:

### 1. SanitizedHTTPException Class

A custom exception class that sanitizes error messages before they're sent to clients:

```python
class SanitizedHTTPException(HTTPException):
    def __init__(self, status_code: int = 500, detail: Any = None, headers: Optional[Dict[str, str]] = None):
        # Sanitize the error message if it's from OpenRouter
        if detail and isinstance(detail, str):
            if "Error code: " in detail:
                detail = self._sanitize_error(detail)

        super().__init__(status_code=status_code, detail=detail, headers=headers)

    def _sanitize_error(self, error_message: str) -> str:
        # Generic sanitized messages based on error types
        if "Developer instruction is not enabled" in error_message:
            return "The selected model does not support advanced instructions. Please try another model."

        # More specific error handling...

        # Pattern to match and remove model IDs
        model_id_pattern = r'models?/[a-zA-Z0-9_\-]+(?:[:/][a-zA-Z0-9_\-]+)*'
        sanitized = re.sub(model_id_pattern, "the selected model", error_message)

        # Additional sanitization logic...

        return sanitized
```

### 2. Improved Service Error Handling

We updated the OpenRouterService to catch errors and convert them to user-friendly messages:

```python
# Format the error message for better client handling
if "model_not_found" in error_str.lower() or "no endpoints found" in error_str.lower():
    raise ValueError("Error code: 404 - The selected model is currently unavailable")
elif "not enabled" in error_str.lower() or "permission" in error_str.lower():
    raise ValueError("Error code: 400 - The selected model does not support this feature")
# Additional error handling cases...
```

### 3. Global Exception Handler

We added a global exception handler to catch any unhandled exceptions, especially database errors:

```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_msg = str(exc)

    # Check for database connection errors
    if "OperationalError" in error_msg and any(db_error in error_msg for db_error in
                                             ["connection", "SSL", "timeout", "reset"]):
        return JSONResponse(
            status_code=503,
            content={"detail": "Database service temporarily unavailable. Please try again later."},
        )

    # For all other errors, use the SanitizedHTTPException
    sanitized_exc = SanitizedHTTPException(status_code=500, detail=error_msg)
    return JSONResponse(
        status_code=sanitized_exc.status_code,
        content={"detail": sanitized_exc.detail},
    )
```

## Benefits

1. **Security**: Sensitive information like model IDs and provider names are no longer exposed
2. **User Experience**: Error messages are now user-friendly and actionable
3. **Consistency**: All errors follow the same format and pattern
4. **Maintainability**: Error handling is centralized and easy to update

## Testing

We created a test script (`test_error_handling.py`) that verifies:

1. Error messages don't contain sensitive model IDs
2. Appropriate status codes are returned
3. Error messages are properly formatted as JSON
4. User-friendly suggestions are included when appropriate

This ensures that our error handling works correctly and maintains security across all API endpoints.
