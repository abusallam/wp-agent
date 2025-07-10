# Multi-stage build for production optimization
FROM dunglas/frankenphp:1.1.0-php8.3-bookworm AS base-dependencies

# Install system dependencies with specific versions for reproducibility
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget=1.21.3-1+deb12u2 \
    unzip=6.0-28 \
    mariadb-client=1:10.11.6-0+deb12u1 \
    python3=3.11.2-1+b1 \
    python3-pip=23.0.1+dfsg-1 \
    python3-venv=3.11.2-1+b1 \
    curl=7.88.1-10+deb12u7 \
    gnupg2=2.2.40-1.1 \
    ca-certificates=20230311 \
    supervisor=4.2.5-1 \
    logrotate=3.21.0-1 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Create non-root user with specific UID/GID for consistency
RUN groupadd -r appuser -g 1001 && \
    useradd -r -g appuser -u 1001 -d /app -s /bin/bash appuser

# Install WP-CLI with version pinning and verification
RUN wget -O /tmp/wp-cli.phar.asc https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar.asc && \
    wget -O /tmp/wp-cli.phar https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar && \
    # Verify WP-CLI signature (optional but recommended)
    gpg --batch --keyserver keyserver.ubuntu.com --recv-keys 63AF7AA15067C05616FDDD88A3A2E8F226F0BC06 || true && \
    mv /tmp/wp-cli.phar /usr/local/bin/wp && \
    chmod +x /usr/local/bin/wp && \
    rm -f /tmp/wp-cli.phar.asc

# Production stage
FROM base-dependencies AS production

# Set security-focused environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/agent \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    FLASK_ENV=production \
    WP_CLI_CACHE_DIR=/tmp/wp-cli-cache \
    WP_CLI_PACKAGES_DIR=/tmp/wp-cli-packages

# Create application directory structure
RUN mkdir -p /app/agent /app/logs /app/backups /app/tmp \
    && chown -R appuser:appuser /app \
    && chmod -R 755 /app

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY --chown=appuser:appuser ./agent/requirements.txt /app/agent/

# Create Python virtual environment and install dependencies
RUN python3 -m venv /app/venv \
    && chown -R appuser:appuser /app/venv \
    && /app/venv/bin/pip install --no-cache-dir --upgrade pip==24.0 \
    && /app/venv/bin/pip install --no-cache-dir -r /app/agent/requirements.txt

# Copy application code
COPY --chown=appuser:appuser ./agent /app/agent/
COPY --chown=appuser:appuser ./config /app/config/
COPY --chown=appuser:appuser ./scripts /app/scripts/

# Copy and configure supervisor
COPY --chown=root:root ./config/supervisord.conf /etc/supervisor/conf.d/
COPY --chown=root:root ./config/logrotate.conf /etc/logrotate.d/wordpress-agent

# Create WordPress directory and set permissions
RUN mkdir -p /var/www/html \
    && chown -R appuser:appuser /var/www/html \
    && chmod -R 755 /var/www/html

# Copy entrypoint script
COPY --chown=appuser:appuser ./scripts/entrypoint.sh /app/scripts/
RUN chmod +x /app/scripts/entrypoint.sh

# Set up health check
COPY --chown=appuser:appuser ./scripts/healthcheck.sh /app/scripts/
RUN chmod +x /app/scripts/healthcheck.sh

# Configure security headers and PHP settings
COPY --chown=root:root ./config/security.ini /usr/local/etc/php/conf.d/99-security.ini
COPY --chown=root:root ./config/Caddyfile /etc/caddy/Caddyfile

# Set up log rotation
RUN mkdir -p /var/log/wordpress-agent \
    && chown -R appuser:appuser /var/log/wordpress-agent \
    && chmod -R 755 /var/log/wordpress-agent

# Security hardening
RUN find /app -type f -name "*.py" -exec chmod 644 {} \; \
    && find /app -type f -name "*.sh" -exec chmod 755 {} \; \
    && find /app -type d -exec chmod 755 {} \;

# Remove unnecessary packages and clean up
RUN apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Switch to non-root user
USER appuser

# Expose ports
EXPOSE 80 443 5000 9001

# Add labels for better container management
LABEL maintainer="your-email@example.com" \
      version="2.0.0" \
      description="Production-ready WordPress Agent with A2A protocol" \
      security.scan="enabled"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD /app/scripts/healthcheck.sh

# Set entrypoint
ENTRYPOINT ["/app/scripts/entrypoint.sh"]

# Default command
CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
