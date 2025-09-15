import json
from uuid import uuid4
from datetime import datetime
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import Document, DocumentStatus
from app.summarizer import summarize_url
import subprocess
from fastapi import BackgroundTasks
from dotenv import load_dotenv
from typing import Generator
import redis
import logging

from app.config import REDIS_URL

# Initialize Redis client
redis_client = redis.Redis.from_url(REDIS_URL or "redis://localhost:6379")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)

logger = logging.getLogger(__name__)

app = FastAPI()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get DB session
    :return: SessionLocal: DB session
    :rtype: Session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def summarize_and_update(doc_id: str) -> None:
    """
    Summarizes the document and updates the database
    :param doc_id: Document ID
    :return: None
    """
    db = SessionLocal()
    try:
        doc = db.get(Document, doc_id)
        if not doc:
            logger.error(f"Document {doc_id} not found")
            return

        logger.info(f"Starting summarization for document: {doc_id}")

        def update_progress(progress):
            # Store progress in Redis with expiration
            redis_client.setex(
                f"progress:{doc_id}", 3600, progress
            )  # Expires in 1 hour

        try:
            summary = await summarize_url(doc.url, progress_cb=update_progress)
            doc.summary = summary
            doc.status = DocumentStatus.SUCCESS
            logger.info(f"Summarization succeeded for document: {doc_id}")
            # Clean up progress when done
            redis_client.delete(f"progress:{doc_id}")
        except Exception as e:
            doc.status = DocumentStatus.FAILED
            doc.error = str(e)
            logger.error(
                f"Summarization failed for document: {doc_id} - {e}", exc_info=True
            )
            redis_client.delete(f"progress:{doc_id}")
        doc.updated_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


@app.post("/documents/", status_code=202)
def submit(
    payload: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> JSONResponse:
    """
    Submit a new document for summarization
    :param payload: dict with "name" and "URL" keys
    :param background_tasks: BackgroundTasks
    :param db: DB session
    :return: JSONResponse with document details
    """
    name, url = payload["name"], payload["URL"]
    if (
        db.query(Document)
        .filter((Document.name == name) | (Document.url == url))
        .first()
    ):
        logger.warning(
            f"Conflict: Document with name '{name}' or URL '{url}' already exists."
        )
        raise HTTPException(409, "Conflict")
    doc = Document(
        document_uuid=str(uuid4()),
        status=DocumentStatus.RUNNING,
        name=name,
        url=url,
    )
    db.add(doc)
    db.commit()
    logger.info(f"Submitted new document: {doc.document_uuid}")
    background_tasks.add_task(summarize_and_update, str(doc.document_uuid))
    return JSONResponse(
        content={
            "document_uuid": doc.document_uuid,
            "status": doc.status,
            "name": doc.name,
            "URL": doc.url,
            "summary": doc.summary,
            "progress": 0.0,
        }
    )


@app.get("/documents/{document_id}")
def get_document(document_id: str, db: Session = Depends(get_db)) -> JSONResponse:
    """
    Get document status and summary
    :param document_id: Document ID
    :param db: DB session
    :return: Document details
    """
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    # Get progress from Redis
    progress = redis_client.get(f"progress:{document_id}")
    if doc.status == DocumentStatus.SUCCESS:
        progress_value = 1.0
    else:
        progress_value = float(progress) if progress else None

    return JSONResponse(
        content={
            "document_uuid": doc.document_uuid,
            "status": doc.status,
            "name": doc.name,
            "URL": doc.url,
            "summary": doc.summary,
            "progress": progress_value,
        }
    )


@app.get("/healthz")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    subprocess.run(["python", "-m", "app.db_migrate"], check=True)
    subprocess.run(
        [
            "uvicorn",
            "app.main:app",
            "--host",
            "0.0.0.0",
            "--port",
            "8000",
            "--workers",
            "1",
        ],
        check=True,
    )
