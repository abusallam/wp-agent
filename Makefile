.PHONY: help dev test lint format clean build deploy

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

dev: ## Start development environment
	docker compose up --build

test: ## Run tests
	docker compose exec wp-agent pytest

lint: ## Run linting
	docker compose exec wp-agent flake8 .
	docker compose exec wp-agent black --check .

format: ## Format code
	docker compose exec wp-agent black .

clean: ## Clean up containers and volumes
	docker compose down -v
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

build: ## Build production image
	docker compose -f docker-compose.coolify.yml build

deploy: ## Deploy to production
	docker compose -f docker-compose.coolify.yml up -d