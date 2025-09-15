import os

#DB_PATH = os.getenv("DB_PATH", "/data/data.db")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11435/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:1b")
SQLALCHEMY_DATABASE_URL = "sqlite:///./db.sqlite3"