import flask
from flask_swagger_ui import get_swaggerui_blueprint
import subprocess
import json
import os
import logging
import structlog
from functools import wraps
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from prometheus_flask_exporter import PrometheusMetrics

from config import active_config

# Initialize Flask app
app = flask.Flask(__name__)
app.config.from_object(active_config)

# Swagger UI setup
SWAGGER_URL = '/api/docs'  # URL for exposing Swagger UI (without trailing '/')
API_URL = '/static/openapi.json'  # Our API url (can of course be a local file)

# Call factory function to create our blueprint
swaggerui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "WordPress Agent API"
    }
)

app.register_blueprint(swaggerui_blueprint)

# Initialize CORS
CORS(app, origins=active_config.CORS_ORIGINS)

# Initialize rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=[active_config.RATE_LIMIT]
)

# Initialize metrics
metrics = PrometheusMetrics(app)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if active_config.LOG_FORMAT == 'json'
        else structlog.dev.ConsoleRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Load configuration
A2A_API_KEY = active_config.A2A_API_KEY
if not A2A_API_KEY:
    logger.error("A2A_API_KEY not set. Agent will not be secured.")

WP_PATH = active_config.WP_PATH
SAFE_BASE_PATH = active_config.SAFE_BASE_PATH

def require_api_key(view_function):
    @wraps(view_function)
    def decorated_function(*args, **kwargs):
        if not A2A_API_KEY:
            logger.warning("API key not set on server, skipping authentication.")
            return view_function(*args, **kwargs) # Allow access if key not configured (dev mode)

        api_key = flask.request.headers.get('X-API-KEY')
        if not api_key or api_key != A2A_API_KEY:
            logger.warning(f"Unauthorized access attempt from {flask.request.remote_addr}. Invalid API key provided.")
            return flask.jsonify({"status": "error", "message": "Unauthorized: Invalid or missing API Key"}), 401
        return view_function(*args, **kwargs)
    return decorated_function

def run_wp_cli_command(args, decode_json=False):
    """Helper function to run WP-CLI commands."""
    base_command = ['wp', f'--path={WP_PATH}', '--allow-root'] # Allow root for now, revisit permissions
    command = base_command + args
    logger.info(f"Executing WP-CLI command: {' '.join(command)}")
    try:
        process = subprocess.run(command, capture_output=True, text=True, check=True)
        output = process.stdout.strip()
        if decode_json:
            return json.loads(output) if output else {}
        return output
    except subprocess.CalledProcessError as e:
        error_message = f"WP-CLI command failed: {e.cmd}\nReturn Code: {e.returncode}\nStderr: {e.stderr.strip()}\nStdout: {e.stdout.strip()}"
        logger.error(error_message)
        raise Exception(f"WP-CLI Error: {e.stderr.strip() or e.stdout.strip()}")
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON from WP-CLI output: {e}. Raw output: {output}")
        raise Exception(f"WP-CLI JSON Decode Error: {output}")
    except Exception as e:
        logger.error(f"Unexpected error running WP-CLI command: {e}")
        raise Exception(f"Unexpected WP-CLI Error: {str(e)}")


def get_tool_arg(data, arg_name, default=None, required=True, arg_type=None):
    """Helper to get and validate arguments for tools."""
    args = data.get('args', {})
    if arg_name not in args and required:
        raise ValueError(f"Missing required argument: {arg_name}")
    value = args.get(arg_name, default)
    if value is None and required and default is None: # Handles cases where default is None but arg is still missing
         raise ValueError(f"Missing required argument: {arg_name}")
    if value is not None and arg_type is not None and not isinstance(value, arg_type):
        raise ValueError(f"Argument '{arg_name}' must be of type {arg_type.__name__}, got {type(value).__name__}")
    return value

# --- Agent Tools ---

# --- System Tools ---
def get_system_information(data):
    """Retrieves version information for OS, Python, PHP, WordPress, and WP-CLI."""
    logger.info("Executing get_system_information tool")
    info = {}
    try:
        # OS Version (example, might need refinement for specific details)
        os_version = subprocess.run(['uname', '-a'], capture_output=True, text=True, check=True).stdout.strip()
        info['os_version'] = os_version

        # Python Version
        python_version = subprocess.run(['python3', '--version'], capture_output=True, text=True, check=True).stdout.strip()
        info['python_version'] = python_version

        # PHP Version (via WP-CLI or php command if available directly)
        # php_version = subprocess.run(['php', '--version'], capture_output=True, text=True, check=True).stdout.splitlines()[0]
        # Using wp-cli to get PHP version as it's contextually relevant
        php_version_raw = run_wp_cli_command(['cli', 'info', '--format=json'], decode_json=True)
        info['php_version'] = php_version_raw.get('php_version', 'N/A')


        # WordPress Version
        wp_version_raw = run_wp_cli_command(['core', 'version'])
        info['wordpress_version'] = wp_version_raw # This is usually just the string of the version

        # WP-CLI Version
        wp_cli_version_raw = run_wp_cli_command(['cli', 'version'])
        info['wp_cli_version'] = wp_cli_version_raw # This is usually just the string of the version

        return {"status": "success", "data": info}
    except Exception as e:
        logger.error(f"Error in get_system_information: {e}")
        return {"status": "error", "message": str(e)}

