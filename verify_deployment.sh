#!/bin/bash

# Deployment Verification Script for Content Writer AI API
# Usage: ./verify_deployment.sh <your-vercel-url>

if [ $# -eq 0 ]; then
    echo "Usage: $0 <vercel-url>"
    echo "Example: $0 https://contentwriterapi.vercel.app"
    exit 1
fi

URL=$1
echo "🚀 Verifying deployment at: $URL"
echo "=========================================="

# Test 1: Basic connectivity
echo "🔌 Testing basic connectivity..."
response=$(curl -s -w "%{http_code}" "$URL/" -o /tmp/response.txt)
status_code="${response: -3}"

if [ "$status_code" = "200" ]; then
    echo "✅ Root endpoint: WORKING"
    cat /tmp/response.txt
    echo ""
else
    echo "❌ Root endpoint: FAILED (Status: $status_code)"
    cat /tmp/response.txt
    echo ""
fi

# Test 2: Models endpoint
echo "📚 Testing models endpoint..."
response=$(curl -s -w "%{http_code}" "$URL/models" -o /tmp/models.txt)
status_code="${response: -3}"

if [ "$status_code" = "200" ]; then
    echo "✅ Models endpoint: WORKING"
    # Show first model only for brevity
    python3 -c "
import json, sys
try:
    with open('/tmp/models.txt', 'r') as f:
        data = json.load(f)
        if 'models' in data and len(data['models']) > 0:
            print(f'Found {len(data[\"models\"])} models')
            print(f'First model: {data[\"models\"][0][\"name\"]}')
        else:
            print('No models found')
except:
    print('Failed to parse models response')
"
else
    echo "❌ Models endpoint: FAILED (Status: $status_code)"
    cat /tmp/models.txt
fi
echo ""

# Test 3: Rate limiting
echo "🚦 Testing rate limiting (10 requests)..."
success_count=0
rate_limited_count=0

for i in {1..12}; do
    response=$(curl -s -w "%{http_code}" "$URL/" -o /dev/null)
    status_code="${response: -3}"
    
    if [ "$status_code" = "200" ]; then
        success_count=$((success_count + 1))
        echo -n "✅"
    elif [ "$status_code" = "429" ]; then
        rate_limited_count=$((rate_limited_count + 1))
        echo -n "🚫"
    else
        echo -n "❌"
    fi
done

echo ""
echo "Results: $success_count successful, $rate_limited_count rate limited"

if [ $rate_limited_count -gt 0 ]; then
    echo "✅ Rate limiting: WORKING"
else
    echo "⚠️  Rate limiting: NOT WORKING or limit too high"
fi

echo ""

# Test 4: API Documentation
echo "📖 Testing API documentation..."
response=$(curl -s -w "%{http_code}" "$URL/docs" -o /dev/null)
status_code="${response: -3}"

if [ "$status_code" = "200" ]; then
    echo "✅ API docs (/docs): ACCESSIBLE"
else
    echo "❌ API docs (/docs): FAILED (Status: $status_code)"
fi

# Test 5: OpenAPI schema
response=$(curl -s -w "%{http_code}" "$URL/openapi.json" -o /dev/null)
status_code="${response: -3}"

if [ "$status_code" = "200" ]; then
    echo "✅ OpenAPI schema: ACCESSIBLE"
else
    echo "❌ OpenAPI schema: FAILED (Status: $status_code)"
fi

echo ""
echo "🎉 Deployment verification completed!"
echo ""
echo "Next steps:"
echo "1. Test article generation with your OpenRouter API key"
echo "2. Set up monitoring for rate limit breaches"
echo "3. Configure Redis for persistent rate limiting"
echo "4. Add custom domain if needed"

# Cleanup
rm -f /tmp/response.txt /tmp/models.txt 