#!/bin/bash
# Development startup script for local testing with Docker services

echo "🚀 Starting DY Golf Cart Application in Development Mode"

# Set environment to development to load .env.development
export ENVIRONMENT=development

# Optional: Show which config file is being loaded
export DEBUG_CONFIG=true

echo "📦 Using dynamic environment configuration"
echo "  - Environment: development"
echo "  - Config file: .env.development (auto-detected)"
echo ""
echo "  Services expected:"
echo "  - Main DB: localhost:5435"
echo "  - Test DB: localhost:5436"
echo "  - Redis: localhost:6379"

# Start the application with hot reload
echo "🔥 Starting application with hot reload..."
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000