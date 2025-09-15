import os

REDIS_URL = os.environ.get("REDIS_URL" or "redis://localhost:6379")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:1b")
SQLALCHEMY_DATABASE_URL = "sqlite:///./db.sqlite3"
