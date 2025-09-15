import json
import asyncio
from uuid import uuid4
from datetime import datetime
from fastapi import FastAPI,HTTPException,status,Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.db import SessionLocal
from app.models import Document,DocumentStatus
from app.summarizer import summarize_url
import subprocess


app=FastAPI()
def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()

queue=asyncio.Queue()
worker_started=False

async def worker():
    while True:
        doc_id = await queue.get()
        db = SessionLocal()
        try:
            doc = db.get(Document, doc_id)
            if not doc:
                continue
            doc.status = DocumentStatus.RUNNING
            db.commit()
            summary = summarize_url(doc.url, progress_cb=lambda p: None)
            if isinstance(summary, str):
                try:
                    summary = json.loads(summary)
                except json.JSONDecodeError as e:
                    doc.status = DocumentStatus.FAILED
                    doc.error = str(e)
                    db.commit()
                    continue
            doc.summary = summary
            doc.status = DocumentStatus.SUCCESS
            doc.data_progress = 1.0
            doc.updated_at = datetime.utcnow()
            db.commit()
        except Exception as e:
            doc = db.get(Document, doc_id)
            if doc:
                doc.status = DocumentStatus.FAILED
                doc.error = str(e)
                db.commit()
        finally:
            db.close()
            queue.task_done()

@app.on_event("startup")
async def start(): global worker_started; import app.db_migrate;     asyncio.create_task(worker()) if not worker_started else None; worker_started=True

@app.post("/documents/",status_code=202)
async def submit(payload:dict,db:Session=Depends(get_db)):
    name,url=payload["name"],payload["URL"]
    if db.query(Document).filter((Document.name==name)|(Document.url==url)).first():
        raise HTTPException(409,"Conflict")
    doc=Document(document_uuid=str(uuid4()),name=name,url=url,status=DocumentStatus.PENDING,created_at=datetime.utcnow(),updated_at=datetime.utcnow())
    db.add(doc); db.commit()
    await queue.put(doc.document_uuid)
    return {"document_uuid":doc.document_uuid,"status":doc.status,"name":doc.name,"URL":doc.url,"summary":doc.summary,"data_progress":doc.data_progress,"error":doc.error}

@app.get("/documents/{uuid}")
def get(uuid:str,db:Session=Depends(get_db)):
    doc=db.get(Document,uuid)
    if not doc: raise HTTPException(404,"Not found")
    return {"document_uuid":doc.document_uuid,"status":doc.status,"name":doc.name,"URL":doc.url,"summary":doc.summary,"data_progress":doc.data_progress,"error":doc.error}

@app.get("/healthz")
def health(): return {"status":"ok"}




if __name__ == "__main__":
    subprocess.run(["python", "-m", "app.db_migrate"], check=True)
    subprocess.run([
        "uvicorn", "app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--workers", "1"
    ], check=True)