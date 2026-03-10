import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24)
    ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'admin@radar.com')
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin123')
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY', '')
    
    # PostgreSQL Database
    DATABASE_URL = os.environ.get('DATABASE_URL')
    
    # Telegram Settings
    TELEGRAM_API_ID = os.environ.get('TELEGRAM_API_ID')
    TELEGRAM_API_HASH = os.environ.get('TELEGRAM_API_HASH')
    
    # AI Settings
    AI_MODEL = 'qwen/qwen-2.5-72b-instruct'
    AI_ENABLED = os.environ.get('AI_ENABLED', 'True').lower() == 'true'
    
    # Radar Settings
    RADAR_ENABLED = os.environ.get('RADAR_ENABLED', 'False').lower() == 'true'
    LOG_FILE = 'radar.log'
