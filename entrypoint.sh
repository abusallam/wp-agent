#!/bin/bash
set -e # Exit immediately if a command exits with a non-zero status.

# Environment Variables (expected to be set in docker-compose.yml)
# WORDPRESS_DB_HOST, WORDPRESS_DB_USER, WORDPRESS_DB_PASSWORD, WORDPRESS_DB_NAME
# WORDPRESS_ADMIN_USER, WORDPRESS_ADMIN_PASSWORD, WORDPRESS_ADMIN_EMAIL
# WORDPRESS_SITE_TITLE, WORDPRESS_SITE_URL

# FrankenPHP/Caddy related environment variables
# SERVER_NAME (e.g., ":80" or "example.com")
# PHP_OPCACHE_ENABLE, etc.

# Path to WordPress installation
WP_PATH="/var/www/html"
AGENT_PATH="${WP_PATH}/agent"

# Wait for the database to be ready
# This is a simple loop; more robust solutions like wait-for-it.sh could be used.
echo "Waiting for database at ${WORDPRESS_DB_HOST}..."
while ! mariadb -h "${WORDPRESS_DB_HOST}" -u "${WORDPRESS_DB_USER}" -p"${WORDPRESS_DB_PASSWORD}" -e "SELECT 1" > /dev/null 2>&1; do
    echo "Database not ready, sleeping for 5 seconds..."
    sleep 5
done
echo "Database is ready."

# Check if WordPress is installed by looking for wp-config.php
if [ ! -f "${WP_PATH}/wp-config.php" ]; then
    echo "WordPress not found. Installing..."

    # Download WordPress core files
    # wp core download will fail if directory is not empty, but it should be empty
    # or contain only our agent and entrypoint.sh at this stage if it's a fresh volume.
    # We need to ensure we are the 'frankie' user or have permissions.
    # The Dockerfile should set WORKDIR /var/www/html and USER frankie.
    echo "Downloading WordPress core..."
    wp core download --path="${WP_PATH}" --allow-root # Allow root for initial setup if needed, though frankie should own WP_PATH

    echo "Creating wp-config.php..."
    wp config create \
        --path="${WP_PATH}" \
        --dbname="${WORDPRESS_DB_NAME}" \
        --dbuser="${WORDPRESS_DB_USER}" \
        --dbpass="${WORDPRESS_DB_PASSWORD}" \
        --dbhost="${WORDPRESS_DB_HOST}" \
        --dbprefix="wp_" \
        --allow-root # Allow root for initial setup

    echo "Installing WordPress..."
    wp core install \
        --path="${WP_PATH}" \
        --url="${WORDPRESS_SITE_URL}" \
        --title="${WORDPRESS_SITE_TITLE}" \
        --admin_user="${WORDPRESS_ADMIN_USER}" \
        --admin_password="${WORDPRESS_ADMIN_PASSWORD}" \
        --admin_email="${WORDPRESS_ADMIN_EMAIL}" \
        --skip-email \
        --allow-root # Allow root for initial setup

    # Set ownership again to ensure 'frankie' owns all WordPress files
    # This is important if wp-cli commands were run as root.
    # The 'frankie' user is assumed from the dunglas/frankenphp base image.
    echo "Setting WordPress file permissions..."
    chown -R frankie:frankie "${WP_PATH}"

    echo "WordPress installation complete."
else
    echo "WordPress already installed."
fi

# Install/update Python dependencies for the agent
echo "Installing/updating Python agent dependencies..."
if [ -f "${AGENT_PATH}/requirements.txt" ]; then
    # Using sudo because frankie might not have permissions to install system-wide
    # A virtual environment would be better but adds complexity to the entrypoint.
    # Alternatively, ensure 'frankie' can pip install into a user scheme or globally if permissions allow.
    # For simplicity here, we might need to adjust Dockerfile for pip install permissions or use sudo.
    # The Dockerfile now installs python3-pip, so pip3 should be available.
    # Let's try installing as the current user (frankie) first.
    # This assumes pip user install paths are in PATH or PYTHONPATH for the agent.
    # If running as root (not recommended for the agent itself), this would be global.
    # The Dockerfile runs this script as 'frankie'.
    pip3 install --user -r "${AGENT_PATH}/requirements.txt"
    # If --user is problematic, consider a virtual env or ensuring global write perms for frankie (less secure).
else
    echo "requirements.txt not found in ${AGENT_PATH}. Skipping Python dependencies."
fi

# Start the Python Google Agent in the background
echo "Starting Google Agent (agent.py)..."
# Ensure the agent is executable if it's not already
chmod +x "${AGENT_PATH}/agent.py"
# Run as 'frankie'. Python needs to be in PATH.
# Log agent output to stdout/stderr of the container for Docker logs
# Ensure PYTHONPATH includes user install location if pip3 install --user was used
export PYTHONPATH="${HOME}/.local/bin:${PYTHONPATH}" # Common for --user installs
python3 "${AGENT_PATH}/agent.py" &
AGENT_PID=$!
echo "Agent started with PID ${AGENT_PID}."

# Start FrankenPHP (Caddy server)
# The CMD in Dockerfile is `frankenphp run --config /etc/caddy/Caddyfile`
# We execute that default command here.
# Or, if CADDY_SERVER_NAME is set, Caddy might pick it up automatically.
# The base FrankenPHP image's entrypoint usually handles starting Caddy/FrankenPHP.
# If this script is the ENTRYPOINT, it needs to end with exec "$@" or the specific server command.
echo "Starting FrankenPHP/Caddy server..."

# If there's a Caddyfile in /etc/caddy/Caddyfile, it will be used.
# We can customize it or rely on FrankenPHP's auto-generation based on env vars.
# The `dunglas/frankenphp` image handles this. We just need to make sure
# this script execs the CMD passed to the container, or the default CMD from the Dockerfile.
# The `frankenphp run` command should be the final one.
# The Dockerfile CMD is ["frankenphp", "run", "--config", "/etc/caddy/Caddyfile"]
# So, if this script is the ENTRYPOINT, we should run `exec "$@"` to execute the CMD.
exec "$@"

# Graceful shutdown (optional, Docker handles SIGTERM to PID 1)
# trap "echo 'Shutting down agent...'; kill $AGENT_PID; wait $AGENT_PID; exit 0" SIGTERM SIGINT
# This trap might not be necessary if the agent exits cleanly when Python interpreter is killed.
# Docker sends SIGTERM to PID 1 (this script). If FrankenPHP is PID 1 (due to exec), it handles it.
# If the agent is a child process, it should also receive the signal if FrankenPHP propagates it.
# Python's default signal handlers usually mean Flask will shut down.
