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


app = FastAPI()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def summarize_and_update(doc_id: str, db: Session):
    doc = db.get(Document, doc_id)
    try:
        summary = await summarize_url(doc.url, progress_cb=lambda p: None)
        doc.summary = summary
        doc.status = DocumentStatus.SUCCESS
    except Exception as e:
        doc.status = DocumentStatus.FAILED
        doc.error = str(e)
    doc.updated_at = datetime.utcnow()
    db.commit()


@app.post("/documents/", status_code=202)
def submit(payload: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    name, url = payload["name"], payload["URL"]
    if (
        db.query(Document)
        .filter((Document.name == name) | (Document.url == url))
        .first()
    ):
        raise HTTPException(409, "Conflict")
    doc = Document(
        document_uuid=str(uuid4()),
        status=DocumentStatus.RUNNING,
        name=name,
        url=url,
    )
    db.add(doc)
    db.commit()
    background_tasks.add_task(summarize_and_update, doc.document_uuid, db)
    return {
        "document_uuid": doc.document_uuid,
        "status": DocumentStatus.PENDING,
        "name": doc.name,
        "URL": doc.url,
        "summary": None,
    }


@app.get("/documents/{uuid}")
def get(uuid: str, db: Session = Depends(get_db)):
    doc = db.get(Document, uuid)
    if not doc:
        raise HTTPException(404, "Not found")
    return {
        "document_uuid": doc.document_uuid,
        "status": doc.status,
        "name": doc.name,
        "URL": doc.url,
        "summary": doc.summary,
        "data_progress": doc.data_progress,
        "error": doc.error,
    }


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
