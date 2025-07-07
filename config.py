import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration"""
    # Flask settings
    DEBUG = False
    TESTING = False
    
    # API settings
    A2A_API_KEY = os.getenv('A2A_API_KEY')
    
    # WordPress paths
    WP_PATH = "/var/www/html"
    SAFE_BASE_PATH = os.path.realpath(WP_PATH)
    
    # Logging settings
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FORMAT = 'json'
    
    # Security settings
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*').split(',')
    RATE_LIMIT = os.getenv('RATE_LIMIT', '100/minute')
    
    @staticmethod
    def to_dict() -> Dict[str, Any]:
        """Convert config to dictionary"""
        return {
            key: getattr(Config, key) 
            for key in dir(Config) 
            if not key.startswith('_') and key.isupper()
        }

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    WP_PATH = "/tmp/wordpress"
    SAFE_BASE_PATH = os.path.realpath(WP_PATH)

class ProductionConfig(Config):
    """Production configuration"""
    LOG_FORMAT = 'json'

# Map environment to config class
config_by_name = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig
}

# Active configuration
active_config = config_by_name[os.getenv('FLASK_ENV', 'development')]