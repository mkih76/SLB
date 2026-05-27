import os
import sys
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Validate critical secrets at import time
_PLACEHOLDER_SECRETS = {
    'SECRET_KEY': 'dev-secret-key-change-in-production',
    'JWT_SECRET': 'jwt-secret-change-in-production',
}

for _env_key, _placeholder in _PLACEHOLDER_SECRETS.items():
    _val = os.getenv(_env_key, '')
    if not _val or _val == _placeholder:
        if os.getenv('FLASK_ENV') == 'production' or os.getenv('ENV') == 'production':
            logger.error(f"FATAL: {_env_key} is not set or uses default value. Refusing to start in production.")
            sys.exit(1)
        else:
            logger.warning(f"WARNING: {_env_key} is using default value. Set it in .env for production.")


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_SECRET = os.getenv('JWT_SECRET', 'jwt-secret-change-in-production')
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRE_DAYS = int(os.getenv('JWT_EXPIRE_DAYS', 7))

    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/slb.db')
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/slb.db')

    # LLM Config
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'deepseek')
    LLM_MODEL = os.getenv('LLM_MODEL', 'deepseek-chat')
    LLM_API_KEY = os.getenv('LLM_API_KEY', '')
    LLM_BASE_URL = os.getenv('LLM_BASE_URL', 'https://api.deepseek.com/v1')
    LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', 0.3))
    LLM_MAX_TOKENS = int(os.getenv('LLM_MAX_TOKENS', 1000))

    # Redis Cache
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    CACHE_TTL = int(os.getenv('CACHE_TTL', 86400))

    # Telegram Bot
    TG_BOT_TOKEN = os.getenv('TG_BOT_TOKEN', '')

    # Upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = 'uploads'


config = Config()

# Module-level exports for convenience
SECRET_KEY = Config.SECRET_KEY
JWT_SECRET = Config.JWT_SECRET
JWT_ALGORITHM = Config.JWT_ALGORITHM
JWT_EXPIRE_DAYS = Config.JWT_EXPIRE_DAYS
DATABASE_URL = Config.DATABASE_URL
DATABASE_PATH = Config.DATABASE_PATH
LLM_PROVIDER = Config.LLM_PROVIDER
LLM_MODEL = Config.LLM_MODEL
LLM_API_KEY = Config.LLM_API_KEY
LLM_BASE_URL = Config.LLM_BASE_URL
LLM_TEMPERATURE = Config.LLM_TEMPERATURE
LLM_MAX_TOKENS = Config.LLM_MAX_TOKENS
REDIS_HOST = Config.REDIS_HOST
REDIS_PORT = Config.REDIS_PORT
REDIS_DB = Config.REDIS_DB
CACHE_TTL = Config.CACHE_TTL
TG_BOT_TOKEN = Config.TG_BOT_TOKEN
