# Project README

## Overview
This application is a document summarization API built with FastAPI. It leverages Redis for progress tracking, SQLite for persistent storage, and integrates with the Ollama LLM service for generating summaries. The app is containerized using Docker Compose, enabling seamless orchestration of its services.

## Architecture

### Components

#### API Service (api):
Built with FastAPI.
Handles document submission, status tracking, and summary retrieval.
Communicates with Redis for progress updates.
Stores document metadata in SQLite.
Calls Ollama for LLM-based summarization.
#### Redis Service (redis):
Used for fast, ephemeral progress tracking.
Accessible from the API container via the Docker network.
#### Ollama Service (ollama):
Provides LLM endpoints for text generation.
Exposes port 11434 inside the Docker network.
#### Database:
SQLite file (db.sqlite3) for document metadata and results.


#### Data Flow

#### 1. Document Submission:
User sends a POST request to /documents/ with a document URL.
API stores metadata in SQLite and starts the summarization process.
#### 2. Summarization:
API asynchronously calls Ollama via HTTP (http://ollama:11434/api/generate).
Progress is updated in Redis (progress:{doc_id}).
#### 3. Progress Tracking:
User can query progress via API endpoints.
API reads progress from Redis.
#### 4. Result Retrieval:
Once summarization is complete, the summary is stored and can be retrieved via GET requests.

### Configuration
#### Environment Variables:
- REDIS_URL: Redis connection string (default: redis://localhost:6379, but should be redis://redis:6379 in Docker).
- OLLAMA_HOST: Ollama endpoint (default: http://ollama:11434/api/generate).
- OLLAMA_MODEL: LLM model name (default: gemma3:1b).
#### Docker Compose:
- Defines all services and their networks.
- Maps ports for external access if needed.
### Key Files
- app/main.py: FastAPI application logic.
- app/config.py: Configuration and environment variable management.
- app/summarizer.py: Summarization logic and Ollama integration.
- app/models.py: Database models.
- docker-compose.yml: Service orchestration.

### Design Decisions
#### Containerization:
- Ensures reproducibility and easy deployment.
- Services communicate via Docker network using service names.
#### Async Processing:
- Summarization is handled asynchronously to avoid blocking API requests.
#### Progress Tracking:
- Redis is used for fast, ephemeral state (progress), decoupled from persistent storage.
#### LLM Integration:
- Ollama is used for flexible, local LLM inference.
### Usage
1. Start the app:
Run 
```sh
docker compose up --build
``` 
to start all services.
2. Submit a document:
POST to /documents/ with a JSON payload containing the document URL.
```sh
curl -X POST "http://localhost:8000/documents/"      -H "Content-Type: application/json"      -d '{"name": "example_name", "URL": "example_url"}'
```
3. Check progress:
GET /documents/{id} to retrieve status and summary.
```sh
curl -X GET "http://localhost:8000/documents/example_uid"
```