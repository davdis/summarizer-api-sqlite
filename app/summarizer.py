import json
import aiohttp
import asyncio
import requests
from app.config import OLLAMA_MODEL
from bs4 import BeautifulSoup
from newspaper import Article
from app.config import OLLAMA_HOST

async def summarize_url(url, progress_cb=None):
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
        prompt = f"Summarize the following article:\n{article_text}"
        payload = {"model": OLLAMA_MODEL, "prompt": prompt}

        async with session.post(
                ollama_url,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
        ) as response:
            response_text = ""
            async for line in response.content:
                if line:
                    try:
                        data = json.loads(line.decode("utf-8"))
                        response_text += data.get("response", "")
                    except json.JSONDecodeError:
                        continue

    if progress_cb:
        progress_cb(1.0)

    return response_text