# --- Post Tools ---
def create_wordpress_post(data):
    """Creates a new post or page in WordPress."""
    logger.info("Executing create_wordpress_post tool")
    try:
        title = get_tool_arg(data, 'title', required=True, arg_type=str)
        content = get_tool_arg(data, 'content', required=True, arg_type=str)
        status = get_tool_arg(data, 'status', default='publish', arg_type=str)
        post_type = get_tool_arg(data, 'post_type', default='post', arg_type=str)

        cmd_args = [
            'post', 'create',
            f'--post_title={title}',
            f'--post_content={content}',
            f'--post_status={status}',
            f'--post_type={post_type}',
            '--porcelain' # Outputs only the new post ID
        ]
        post_id = run_wp_cli_command(cmd_args)
        return {"status": "success", "message": f"{post_type.capitalize()} created successfully with ID: {post_id}", "post_id": post_id}
    except Exception as e:
        logger.error(f"Error in create_wordpress_post: {e}")
        return {"status": "error", "message": str(e)}

# --- Plugin Tools ---
def activate_wordpress_plugin(data):
    """Activates an installed WordPress plugin."""
    logger.info("Executing activate_wordpress_plugin tool")
    try:
        plugin_slug = get_tool_arg(data, 'plugin_slug', required=True, arg_type=str)
        result = run_wp_cli_command(['plugin', 'activate', plugin_slug])
        return {"status": "success", "message": result}
    except Exception as e:
        logger.error(f"Error in activate_wordpress_plugin: {e}")
        # WP-CLI often returns non-zero exit code for "already active" with a message.
        # We might want to check e.message or e.stderr for specific WP-CLI errors.
        return {"status": "error", "message": str(e)}

# --- File Tools ---
def _validate_file_path(file_path_str):
    """Validates the file path to ensure it's within SAFE_BASE_PATH."""
    # Construct the absolute path
    abs_file_path = os.path.join(SAFE_BASE_PATH, os.path.normpath(file_path_str.lstrip('/\\')))

    # Ensure the path is normalized and under SAFE_BASE_PATH
    # os.path.commonprefix is not foolproof for path traversal alone.
    # We need to ensure the real, resolved path starts with SAFE_BASE_PATH.
    real_abs_file_path = os.path.realpath(abs_file_path)

    if not real_abs_file_path.startswith(SAFE_BASE_PATH):
        raise PermissionError(f"File access denied: Path '{file_path_str}' is outside the allowed directory '{WP_PATH}'.")
    return real_abs_file_path


