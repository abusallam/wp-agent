#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}WordPress Agent Development Setup${NC}"

# Check prerequisites
command -v docker >/dev/null 2>&1 || { echo "Docker is required but not installed. Aborting." >&2; exit 1; }
command -v docker compose >/dev/null 2>&1 || { echo "Docker Compose is required but not installed. Aborting." >&2; exit 1; }

# Setup development environment
echo -e "${YELLOW}Setting up development environment...${NC}"

# Copy environment file if it doesn't exist
if [ ! -f .env ]; then
    cp .env.development .env
    echo "Created .env from .env.development"
fi

# Install pre-commit hooks
if command -v pre-commit >/dev/null 2>&1; then
    pre-commit install
    echo "Installed pre-commit hooks"
fi

# Create necessary directories
mkdir -p logs

# Build and start development environment
echo -e "${YELLOW}Building and starting containers...${NC}"
docker compose up --build -d

echo -e "${GREEN}Development environment is ready!${NC}"
echo "WordPress: http://localhost"
echo "Agent API: http://localhost:5000"
echo "Metrics: http://localhost:9090"

echo -e "${YELLOW}Running initial tests...${NC}"
docker compose exec -T wp-agent pytest

echo -e "${GREEN}Setup complete!${NC}"