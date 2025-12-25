#!/bin/bash

# Quick Start Script for Multi-AI Trading System
# This script will guide you through the setup process

set -e

echo "🤖 Multi-AI Trading System - Quick Start"
echo "========================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first:"
    echo "   https://docs.docker.com/get-docker/"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first:"
    echo "   https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
    echo ""
    echo "⚠️  IMPORTANT: You need to configure your .env file!"
    echo ""
    echo "   Please edit .env and set at minimum:"
    echo "   - OPENROUTER_API_KEY (required)"
    echo "   - SECRET_KEY (generate with: openssl rand -hex 32)"
    echo "   - ADMIN_PASSWORD (change default)"
    echo ""
    echo "   Optional (for live trading):"
    echo "   - IB_ACCOUNT_ID"
    echo "   - NEWS_API_KEY"
    echo ""
    read -p "Press Enter after you've configured .env..."
else
    echo "✅ .env file exists"
fi

echo ""
echo "🚀 Building and starting containers..."
echo ""

# Build and start containers
docker-compose up -d --build

echo ""
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Check backend health
echo "Checking backend health..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Backend is healthy"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ Backend health check failed"
        echo "Check logs with: docker-compose logs backend"
        exit 1
    fi
    sleep 2
done

echo ""
echo "🎉 System is ready!"
echo ""
echo "📊 Access points:"
echo "   - Frontend Dashboard: http://localhost:3000"
echo "   - Backend API: http://localhost:8000"
echo "   - API Documentation: http://localhost:8000/docs"
echo ""
echo "📝 Useful commands:"
echo "   - View logs: docker-compose logs -f"
echo "   - Stop system: docker-compose down"
echo "   - Restart: docker-compose restart"
echo ""
echo "⚠️  System is in PAPER TRADING mode by default (safe)"
echo "   Check README.md for configuration options"
echo ""
