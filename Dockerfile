# Use an official FrankenPHP image as a parent image
# Check https://github.com/dunglas/frankenphp for available tags
FROM dunglas/frankenphp:1.1.0-php8.3-bookworm AS base

# Install system dependencies
# - wget, unzip for WP-CLI and WordPress installation
# - default-mysql-client or mariadb-client for wp-cli to connect to the DB (mariadb-client is more fitting for MariaDB)
# - python3, python3-pip for the agent
# - sudo for potential permission management (though we aim to run as non-root where possible)
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    unzip \
    mariadb-client \
    python3 \
    python3-pip \
    sudo \
    && rm -rf /var/lib/apt/lists/*

# Install WP-CLI
RUN wget https://raw.githubusercontent.com/wp-cli/builds/gh-pages/phar/wp-cli.phar -O /usr/local/bin/wp \
    && chmod +x /usr/local/bin/wp

# Set up a non-root user for WordPress and the agent
# FrankenPHP images often run as 'frankie' or a similar user.
# We'll ensure our files are owned by this user.
# The default FrankenPHP user is 'frankie' (UID 1000, GID 1000)
# WordPress files should be owned by this user for Caddy/FrankenPHP to manage them.
USER root

# Create agent directory and copy agent files
WORKDIR /var/www/html
COPY ./agent ./agent/
COPY ./entrypoint.sh /usr/local/bin/entrypoint.sh

# Ensure entrypoint.sh is executable and set correct ownership
# /var/www/html is the document root for FrankenPHP
RUN chmod +x /usr/local/bin/entrypoint.sh \
    && chown -R frankie:frankie /var/www/html \
    && chown frankie:frankie /usr/local/bin/entrypoint.sh

# Switch to the non-root user 'frankie'
USER frankie

# Expose ports (FrankenPHP handles this, but good for documentation)
# Port 80 for HTTP, 443 for HTTPS, 5000 for the agent
EXPOSE 80 443 5000

# Set the entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Default command for FrankenPHP (can be overridden by entrypoint.sh if needed)
# The entrypoint.sh will ultimately run 'frankenphp run --config /etc/caddy/Caddyfile' or similar
CMD ["frankenphp", "run", "--config", "/etc/caddy/Caddyfile"]
