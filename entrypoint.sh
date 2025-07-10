#!/bin/bash
set -e

# --- Configuration ---
WP_PATH="/var/www/html"
AGENT_PATH="${WP_PATH}/agent"
VENV_PATH="/opt/venv"
LOG_DIR="/var/log/wp-agent"

# Enable error handling
trap 'error_handler $? $LINENO $BASH_LINENO "$BASH_COMMAND" $(printf "::%s" ${FUNCNAME[@]:-})' ERR

# Error handling function
error_handler() {
    local exit_code=$1
    local line_no=$2
    local bash_lineno=$3
    local last_command=$4
    local func_trace=$5
    echo "Error in entrypoint.sh - Exit code: $exit_code Command: $last_command Line: $line_no"
}

# --- Environment Setup ---
setup_environment() {
    # Create necessary directories
    mkdir -p "${LOG_DIR}"
    
    # Activate virtual environment
    source "${VENV_PATH}/bin/activate"
    
    # Set environment-specific variables
    if [ "${FLASK_ENV}" = "development" ]; then
        export FLASK_DEBUG=1
        export LOG_LEVEL=DEBUG
    else
        export FLASK_DEBUG=0
        export LOG_LEVEL=INFO
    fi
}

# --- Database Setup ---
wait_for_database() {
    echo "Waiting for database at ${WORDPRESS_DB_HOST}..."
    until mariadb -h "${WORDPRESS_DB_HOST}" -u "${WORDPRESS_DB_USER}" -p"${WORDPRESS_DB_PASSWORD}" -e "SELECT 1" >/dev/null 2>&1; do
        echo "Database not ready, sleeping for 5 seconds..."
        sleep 5
    done
    echo "Database is ready."
}

# --- WordPress Setup ---
setup_wordpress() {
    if [ ! -f "${WP_PATH}/wp-config.php" ]; then
        echo "Installing WordPress..."
        wp core download --path="${WP_PATH}"
        wp config create \
            --path="${WP_PATH}" \
            --dbname="${WORDPRESS_DB_NAME}" \
            --dbuser="${WORDPRESS_DB_USER}" \
            --dbpass="${WORDPRESS_DB_PASSWORD}" \
            --dbhost="${WORDPRESS_DB_HOST}" \
            --dbprefix="wp_"
        
        wp core install \
            --path="${WP_PATH}" \
            --url="${WORDPRESS_SITE_URL}" \
            --title="${WORDPRESS_SITE_TITLE}" \
            --admin_user="${WORDPRESS_ADMIN_USER}" \
            --admin_password="${WORDPRESS_ADMIN_PASSWORD}" \
            --admin_email="${WORDPRESS_ADMIN_EMAIL}" \
            --skip-email
        
        echo "WordPress installation complete."
    fi
}

# --- Agent Setup ---
start_agent() {
    cd "${AGENT_PATH}"
    
    if [ "${FLASK_ENV}" = "development" ]; then
        echo "Starting agent in development mode..."
        python -m flask run --host=0.0.0.0 --port=5000 --reload &
    else
        echo "Starting agent in production mode..."
        gunicorn --bind 0.0.0.0:5000 \
                 --workers 4 \
                 --access-logfile "${LOG_DIR}/access.log" \
                 --error-logfile "${LOG_DIR}/error.log" \
                 --capture-output \
                 --log-level "${LOG_LEVEL}" \
                 agent:app &
    fi
    
    AGENT_PID=$!
    echo "Agent started with PID ${AGENT_PID}"
}

# --- Main Execution ---
main() {
    setup_environment
    wait_for_database
    setup_wordpress
    start_agent
    
    # Start FrankenPHP
    echo "Starting FrankenPHP server..."
    exec "$@"
}

main "$@"
