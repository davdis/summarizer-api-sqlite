import json
import aiohttp
import asyncio
from newspaper import Article
from typing import Generator
from sqlalchemy.orm import Session
import logging
import redis
from datetime import datetime

from app.models import Document, DocumentStatus
from app.db import SessionLocal
from app.config import OLLAMA_HOST, OLLAMA_MODEL

logger = logging.getLogger(__name__)

redis_client = redis.Redis(host="redis", port=6379)


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


async def summarize_url(url: str, progress_cb=None) -> str:
    """
    Summarize the article at the given URL using the Ollama API.
    :param url: URL of the article to summarize
    :param progress_cb: Optional callback to report progress (0.0 to 1.0)
    :return: Summary text
    """
    # These are still blocking, but newspaper doesn't have async versions
    # We'll run them in a thread pool
    loop = asyncio.get_event_loop()

    # Run newspaper operations in thread pool to avoid blocking
    def download_and_parse():
        article = Article(url)
        article.download()
        article.parse()
        return f"{article.title}\n\n{article.text}"

    article_text = await loop.run_in_executor(None, download_and_parse)

    if progress_cb:
        progress_cb(0.5)

    # Use aiohttp for async HTTP requests
    async with aiohttp.ClientSession() as session:
        ollama_url = OLLAMA_HOST
        prompt = (
            f"Summarize the following article in less than 1500 chars:\n{article_text}"
        )
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": True,  # Explicitly enable streaming
        }

        async with session.post(
            ollama_url,
            json=payload,
            timeout=aiohttp.ClientTimeout(
                total=3600, sock_read=3500
            ),  # Different timeouts
        ) as response:
            response_text = ""

            # Handle streaming response properly
            async for chunk in response.content.iter_chunked(1024):
                if chunk:
                    try:
                        # Each chunk might contain multiple JSON objects
                        for line in chunk.decode("utf-8").split("\n"):
                            if line.strip():
                                data = json.loads(line)
                                if "response" in data:
                                    response_text += data["response"]
                                # Check if done
                                if data.get("done", False):
                                    break
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        continue

    if progress_cb:
        progress_cb(1.0)

    return response_text