def read_file(data):
    """Reads the content of a file within the WordPress installation."""
    logger.info("Executing read_file tool")
    try:
        file_path_str = get_tool_arg(data, 'file_path', required=True, arg_type=str)
        target_file_path = _validate_file_path(file_path_str)

        if not os.path.exists(target_file_path):
            return {"status": "error", "message": f"File not found: {file_path_str}"}
        if not os.path.isfile(target_file_path):
            return {"status": "error", "message": f"Path is not a file: {file_path_str}"}

        with open(target_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {"status": "success", "file_path": file_path_str, "content": content}
    except PermissionError as e:
        logger.error(f"Permission error in read_file: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Error in read_file: {e}")
        return {"status": "error", "message": str(e)}


def edit_file(data):
    """Edits/Overwrites a file within the WordPress installation."""
    logger.info("Executing edit_file tool")
    try:
        file_path_str = get_tool_arg(data, 'file_path', required=True, arg_type=str)
        content = get_tool_arg(data, 'content', required=True, arg_type=str) # Content must be string

        target_file_path = _validate_file_path(file_path_str)

        # For safety, ensure the parent directory exists if we are creating a new file (optional)
        # os.makedirs(os.path.dirname(target_file_path), exist_ok=True)

        with open(target_file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"status": "success", "message": f"File '{file_path_str}' written successfully."}
    except PermissionError as e:
        logger.error(f"Permission error in edit_file: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Error in edit_file: {e}")
        return {"status": "error", "message": str(e)}

# --- Option Tools ---
def get_wordpress_option(data):
    """Retrieves a WordPress option value."""
    logger.info("Executing get_wordpress_option tool")
    try:
        option_name = get_tool_arg(data, 'option_name', required=True, arg_type=str)
        # Using --format=json for potentially complex option types, though many are strings.
        value = run_wp_cli_command(['option', 'get', option_name, '--format=json'], decode_json=True)
        return {"status": "success", "option_name": option_name, "value": value}
    except Exception as e:
        logger.error(f"Error in get_wordpress_option: {e}")
        return {"status": "error", "message": str(e)}


def update_wordpress_option(data):
    """Updates a WordPress option."""
    logger.info("Executing update_wordpress_option tool")
    try:
        option_name = get_tool_arg(data, 'option_name', required=True, arg_type=str)
        option_value = get_tool_arg(data, 'option_value', required=True) # Value can be string, number, bool

        cmd_args = ['option', 'update', option_name]
        # WP-CLI 'option update' expects the value as a string.
        # For structured data (arrays, objects), it can take JSON if --format=json is used for the value.
        # Here, we assume option_value is a simple string or will be stringified.
        # If complex JSON objects need to be passed, this needs adjustment.
        if isinstance(option_value, (dict, list)):
             cmd_args.extend([json.dumps(option_value), '--format=json'])
        else:
            cmd_args.append(str(option_value))

        result = run_wp_cli_command(cmd_args)
        return {"status": "success", "message": result}
    except Exception as e:
        logger.error(f"Error in update_wordpress_option: {e}")
        return {"status": "error", "message": str(e)}

# --- Theme Tools ---
def install_wordpress_theme(data):
    """Installs a WordPress theme."""
    logger.info("Executing install_wordpress_theme tool")
    try:
        theme_slug = get_tool_arg(data, 'theme_slug', required=True, arg_type=str)
        version = get_tool_arg(data, 'version', required=False, arg_type=str)
        cmd_args = ['theme', 'install', theme_slug]
        if version:
            cmd_args.extend(['--version', version])
        result = run_wp_cli_command(cmd_args)
        return {"status": "success", "message": result}
    except Exception as e:
        logger.error(f"Error in install_wordpress_theme: {e}")
        return {"status": "error", "message": str(e)}

def activate_wordpress_theme(data):
    """Activates a WordPress theme."""
    logger.info("Executing activate_wordpress_theme tool")
    try:
        theme_slug = get_tool_arg(data, 'theme_slug', required=True, arg_type=str)
        result = run_wp_cli_command(['theme', 'activate', theme_slug])
        return {"status": "success", "message": result}
    except Exception as e:
        logger.error(f"Error in activate_wordpress_theme: {e}")
        return {"status": "error", "message": str(e)}

def list_wordpress_themes(data):
    """Lists installed WordPress themes."""
    logger.info("Executing list_wordpress_themes tool")
    try:
        themes = run_wp_cli_command(['theme', 'list', '--format=json'], decode_json=True)
        return {"status": "success", "data": themes}
    except Exception as e:
        logger.error(f"Error in list_wordpress_themes: {e}")
        return {"status": "error", "message": str(e)}

def get_active_wordpress_theme(data):
    """Gets the active WordPress theme."""
    logger.info("Executing get_active_wordpress_theme tool")
    try:
        # 'wp theme status' is not a valid command. 'wp theme list' with filtering is better.
        themes = run_wp_cli_command(['theme', 'list', '--status=active', '--format=json'], decode_json=True)
        return {"status": "success", "data": themes[0] if themes else None}
    except Exception as e:
        logger.error(f"Error in get_active_wordpress_theme: {e}")
        return {"status": "error", "message": str(e)}


def delete_wordpress_theme(data):
    """Deletes a WordPress theme."""
    logger.info("Executing delete_wordpress_theme tool")
    try:
        theme_slug = get_tool_arg(data, 'theme_slug', required=True, arg_type=str)
        result = run_wp_cli_command(['theme', 'delete', theme_slug])
        return {"status": "success", "message": result}
    except Exception as e:
        logger.error(f"Error in delete_wordpress_theme: {e}")
        return {"status": "error", "message": str(e)}


def append_to_file(data):
    """Appends content to a file within the WordPress installation."""
    logger.info("Executing append_to_file tool")
    try:
        file_path_str = get_tool_arg(data, 'file_path', required=True, arg_type=str)
        content = get_tool_arg(data, 'content', required=True, arg_type=str)  # Content must be string

        target_file_path = _validate_file_path(file_path_str)

        with open(target_file_path, 'a', encoding='utf-8') as f:
            f.write(content)
        return {"status": "success", "message": f"Content appended to file '{file_path_str}' successfully."}
    except PermissionError as e:
        logger.error(f"Permission error in append_to_file: {e}")
        return {"status": "error", "message": str(e)}
    except Exception as e:
        logger.error(f"Error in append_to_file: {e}")
        return {"status": "error", "message": str(e)}


def install_wordpress_plugin(data):
    """Installs a WordPress plugin."""
    logger.info("Executing install_wordpress_plugin tool")
    try:
        plugin_slug = get_tool_arg(data, 'plugin_slug', required=True, arg_type=str)
        version = get_tool_arg(data, 'version', required=False, arg_type=str)
        cmd_args = ['plugin', 'install', plugin_slug]
        if version:
            cmd_args.extend(['--version', version])
        result = run_wp_cli_command(cmd_args)
        return {"status": "success", "message": result}
    except Exception as e:
        logger.error(f"Error in install_wordpress_plugin: {e}")
        return {"status": "error", "message": str(e)}


def deactivate_wordpress_plugin(data):
    """Deactivates an installed WordPress plugin."""
    logger.info("Executing deactivate_wordpress_plugin tool")
    try:
        plugin_slug = get_tool_arg(data, 'plugin_slug', required=True, arg_type=str)
        result = run_wp_cli_command(['plugin', 'deactivate', plugin_slug])
        return {"status": "success", "message": result}
    except Exception as e:
        logger.error(f"Error in deactivate_wordpress_plugin: {e}")
        return {"status": "error", "message": str(e)}


def delete_wordpress_plugin(data):
    """Deletes a WordPress plugin."""
    logger.info("Executing delete_wordpress_plugin tool")
    try:
        plugin_slug = get_tool_arg(data, 'plugin_slug', required=True, arg_type=str)
        result = run_wp_cli_command(['plugin', 'delete', plugin_slug])
        return {"status": "success", "message": result}
    except Exception as e:
        logger.error(f"Error in delete_wordpress_plugin: {e}")
        return {"status": "error", "message": str(e)}


# --- Tool Dispatcher ---

TOOLS = {
    "get_system_information": get_system_information,
    "create_wordpress_post": create_wordpress_post,
    "activate_wordpress_plugin": activate_wordpress_plugin,
    "read_file": read_file,
    "edit_file": edit_file,
    "get_wordpress_option": get_wordpress_option,
    "update_wordpress_option": update_wordpress_option,
    "install_wordpress_theme": install_wordpress_theme,
    "activate_wordpress_theme": activate_wordpress_theme,
    "list_wordpress_themes": list_wordpress_themes,
    "get_active_wordpress_theme": get_active_wordpress_theme,
    "delete_wordpress_theme": delete_wordpress_theme,
    "append_to_file": append_to_file,
    "install_wordpress_plugin": install_wordpress_plugin,
    "deactivate_wordpress_plugin": deactivate_wordpress_plugin,
    "delete_wordpress_plugin": delete_wordpress_plugin,
}

@app.route('/a2a/task', methods=['POST'])
@require_api_key
def handle_a2a_task():
    try:
        # Handle JSON parsing errors specifically
        try:
            data = flask.request.get_json()
        except Exception as json_error:
            logger.warning(f"Invalid JSON received: {json_error}")
            return flask.jsonify({"status": "error", "message": "Invalid JSON payload"}), 400
        
        if not data:
            return flask.jsonify({"status": "error", "message": "Invalid JSON payload"}), 400

        tool_name = data.get('tool')
        if not tool_name:
            return flask.jsonify({"status": "error", "message": "Missing 'tool' field in request"}), 400

        if tool_name in TOOLS:
            logger.info(f"Received A2A task for tool: {tool_name}")
            tool_function = TOOLS[tool_name]
            # Pass the whole data dict so tools can extract args themselves
            result = tool_function(data)
            return flask.jsonify(result)
        else:
            logger.warning(f"Unknown tool requested: {tool_name}")
            return flask.jsonify({"status": "error", "message": f"Unknown tool: {tool_name}"}), 404
    except ValueError as e:
        logger.error(f"Tool argument error: {e}")
        return flask.jsonify({"status": "error", "message": f"Invalid tool arguments: {str(e)}"}), 400
    except Exception as e:
        logger.error(f"Unhandled error in /a2a/task: {e}", exc_info=True)
        return flask.jsonify({"status": "error", "message": f"An internal error occurred: {str(e)}"}), 500

@app.route('/health', methods=['GET'])
def health_check():
    return flask.jsonify({"status": "healthy", "message": "Agent is running"}), 200

@app.route('/static/<path:path>')
def send_static(path):
    return flask.send_from_directory('docs', path)

if __name__ == '__main__':
    logger.info("Agent A2A server starting on port 5000...")
    # Host 0.0.0.0 to be accessible from outside the container
    app.run(host='0.0.0.0', port=5000, debug=False) # Debug should be False for production/staging
