from http.server import BaseHTTPRequestHandler
import sys
import os
import json

# Add parent directory to sys.path so we can import from app module
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = {
                "message": "Content Writer API is running on Vercel!",
                "status": "success",
                "endpoints": {
                    "root": "/",
                    "models": "/models",
                    "generate": "/generate-article",
                    "validate": "/validate-content",
                    "cost": "/calculate-cost",
                    "usage": "/user-usage"
                }
            }
            self.wfile.write(json.dumps(response).encode())
        elif self.path == '/models':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            models = [
                "openai/gpt-4o-mini",
                "openai/gpt-4o",
                "anthropic/claude-3.5-sonnet",
                "google/gemini-pro-1.5"
            ]
            self.wfile.write(json.dumps({"models": models}).encode())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Endpoint not found"}).encode())
    
    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        response = {"message": "POST endpoint working", "path": self.path}
        self.wfile.write(json.dumps(response).encode()) 