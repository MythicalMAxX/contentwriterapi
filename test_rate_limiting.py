#!/usr/bin/env python3
"""
Test script to verify rate limiting functionality
"""

import asyncio
import aiohttp
import time
from typing import List, Dict
import json

BASE_URL = "http://localhost:8000"

async def test_endpoint(session: aiohttp.ClientSession, endpoint: str, method: str = "GET", data: dict = None) -> Dict:
    """Test a single endpoint and return response info"""
    url = f"{BASE_URL}{endpoint}"
    
    try:
        if method.upper() == "GET":
            async with session.get(url) as response:
                status = response.status
                headers = dict(response.headers)
                try:
                    body = await response.json()
                except:
                    body = await response.text()
                return {
                    "status": status,
                    "headers": headers,
                    "body": body,
                    "success": status < 400
                }
        else:
            async with session.post(url, json=data) as response:
                status = response.status
                headers = dict(response.headers)
                try:
                    body = await response.json()
                except:
                    body = await response.text()
                return {
                    "status": status,
                    "headers": headers,
                    "body": body,
                    "success": status < 400
                }
    except Exception as e:
        return {
            "status": 0,
            "headers": {},
            "body": str(e),
            "success": False
        }

async def test_rate_limiting():
    """Test rate limiting on different endpoints"""
    
    print("🚀 Starting Rate Limiting Tests\n")
    
    # Test data for POST endpoints
    article_data = {
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "title": "Test Article",
        "details": "A simple test article for rate limiting",
        "tone": "Professional",
        "id": "Qwen 4B",
        "word_count": 100
    }
    
    validation_data = {
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "article_content": "This is a test article content for validation.",
        "evaluation_metrics": ["Clarity", "Coherence"],
        "id": "Qwen 4B"
    }
    
    cost_data = {
        "user_id": "550e8400-e29b-41d4-a716-446655440000",
        "id": "test-model-id",
        "input_tokens": 100,
        "output_tokens": 200
    }
    
    # Test scenarios
    test_scenarios = [
        {
            "name": "Root Endpoint (10/minute limit)",
            "endpoint": "/",
            "method": "GET",
            "data": None,
            "requests": 12,  # Exceed limit
            "expected_limit": 10
        },
        {
            "name": "Models Endpoint (60/minute limit)",
            "endpoint": "/models",
            "method": "GET", 
            "data": None,
            "requests": 5,  # Within limit
            "expected_limit": 60
        },
        {
            "name": "Generate Article (20/minute limit)",
            "endpoint": "/generate-article",
            "method": "POST",
            "data": article_data,
            "requests": 3,  # Within limit (but may fail due to API)
            "expected_limit": 20
        }
    ]
    
    async with aiohttp.ClientSession() as session:
        for scenario in test_scenarios:
            print(f"📋 Testing: {scenario['name']}")
            print(f"   Endpoint: {scenario['endpoint']}")
            print(f"   Rate Limit: {scenario['expected_limit']}/minute")
            print(f"   Sending {scenario['requests']} requests...")
            
            results = []
            start_time = time.time()
            
            # Send requests rapidly
            tasks = []
            for i in range(scenario['requests']):
                task = test_endpoint(
                    session, 
                    scenario['endpoint'], 
                    scenario['method'], 
                    scenario['data']
                )
                tasks.append(task)
            
            # Execute all requests concurrently
            results = await asyncio.gather(*tasks)
            
            end_time = time.time()
            duration = end_time - start_time
            
            # Analyze results
            successful_requests = sum(1 for r in results if r['success'])
            rate_limited_requests = sum(1 for r in results if r['status'] == 429)
            other_errors = sum(1 for r in results if not r['success'] and r['status'] != 429)
            
            print(f"   ✅ Successful: {successful_requests}")
            print(f"   🚫 Rate Limited (429): {rate_limited_requests}")
            print(f"   ❌ Other Errors: {other_errors}")
            print(f"   ⏱️  Duration: {duration:.2f}s")
            
            # Check if rate limiting is working
            if scenario['requests'] > scenario['expected_limit']:
                if rate_limited_requests > 0:
                    print(f"   ✅ Rate limiting is WORKING! Got {rate_limited_requests} rate limit responses")
                else:
                    print(f"   ⚠️  Rate limiting might not be working - no 429 responses received")
            
            # Show sample response headers for rate limiting info
            for result in results:
                if 'X-RateLimit-Limit' in result['headers'] or 'X-RateLimit-Remaining' in result['headers']:
                    print(f"   📊 Rate Limit Headers: Limit={result['headers'].get('X-RateLimit-Limit', 'N/A')}, "
                          f"Remaining={result['headers'].get('X-RateLimit-Remaining', 'N/A')}")
                    break
            
            print()

async def test_concurrent_users():
    """Test rate limiting with multiple concurrent users"""
    print("👥 Testing Concurrent Users Rate Limiting\n")
    
    async def user_requests(session, user_ip):
        """Simulate requests from a single user"""
        headers = {'X-Forwarded-For': user_ip}  # Simulate different IPs
        results = []
        
        for i in range(5):  # 5 requests per user
            try:
                async with session.get(f"{BASE_URL}/", headers=headers) as response:
                    results.append({
                        "status": response.status,
                        "user_ip": user_ip,
                        "success": response.status < 400
                    })
            except Exception as e:
                results.append({
                    "status": 0,
                    "user_ip": user_ip,
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    async with aiohttp.ClientSession() as session:
        # Simulate 3 different users
        user_ips = ["192.168.1.1", "192.168.1.2", "192.168.1.3"]
        
        tasks = [user_requests(session, ip) for ip in user_ips]
        all_results = await asyncio.gather(*tasks)
        
        # Analyze results per user
        for i, user_results in enumerate(all_results):
            user_ip = user_ips[i]
            successful = sum(1 for r in user_results if r['success'])
            rate_limited = sum(1 for r in user_results if r['status'] == 429)
            
            print(f"User {user_ip}: {successful} successful, {rate_limited} rate limited")

async def main():
    """Main test function"""
    try:
        print("🧪 Content Writer AI - Rate Limiting Test Suite")
        print("=" * 50)
        
        # Test basic connectivity
        async with aiohttp.ClientSession() as session:
            result = await test_endpoint(session, "/")
            if not result['success']:
                print(f"❌ Server not reachable at {BASE_URL}")
                print(f"   Error: {result['body']}")
                print("   Make sure the server is running: uvicorn app.main:app --host 0.0.0.0 --port 8000")
                return
            
            print(f"✅ Server is reachable at {BASE_URL}")
            print()
        
        # Run rate limiting tests
        await test_rate_limiting()
        
        # Test concurrent users
        await test_concurrent_users()
        
        print("\n🎉 Rate Limiting Tests Completed!")
        print("\nNote: If you see errors related to OpenRouter API or database,")
        print("that's expected - we're mainly testing the rate limiting functionality.")
        
    except KeyboardInterrupt:
        print("\n🛑 Tests interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 