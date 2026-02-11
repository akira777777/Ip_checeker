"""
Configuration management for IP Checker application.
Environment-based configuration with sensible defaults.
"""

import os


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32)
    JSON_SORT_KEYS = False
    GEO_CACHE_TTL = int(os.environ.get('GEO_CACHE_TTL', 3600))
    GEO_LOOKUP_LIMIT = int(os.environ.get('GEO_LOOKUP_LIMIT', 15))
    LOCAL_ONLY = os.environ.get('LOCAL_ONLY', 'True').lower() == 'true'
    FORCE_HTTPS = os.environ.get('FORCE_HTTPS', 'False').lower() == 'true'
    CACHE_DIR = os.environ.get('CACHE_DIR', './cache')


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    TESTING = False
    FORCE_HTTPS = True


class TestingConfig(Config):
    """Testing configuration."""
    DEBUG = True
    TESTING = True
    GEO_LOOKUP_LIMIT = 5
    LOCAL_ONLY = False


config_by_name = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}