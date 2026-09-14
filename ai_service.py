import hashlib
import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from database import get_ai_cache, reserve_ai_request, save_ai_cache


CATEGORIES = {
    "education": "Education", "school": "Education", "student": "Education",
    "farm": "Agriculture", "farmer": "Agriculture", "crop": "Agriculture", "irrigation": "Agriculture",
    "hospital": "Healthcare", "health": "Healthcare", "clinic": "Healthcare",
    "water": "Water", "drinking": "Water", "waste": "Environment", "flood": "Environment",
    "solar": "Energy", "electricity": "Energy", "bus": "Urban Development", "road": "Urban Development",
    "disability": "Accessibility", "accessible": "Accessibility", "livelihood": "Rural Livelihoods",
}


def _cache_key(title, description, category, location):
    content = "|".join(value.strip().lower() for value in (title, description, category, location))
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _local_analysis(title, description, category, location):
    words = re.findall(r"[a-zA-Z]{4,}", f"{title} {description}".lower())
    keywords = []
    for word in words:
        if word not in keywords and word not in {"with", "from", "that", "this", "area", "need", "people"}:
            keywords.append(word)
        if len(keywords) == 5:
            break
    inferred_category = category or next((value for word, value in CATEGORIES.items() if word in words), "Public Administration")
    priority = "High" if any(word in f"{title} {description}".lower() for word in ("unsafe", "urgent", "shortage", "emergency", "no access")) else "Medium"
    summary = description.strip()
    if len(summary) > 180:
        summary = summary[:177].rsplit(" ", 1)[0] + "..."
    return {"category": inferred_category, "priority": priority, "summary": summary, "keywords": keywords[:5], "domains": [inferred_category, "Community Innovation"], "source": "local"}


def _extract_json(text):
    cleaned = text.strip().removeprefix("```json").removesuffix("```").strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    return json.loads(cleaned[start:end + 1])


def _gemini_analysis(title, description, category, location):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    limit = int(os.getenv("GEMINI_DAILY_REQUEST_LIMIT", "20"))
    if not reserve_ai_request(limit):
        return None
    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")
    prompt = f"""Analyze this community challenge for JanSaathi. Return JSON only with exactly these keys: category, priority, summary, keywords, domains. priority must be Low, Medium, High, or Critical. keywords and domains must be arrays of short strings. Keep summary under 45 words. This is a recommendation for human review.
Title: {title}
Description: {description[:4000]}
Citizen category: {category}
Location: {location}"""
    payload = json.dumps({"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"}}).encode()
    request = Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}", data=payload, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=12) as response:
            body = json.loads(response.read().decode("utf-8"))
        text = body["candidates"][0]["content"]["parts"][0]["text"]
        result = _extract_json(text)
        result.update(source="gemini")
        return result
    except (HTTPError, URLError, KeyError, IndexError, ValueError, TimeoutError):
        return None


def analyze_challenge(title, description, category, location):
    key = _cache_key(title, description, category, location)
    cached = get_ai_cache(key)
    if cached:
        cached = dict(cached)
        cached["source"] = "cache"
        return cached
    result = _gemini_analysis(title, description, category, location) or _local_analysis(title, description, category, location)
    result["summary"] = str(result.get("summary", description))[:500]
    result["keywords"] = [str(item)[:40] for item in result.get("keywords", [])[:8]]
    result["domains"] = [str(item)[:60] for item in result.get("domains", [])[:5]]
    save_ai_cache(key, result)
    return result