# WordPress Agent

A containerized WordPress environment with a Python-based agent for programmatic control over WordPress sites. This project provides a secure, scalable, and maintainable solution for managing WordPress installations programmatically.

## Table of Contents

- [Architecture](#architecture)
- [Features](#features)
- [Installation](#installation)
- [Development](#development)
- [API Reference](#api-reference)
- [Deployment](#deployment)
- [Security](#security)
- [Monitoring](#monitoring)
- [Contributing](#contributing)
- [License](#license)

## Architecture

The project consists of three main components:

1. **WordPress Container**: FrankenPHP-based WordPress installation
2. **Python Agent**: Flask application for WordPress management
3. **Monitoring Stack**: Prometheus + Grafana for metrics

```mermaid
graph TD
    subgraph "User Interaction"
        A[User/Client]
    end

    subgraph "WP-Agent System"
        B[Python Agent (Flask)]
        C[WordPress Container (FrankenPHP)]
        D[Database (MySQL)]
        E[Monitoring Stack]
    end

    subgraph "Monitoring Stack"
        F[Prometheus]
        G[Grafana]
        H[Alertmanager]
    end

    A -- "API Calls (RESTful)" --> B
    B -- "Manages" --> C
    C -- "Reads/Writes" --> D
    B -- "Exposes /metrics" --> F
    F -- "Sends Alerts" --> H
    F -- "Data Source" --> G
    G -- "Visualizes Metrics" --> A
```

### Directory Structure

```
wp-agent/
├── agent.py                 # Main application
├── config.py               # Configuration management
├── requirements.txt        # Dependencies
├── setup.py               # Package setup
├── Dockerfile             # Multi-stage Docker build
├── docker-compose.yml     # Development environment
├── docker-compose.coolify.yml  # Production deployment
├── tests/                 # Test suite
├── monitoring/            # Prometheus configuration
└── scripts/              # Development tools
```

## Features

### Core Features

- **Containerized Environment:** Self-contained WordPress + Python agent using Docker
- **Development Mode:** Hot-reloading, debug logging, and development tools
- **Production Ready:** Gunicorn server, metrics, and security features

### WordPress Management

- **Posts & Pages:** Create, update, delete, and query posts and pages
- **Plugins:** Install, activate, deactivate, and remove plugins
- **Themes:** Manage themes and customize appearance
- **Files:** Secure file operations within WordPress directory
- **Options:** Get and update WordPress options

### Technical Features

- **API Control:** RESTful API with A2A protocol support
- **Security:**
  - API key authentication
  - Rate limiting per IP
  - CORS protection
  - Path traversal prevention
- **Monitoring:**
  - Prometheus metrics
  - Structured logging
  - Health checks
  - Performance monitoring
- **Development Tools:**
  - Hot reloading
  - VS Code integration
  - Pre-commit hooks
  - Comprehensive testing

## Installation

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- Python 3.8+
- Make (optional)

### Development Setup

1. Clone the repository:

```bash
git clone https://github.com/your-username/wp-agent.git
cd wp-agent
```

2. Quick setup using script:

```bash
./scripts/dev-setup.sh
```

Or manually:

```bash
# Copy environment file
cp .env.development .env

# Start development environment
make dev

# Install pre-commit hooks (optional)
make setup-hooks
```

### Available Make Commands

```bash
make help          # Show available commands
make dev           # Start development environment
make test          # Run tests
make lint          # Run linting
make format        # Format code
make clean         # Clean up containers and volumes
make build         # Build production image
make deploy        # Deploy to production
```

### Development URLs

- WordPress Admin: http://localhost/wp-admin
- Agent API: http://localhost:5000
- Metrics: http://localhost:9090
- Grafana: http://localhost:3000

## Configuration

### Environment Variables

#### Development Variables (.env.development)

```env
# Environment
FLASK_ENV=development
FLASK_DEBUG=1
LOG_LEVEL=DEBUG
LOG_FORMAT=console

# WordPress
WORDPRESS_DB_HOST=db
WORDPRESS_DB_USER=wordpress
WORDPRESS_DB_PASSWORD=wordpress_dev
WORDPRESS_DB_NAME=wordpress_dev
WORDPRESS_SITE_URL=http://localhost
WORDPRESS_SITE_TITLE=WP Agent Development
WORDPRESS_ADMIN_USER=admin
WORDPRESS_ADMIN_PASSWORD=admin_password
WORDPRESS_ADMIN_EMAIL=admin@example.com

# Security
A2A_API_KEY=dev_secret_key
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
RATE_LIMIT=200/minute

# Resources
PHP_MEMORY_LIMIT=512M
```

#### Production Variables (.envsample.env)

```env
# Environment
FLASK_ENV=production
FLASK_DEBUG=0
LOG_LEVEL=INFO
LOG_FORMAT=json

# WordPress
WORDPRESS_DB_HOST=db
WORDPRESS_DB_USER=wordpress
WORDPRESS_DB_PASSWORD=<strong-password>
WORDPRESS_DB_NAME=wordpress
WORDPRESS_SITE_URL=https://your-domain.com
WORDPRESS_SITE_TITLE=WordPress Site
WORDPRESS_ADMIN_USER=admin
WORDPRESS_ADMIN_PASSWORD=<strong-admin-password>
WORDPRESS_ADMIN_EMAIL=admin@your-domain.com

# Security
A2A_API_KEY=<strong-api-key>
CORS_ORIGINS=https://your-domain.com
RATE_LIMIT=100/minute

# Resources
PHP_MEMORY_LIMIT=512M
GUNICORN_WORKERS=4
MAX_REQUESTS=1000
MAX_REQUESTS_JITTER=50
```

## Development

### Prerequisites

- Docker and Docker Compose
- Python 3.8+
- Make (optional, for using Makefile commands)

### Local Development

1. Start development environment:

   ```bash
   docker compose up
   ```

2. Run tests:

   ```bash
   docker compose exec wp-agent pytest
   ```

3. Code formatting:
   ```bash
   docker compose exec wp-agent black .
   docker compose exec wp-agent flake8
   ```

### API Documentation

The agent provides RESTful endpoints for WordPress management:

#### Authentication

All requests require an API key in the `X-API-KEY` header:

```bash
curl -H "X-API-KEY: your-key" http://localhost:5000/health
```

#### Endpoints

1. System Information:

   ```bash
   GET /health
   POST /a2a/task {"tool": "get_system_information"}
   ```

2. Posts:

   ```bash
   POST /a2a/task
   {
     "tool": "create_wordpress_post",
     "args": {
       "title": "Post Title",
       "content": "Post content"
     }
   }
   ```

3. Plugins:
   ```bash
   POST /a2a/task
   {
     "tool": "install_wordpress_plugin",
     "args": {
       "plugin_slug": "plugin-name"
     }
   }
   ```

Full API documentation available in `/docs/api.md`

## Monitoring

### Metrics

- Prometheus metrics at `/metrics`
- Custom metrics for API requests and WordPress operations
- A pre-built Grafana dashboard is available in `monitoring/grafana-dashboard.json`. To use it, import it into your Grafana instance.

### Logging

- Development: Console logging with colors
- Production: JSON structured logging
- Log rotation configured via Docker

## Security

- API Key Authentication
- Rate Limiting per IP
- CORS Protection
- Path Traversal Prevention
- Regular Security Updates

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run tests and linting
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

- GitHub Issues: [Project Issues](https://github.com/your-username/wp-agent/issues)
- Documentation: `/docs`
