import os
import sys
import json
import logging
import time
import hashlib
import subprocess
import signal
import threading
from datetime import datetime, timedelta
from functools import wraps
from typing import Dict, Any, Optional, List
from pathlib import Path
import secrets

import flask
from flask import Flask, request, jsonify, g
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
from flask_talisman import Talisman
import jwt
from werkzeug.security import check_password_hash, generate_password_hash
import redis
from prometheus_client import Counter, Histogram, Gauge, generate_latest
import psutil

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(pathname)s:%(lineno)d',
    handlers=[
        logging.FileHandler('/app/logs/agent.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Metrics
REQUEST_COUNT = Counter('agent_requests_total', 'Total requests', ['method', 'endpoint', 'status'])
REQUEST_DURATION = Histogram('agent_request_duration_seconds', 'Request duration')
ACTIVE_CONNECTIONS = Gauge('agent_active_connections', 'Active connections')
SYSTEM_MEMORY = Gauge('agent_system_memory_percent', 'System memory usage')
SYSTEM_CPU = Gauge('agent_system_cpu_percent', 'System CPU usage')

# Configuration
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_urlsafe(32))
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', secrets.token_urlsafe(32))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    WP_PATH = os.environ.get('WP_PATH', '/var/www/html')
    SAFE_BASE_PATH = os.path.realpath(os.environ.get('WP_PATH', '/var/www/html'))
    AGENT_API_KEY = os.environ.get('AGENT_API_KEY', '')
    RATE_LIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379')
    MAX_FILE_SIZE = int(os.environ.get('MAX_FILE_SIZE', '10485760'))  # 10MB
    ALLOWED_EXTENSIONS = set(os.environ.get('ALLOWED_EXTENSIONS', 'php,txt,css,js,html,json,yaml,yml').split(','))
    BACKUP_RETENTION_DAYS = int(os.environ.get('BACKUP_RETENTION_DAYS', '7'))
    ENABLE_PROMETHEUS = os.environ.get('ENABLE_PROMETHEUS', 'true').lower() == 'true'

app = Flask(__name__)
app.config.from_object(Config)

# Security headers
Talisman(app, force_https=False)  # Set to True in production with HTTPS

# CORS configuration
CORS(app, origins=os.environ.get('ALLOWED_ORIGINS', '').split(',') if os.environ.get('ALLOWED_ORIGINS') else ['http://localhost'])

# Rate limiting
limiter = Limiter(
    app,
    key_func=get_remote_address,
    storage_uri=Config.RATE_LIMIT_STORAGE_URL,
    default_limits=["200 per day", "50 per hour"]
)

# Redis client for caching
try:
    redis_client = redis.from_url(Config.REDIS_URL, decode_responses=True)
    redis_client.ping()
    logger.info("Redis connection established")
except Exception as e:
    logger.warning(f"Redis connection failed: {e}. Falling back to in-memory cache.")
    redis_client = None

# In-memory cache fallback
memory_cache = {}

# Circuit breaker pattern
class CircuitBreaker:
    def __init__(self, failure_threshold=5, recovery_timeout=60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        
    def call(self, func, *args, **kwargs):
        if self.state == 'OPEN':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'HALF_OPEN'
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise
    
    def on_success(self):
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'

wp_cli_circuit_breaker = CircuitBreaker()

# Authentication decorators
def token_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'status': 'error', 'message': 'Token is missing'}), 401
        
        try:
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Verify JWT token
            data = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
            g.current_user = data
            
        except jwt.ExpiredSignatureError:
            return jsonify({'status': 'error', 'message': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'status': 'error', 'message': 'Invalid token'}), 401
        
        return f(*args, **kwargs)
    return decorated_function

def api_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key or api_key != Config.AGENT_API_KEY:
            return jsonify({'status': 'error', 'message': 'Invalid API key'}), 401
        return f(*args, **kwargs)
    return decorated_function

# Request logging middleware
@app.before_request
def log_request_info():
    start_time = time.time()
    g.start_time = start_time
    
    # Log request details
    logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")
    
    # Update metrics
    ACTIVE_CONNECTIONS.inc()

