# --- Base Stage ---
FROM dunglas/frankenphp:1.1.0-php8.3-bookworm AS base

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    unzip \
    mariadb-client \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Install WP-CLI
RUN wget https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar -O /usr/local/bin/wp \
    && chmod +x /usr/local/bin/wp

# Create Python virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Set working directory
WORKDIR /var/www/html

# Copy configuration files
COPY ./php-memory-limit.ini /usr/local/etc/php/conf.d/
COPY ./requirements.txt /tmp/

# Install Python dependencies
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# --- Development Stage ---
FROM base AS development

# Install development dependencies
RUN pip install --no-cache-dir pytest pytest-cov pytest-mock black flake8 pre-commit

# Copy application code
COPY . /var/www/html/

# Set development environment
ENV FLASK_ENV=development
ENV FLASK_DEBUG=1
ENV FLASK_APP=agent.py

CMD ["python", "-m", "flask", "run", "--host=0.0.0.0"]

# --- Production Stage ---
FROM base AS production

# Copy application code
COPY . /var/www/html/
RUN mkdir -p /var/www/html/agent

# Set production environment
ENV FLASK_ENV=production
ENV FLASK_DEBUG=0

# Install Gunicorn
RUN pip install --no-cache-dir gunicorn

# Set up non-root user
RUN useradd -r -s /bin/false appuser && \
    chown -R appuser:appuser /var/www/html /opt/venv

USER appuser

# Copy and set entrypoint
COPY ./entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

# Expose ports
EXPOSE 80 443 5000

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
