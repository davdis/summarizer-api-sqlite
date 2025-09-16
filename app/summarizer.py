import json
import aiohttp
import asyncio
import requests
from app.config import OLLAMA_MODEL
from bs4 import BeautifulSoup
from newspaper import Article
from app.config import OLLAMA_HOST


async def summarize_url(url, progress_cb=None):
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
                total=300, sock_read=180
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