@app.after_request
def log_response_info(response):
    duration = time.time() - g.start_time
    
    # Log response details
    logger.info(f"Response: {response.status_code} in {duration:.3f}s")
    
    # Update metrics
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.endpoint or 'unknown',
        status=response.status_code
    ).inc()
    
    REQUEST_DURATION.observe(duration)
    ACTIVE_CONNECTIONS.dec()
    
    return response

# Caching utilities
def cache_get(key: str) -> Optional[Any]:
    if redis_client:
        try:
            data = redis_client.get(key)
            return json.loads(data) if data else None
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
            return memory_cache.get(key)
    return memory_cache.get(key)

def cache_set(key: str, value: Any, ttl: int = 300):
    if redis_client:
        try:
            redis_client.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")
            memory_cache[key] = value
    else:
        memory_cache[key] = value

# Enhanced WP-CLI command execution
def run_wp_cli_command(args: List[str], decode_json: bool = False, timeout: int = 30) -> Any:
    """Enhanced WP-CLI command execution with error handling and logging."""
    base_command = ['wp', f'--path={Config.WP_PATH}', '--allow-root']
    command = base_command + args
    
    # Create cache key
    cache_key = f"wp_cli:{hashlib.md5(':'.join(command).encode()).hexdigest()}"
    
    # Check cache for read-only commands
    if args[0] in ['option', 'post', 'plugin'] and 'get' in args:
        cached_result = cache_get(cache_key)
        if cached_result:
            return cached_result
    
    logger.info(f"Executing WP-CLI command: {' '.join(command)}")
    
    try:
        result = wp_cli_circuit_breaker.call(
            subprocess.run,
            command,
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout
        )
        
        output = result.stdout.strip()
        
        if decode_json:
            parsed_output = json.loads(output) if output else {}
        else:
            parsed_output = output
        
        # Cache successful results
        if args[0] in ['option', 'post', 'plugin'] and 'get' in args:
            cache_set(cache_key, parsed_output, ttl=600)
        
        return parsed_output
        
    except subprocess.TimeoutExpired:
        logger.error(f"WP-CLI command timeout: {' '.join(command)}")
        raise Exception("Command timeout")
    except subprocess.CalledProcessError as e:
        logger.error(f"WP-CLI command failed: {e.stderr}")
        raise Exception(f"WP-CLI Error: {e.stderr.strip() if e.stderr else 'Unknown error'}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {e}")
        raise Exception(f"Invalid JSON response: {output}")

# Input validation
def validate_input(data: Dict[str, Any], required_fields: List[str], field_types: Dict[str, type] = None) -> Dict[str, Any]:
    """Validate input data with required fields and type checking."""
    args = data.get('args', {})
    
    for field in required_fields:
        if field not in args:
            raise ValueError(f"Missing required field: {field}")
    
    if field_types:
        for field, expected_type in field_types.items():
            if field in args and not isinstance(args[field], expected_type):
                raise ValueError(f"Field '{field}' must be of type {expected_type.__name__}")
    
    return args

# File path validation
def validate_file_path(file_path_str: str) -> str:
    """Enhanced file path validation with security checks."""
    # Normalize path and remove leading slashes
    normalized_path = os.path.normpath(file_path_str.lstrip('/\\'))
    
    # Construct absolute path
    abs_file_path = os.path.join(Config.SAFE_BASE_PATH, normalized_path)
    real_abs_file_path = os.path.realpath(abs_file_path)
    
    # Security check: ensure path is within allowed directory
    if not real_abs_file_path.startswith(Config.SAFE_BASE_PATH):
        raise PermissionError(f"Path '{file_path_str}' is outside allowed directory")
    
    # Check file extension
    file_ext = Path(file_path_str).suffix.lstrip('.')
    if file_ext and file_ext not in Config.ALLOWED_EXTENSIONS:
        raise PermissionError(f"File extension '{file_ext}' not allowed")
    
    return real_abs_file_path

