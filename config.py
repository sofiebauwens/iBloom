import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///bloom.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

    # App-specific settings
    MAX_QUESTIONS_PER_SESSION = 5
    SESSION_TIMEOUT_HOURS = 24
    MIN_RESPONSE_LENGTH = 1
    MAX_RESPONSE_LENGTH = 500