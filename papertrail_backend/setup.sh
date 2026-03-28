#!/bin/bash

# PaperTrail Backend Quick Start Script

echo "======================================"
echo "PaperTrail Backend Setup"
echo "======================================"
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version

# Create virtual environment
echo ""
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env from example
if [ ! -f .env ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your SARVAM_API_KEY"
fi

# Create uploads folder
echo ""
echo "Creating uploads folder..."
mkdir -p uploads

echo ""
echo "======================================"
echo "✅ Setup Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Edit .env and add your SARVAM_API_KEY"
echo "2. Start MongoDB: docker run -d -p 27017:27017 mongo"
echo "3. Run server: uvicorn main:app --reload"
echo ""
echo "API will be available at: http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
echo ""