# Backup utilities
def create_backup(file_path: str) -> str:
    """Create backup of file before modification."""
    backup_dir = '/app/backups'
    os.makedirs(backup_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"{Path(file_path).name}_{timestamp}.backup"
    backup_path = os.path.join(backup_dir, backup_name)
    
    try:
        with open(file_path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        return backup_path
    except Exception as e:
        logger.error(f"Backup creation failed: {e}")
        raise

def cleanup_old_backups():
    """Clean up old backup files."""
    backup_dir = '/app/backups'
    if not os.path.exists(backup_dir):
        return
    
    cutoff_time = time.time() - (Config.BACKUP_RETENTION_DAYS * 24 * 60 * 60)
    
    for file_path in Path(backup_dir).glob('*.backup'):
        if file_path.stat().st_mtime < cutoff_time:
            try:
                file_path.unlink()
                logger.info(f"Cleaned up old backup: {file_path}")
            except Exception as e:
                logger.error(f"Failed to clean up backup {file_path}: {e}")

# Enhanced agent tools
def get_system_information(data: Dict[str, Any]) -> Dict[str, Any]:
    """Get comprehensive system information."""
    logger.info("Executing get_system_information tool")
    
    try:
        info = {
            'timestamp': datetime.now().isoformat(),
            'system': {
                'os': subprocess.run(['uname', '-a'], capture_output=True, text=True).stdout.strip(),
                'uptime': subprocess.run(['uptime'], capture_output=True, text=True).stdout.strip(),
                'memory': {
                    'total': psutil.virtual_memory().total,
                    'available': psutil.virtual_memory().available,
                    'percent': psutil.virtual_memory().percent
                },
                'cpu': {
                    'count': psutil.cpu_count(),
                    'percent': psutil.cpu_percent(interval=1)
                },
                'disk': {
                    'total': psutil.disk_usage('/').total,
                    'used': psutil.disk_usage('/').used,
                    'free': psutil.disk_usage('/').free,
                    'percent': psutil.disk_usage('/').percent
                }
            },
            'application': {
                'python_version': sys.version,
                'agent_version': '2.0.0',
                'flask_version': flask.__version__
            }
        }
        
        # WordPress information
        try:
            wp_info = run_wp_cli_command(['core', 'version', '--extra', '--format=json'], decode_json=True)
            info['wordpress'] = wp_info
        except Exception as e:
            logger.warning(f"Failed to get WordPress info: {e}")
            info['wordpress'] = {'error': str(e)}
        
        # Update system metrics
        SYSTEM_MEMORY.set(info['system']['memory']['percent'])
        SYSTEM_CPU.set(info['system']['cpu']['percent'])
        
        return {'status': 'success', 'data': info}
        
    except Exception as e:
        logger.error(f"Error in get_system_information: {e}")
        return {'status': 'error', 'message': str(e)}

def create_wordpress_post(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create WordPress post with enhanced validation."""
    logger.info("Executing create_wordpress_post tool")
    
    try:
        args = validate_input(data, ['title', 'content'], {
            'title': str,
            'content': str,
            'status': str,
            'post_type': str
        })
        
        # Sanitize inputs
        title = args['title'][:200]  # Limit title length
        content = args['content'][:50000]  # Limit content length
        status = args.get('status', 'publish')
        post_type = args.get('post_type', 'post')
        
        # Validate status and post_type
        valid_statuses = ['publish', 'draft', 'pending', 'private']
        valid_post_types = ['post', 'page']
        
        if status not in valid_statuses:
            raise ValueError(f"Invalid status. Must be one of: {valid_statuses}")
        
        if post_type not in valid_post_types:
            raise ValueError(f"Invalid post_type. Must be one of: {valid_post_types}")
        
        cmd_args = [
            'post', 'create',
            f'--post_title={title}',
            f'--post_content={content}',
            f'--post_status={status}',
            f'--post_type={post_type}',
            '--porcelain'
        ]
        
        post_id = run_wp_cli_command(cmd_args)
        
        # Invalidate related caches
        cache_keys = [f"wp_cli:*post*", f"wp_cli:*{post_type}*"]
        for key in cache_keys:
            if redis_client:
                redis_client.delete(key)
        
        return {
            'status': 'success',
            'message': f'{post_type.capitalize()} created successfully',
            'post_id': post_id,
            'post_url': f"{os.environ.get('WORDPRESS_SITE_URL', 'http://localhost')}/?p={post_id}"
        }
        
    except Exception as e:
        logger.error(f"Error in create_wordpress_post: {e}")
        return {'status': 'error', 'message': str(e)}

def read_file(data: Dict[str, Any]) -> Dict[str, Any]:
    """Read file with enhanced security and validation."""
    logger.info("Executing read_file tool")
    
    try:
        args = validate_input(data, ['file_path'], {'file_path': str})
        file_path_str = args['file_path']
        
        target_file_path = validate_file_path(file_path_str)
        
        if not os.path.exists(target_file_path):
            return {'status': 'error', 'message': f'File not found: {file_path_str}'}
        
        if not os.path.isfile(target_file_path):
            return {'status': 'error', 'message': f'Path is not a file: {file_path_str}'}
        
        # Check file size
        file_size = os.path.getsize(target_file_path)
        if file_size > Config.MAX_FILE_SIZE:
            return {'status': 'error', 'message': f'File too large: {file_size} bytes'}
        
        with open(target_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Create file hash for integrity checking
        file_hash = hashlib.sha256(content.encode()).hexdigest()
        
        return {
            'status': 'success',
            'file_path': file_path_str,
            'content': content,
            'size': file_size,
            'hash': file_hash,
            'last_modified': datetime.fromtimestamp(os.path.getmtime(target_file_path)).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error in read_file: {e}")
        return {'status': 'error', 'message': str(e)}

def edit_file(data: Dict[str, Any]) -> Dict[str, Any]:
    """Edit file with backup and validation."""
    logger.info("Executing edit_file tool")
    
    try:
        args = validate_input(data, ['file_path', 'content'], {
            'file_path': str,
            'content': str
        })
        
        file_path_str = args['file_path']
        content = args['content']
        
        target_file_path = validate_file_path(file_path_str)
        
        # Check content size
        if len(content.encode()) > Config.MAX_FILE_SIZE:
            return {'status': 'error', 'message': 'Content too large'}
        
        # Create backup if file exists
        backup_path = None
        if os.path.exists(target_file_path):
            backup_path = create_backup(target_file_path)
        
        # Write file atomically
        temp_file = f"{target_file_path}.tmp"
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(content)
            
            # Atomic rename
            os.rename(temp_file, target_file_path)
            
            # Verify write
            with open(target_file_path, 'r', encoding='utf-8') as f:
                written_content = f.read()
            
            if written_content != content:
                raise Exception("File write verification failed")
            
            # Create content hash
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            
            return {
                'status': 'success',
                'message': f'File {file_path_str} written successfully',
                'backup_path': backup_path,
                'size': len(content.encode()),
                'hash': content_hash
            }
            
        except Exception as e:
            # Cleanup temp file
            if os.path.exists(temp_file):
                os.unlink(temp_file)
            raise
            
    except Exception as e:
        logger.error(f"Error in edit_file: {e}")
        return {'status': 'error', 'message': str(e)}

# Additional tools
def get_wordpress_plugins(data: Dict[str, Any]) -> Dict[str, Any]:
    """Get WordPress plugins list."""
    logger.info("Executing get_wordpress_plugins tool")
    
    try:
        plugins = run_wp_cli_command(['plugin', 'list', '--format=json'], decode_json=True)
        return {'status': 'success', 'plugins': plugins}
    except Exception as e:
        logger.error(f"Error in get_wordpress_plugins: {e}")
        return {'status': 'error', 'message': str(e)}

def get_wordpress_themes(data: Dict[str, Any]) -> Dict[str, Any]:
    """Get WordPress themes list."""
    logger.info("Executing get_wordpress_themes tool")
    
    try:
        themes = run_wp_cli_command(['theme', 'list', '--format=json'], decode_json=True)
        return {'status': 'success', 'themes': themes}
    except Exception as e:
        logger.error(f"Error in get_wordpress_themes: {e}")
        return {'status': 'error', 'message': str(e)}

def backup_database(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create database
