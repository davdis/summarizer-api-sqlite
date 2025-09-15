import requests
from app.config import OLLAMA_MODEL

# def summarize_url(url,progress_cb=None):
#     if progress_cb: progress_cb(1.0)
#     return f'Summary of {url} (stubbed).'



def summarize_url(url, progress_cb=None):
    # Step 1: Download article content
    article_response = requests.get(url)
    article_text = article_response.text

    if progress_cb:
        progress_cb(0.5)  # Halfway done

    # Step 2: Send to Ollama for summarization
    ollama_url = "http://localhost:11435/api/generate"
    prompt = f"Summarize the following article:\n{article_text}"
    payload = {
        "model": OLLAMA_MODEL,  # Change to your model name
        "prompt": prompt
    }
    ollama_response = requests.post(ollama_url, json=payload)
    summary = ollama_response.json().get("response", "")
    import pdb; pdb.set_trace()

    if progress_cb:
        progress_cb(1.0)  # Done

    return summary
