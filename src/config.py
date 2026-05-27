import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_SECRET = os.getenv('JWT_SECRET', 'jwt-secret-change-in-production')
    JWT_ALGORITHM = 'HS256'
    JWT_EXPIRE_DAYS = 7

    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///data/slb.db')
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/slb.db')

    # LLM Config
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'deepseek')
    LLM_MODEL = os.getenv('LLM_MODEL', 'deepseek-chat')
    LLM_API_KEY = os.getenv('LLM_API_KEY', '')
    LLM_BASE_URL = os.getenv('LLM_BASE_URL', 'https://api.deepseek.com/v1')
    LLM_TEMPERATURE = 0.3
    LLM_MAX_TOKENS = 1000

    # Redis Cache
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))
    CACHE_TTL = 86400  # 24 hours

    # Admin
    ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', 'admin123456')

    # Telegram Bot
    TG_BOT_TOKEN = os.getenv('TG_BOT_TOKEN', '')

    # Upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB
    UPLOAD_FOLDER = 'uploads'
