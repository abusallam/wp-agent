#!/bin/bash
set -e

# --- Configuration ---
# WordPress installation path
WP_PATH="/var/www/html"
AGENT_PATH="${WP_PATH}/agent"

# --- Database Initialization ---
# Wait for the database to become available before proceeding.
echo "Waiting for database at ${WORDPRESS_DB_HOST}..."
while ! mariadb -h "${WORDPRESS_DB_HOST}" -u "${WORDPRESS_DB_USER}" -p"${WORDPRESS_DB_PASSWORD}" -e "SELECT 1" > /dev/null 2>&1; do
    echo "Database not ready, sleeping for 5 seconds..."
    sleep 5
done
echo "Database is ready."

# --- WordPress Installation ---
# If wp-config.php does not exist, install WordPress.
if [ ! -f "${WP_PATH}/wp-config.php" ]; then
    echo "WordPress not found. Starting installation..."

    # Download WordPress core files.
    echo "Downloading WordPress core..."
    wp core download --path="${WP_PATH}"

    # Create the WordPress configuration file.
    echo "Creating wp-config.php..."
    wp config create \
        --path="${WP_PATH}" \
        --dbname="${WORDPRESS_DB_NAME}" \
        --dbuser="${WORDPRESS_DB_USER}" \
        --dbpass="${WORDPRESS_DB_PASSWORD}" \
        --dbhost="${WORDPRESS_DB_HOST}" \
        --dbprefix="wp_"

    # Install WordPress.
    echo "Installing WordPress..."
    wp core install \
        --path="${WP_PATH}" \
        --url="${WORDPRESS_SITE_URL}" \
        --title="${WORDPRESS_SITE_TITLE}" \
        --admin_user="${WORDPRESS_ADMIN_USER}" \
        --admin_password="${WORDPRESS_ADMIN_PASSWORD}" \
        --admin_email="${WORDPRESS_ADMIN_EMAIL}" \
        --skip-email

    # Set file permissions to ensure the web server can manage the files.
    echo "Setting WordPress file permissions..."
    chown -R frankie:frankie "${WP_PATH}"

    echo "WordPress installation complete."
else
    echo "WordPress is already installed."
fi

# --- Agent Setup ---
# Install Python dependencies for the agent.
echo "Installing/updating Python agent dependencies..."
if [ -f "${AGENT_PATH}/requirements.txt" ]; then
    pip3 install --user -r "${AGENT_PATH}/requirements.txt"
else
    echo "requirements.txt not found. Skipping Python dependencies."
fi

# Start the Python agent in the background.
echo "Starting WordPress Agent..."
export PYTHONPATH="${HOME}/.local/lib/python3.11/site-packages:${PYTHONPATH}"
export PATH="${HOME}/.local/bin:${PATH}"
cd "${AGENT_PATH}"
python3 agent.py &
AGENT_PID=$!
echo "Agent started with PID ${AGENT_PID}."

# --- Server Execution ---
# Start the FrankenPHP server.
echo "Starting FrankenPHP/Caddy server..."
exec "$@"
