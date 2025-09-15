import os

DB_PATH=os.getenv('DB_PATH','/data/data.db')
OLLAMA_HOST=os.getenv('OLLAMA_HOST','http://ollama:11434')
OLLAMA_MODEL=os.getenv('OLLAMA_MODEL','gemma3:1b')
