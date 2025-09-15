import json
import requests
from app.config import OLLAMA_MODEL
from bs4 import BeautifulSoup
from newspaper import Article


async def summarize_url(url, progress_cb=None):
    article = Article(url)
    article.download()
    article.parse()

    title = article.title
    content = article.text

    article_text = f"{title}\n\n{content}"

    if progress_cb:
        progress_cb(0.5)  # Halfway done

    # Step 2: Send to Ollama for summarization
    ollama_url = "http://localhost:11435/api/generate"
    prompt = f"Summarize the following article:\n{article_text}"
    payload = {"model": OLLAMA_MODEL, "prompt": prompt}  # Change to your model name
    response = requests.post(
        ollama_url,
        json=payload,
        stream=True,
        timeout=30,
    )
    response_text = ""
    for line in response.iter_lines():
        if line:
            data = json.loads(line.decode("utf-8"))
            response_text += data.get("response", "")

    if progress_cb:
        progress_cb(1.0)  # Done

    return response_text
