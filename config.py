import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-key-change-this')
    # Absolute path to database folder, works even if the project is moved
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DB_PATH = os.path.join(BASE_DIR, "database", "mydb.db")

    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_PATH.replace(os.sep, '/')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Reddit OAuth
    REDDIT_USERNAME = os.getenv('REDDIT_USERNAME')
    REDDIT_PASSWORD = os.getenv('REDDIT_PASSWORD')
    
    # Groq
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    
    # App Settings
    ANALYSES_PER_RUN = 30  # Reduced for faster testing
    FREE_TIER_LIMIT = 10