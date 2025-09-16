from uuid import uuid4
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.models import Document, DocumentStatus
from app.summarizer import summarize_and_update, get_db
from fastapi import BackgroundTasks
import redis
import logging
from app.schemas import DocumentCreate
from uuid import UUID

redis_client = redis.Redis(host="redis", port=6379)
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
)

logger = logging.getLogger(__name__)

app = FastAPI()


@app.post("/documents/", status_code=202)
def submit(
    payload: DocumentCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> JSONResponse:
    """
    Submit a new document for summarization
    :param payload: DocumentCreate
    :param background_tasks: BackgroundTasks
    :param db: DB session
    :return: Document details
    1. Check for exact match (name and url): re-summarize
    2. Check for uniqueness (name or url): if conflict, return 409
    3. Create new document and start summarization
    4. Return document details with status 202
    """
    name, url = payload.name, str(payload.url)

    # Check for exact match (re-summarization)
    doc = (
        db.query(Document)
        .filter((Document.name == name) & (Document.url == url))
        .first()
    )
    if doc:
        # Re-summarization: reset and start summarization again
        doc.status = DocumentStatus.RUNNING
        doc.summary = None
        doc.error = None
        doc.updated_at = datetime.utcnow()
        db.commit()
        logger.info(f"Re-summarization triggered for document: {doc.document_uuid}")
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

    # Uniqueness: deny if name or url is already in use (but not both)
    conflict = (
        db.query(Document)
        .filter((Document.name == name) | (Document.url == url))
        .first()
    )
    if conflict:
        logger.warning(
            f"Conflict: Document with name '{name}' or URL '{url}' already exists."
        )
        raise HTTPException(409, "Conflict")

    # Create new document
    doc = Document(
        document_uuid=str(uuid4()),
        status=DocumentStatus.PENDING,
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
def get_document(document_id: UUID, db: Session = Depends(get_db)) -> JSONResponse:
    """
    Get document status and summary
    :param document_id: Document ID
    :param db: DB session
    :return: Document details
    1. Fetch document from DB
    2. If not found, return 404
    3. Get progress from Redis
    4. Return document details with progress
    """
    doc = db.get(Document, str(document_id))
    if not doc:
        raise HTTPException(404, "Document not found")

    # Get progress from Redis
    progress = redis_client.get(f"progress:{document_id}")
    if doc.status == DocumentStatus.SUCCESS:
        progress_value = 1.0
    else:
        progress_value = float(progress.decode()) if progress else 0.0
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
