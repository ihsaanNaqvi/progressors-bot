"""
Real URL finder — fetches actual specific URLs from real APIs.

Solves the "search query URL instead of final video" problem.
For each material, returns a REAL working URL, not a search page.

Sources used:
- YouTube (via youtube-search-python): real video URLs
- Wikipedia: real article URLs
- OpenLibrary: real book URLs
- arXiv: real academic paper URLs
- Curated catalog: known good direct URLs for popular courses
"""
import asyncio
import logging
from urllib.parse import quote_plus

import aiohttp

logger = logging.getLogger(__name__)

_HEADERS = {"User-Agent": "Mozilla/5.0 (Progressors Learning Bot)"}


# ─── YouTube — real video URLs ────────────────────────────────────────────
def _search_youtube_sync(query: str, lang: str = "en") -> list[dict]:
    """Synchronous YouTube search (runs in thread)."""
    try:
        from youtubesearchpython import VideosSearch
        # Add language hint for better results
        if lang == "ru":
            query = query + " на русском"
        videos = VideosSearch(query, limit=3).result().get("result", [])
        return [{
            "title": v.get("title", ""),
            "url": v.get("link", ""),
            "duration": v.get("duration", ""),
            "channel": v.get("channel", {}).get("name", ""),
            "thumbnail": (v.get("thumbnails") or [{}])[0].get("url", ""),
        } for v in videos if v.get("link")]
    except Exception as e:
        logger.warning("YouTube search failed: %s", e)
        return []


async def find_youtube_video(query: str, lang: str = "en") -> dict | None:
    """Returns top YouTube video for query — REAL URL, not search."""
    loop = asyncio.get_event_loop()
    results = await loop.run_in_executor(None, _search_youtube_sync, query, lang)
    return results[0] if results else None


# ─── Wikipedia — real article URLs ────────────────────────────────────────
async def find_wikipedia_article(query: str, lang: str = "en") -> dict | None:
    """Returns Wikipedia article for query — REAL URL."""
    api_lang = lang if lang in ("en", "ru", "es", "fr", "de", "it", "pt",
                                "zh", "ar", "hi", "tr", "ja", "ko",
                                "ur", "uz", "kk") else "en"
    url = f"https://{api_lang}.wikipedia.org/api/rest_v1/page/summary/{quote_plus(query)}"
    try:
        async with aiohttp.ClientSession(headers=_HEADERS) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    page_url = data.get("content_urls", {}).get("desktop", {}).get("page")
                    if page_url:
                        return {
                            "title": data.get("title", query),
                            "url": page_url,
                            "description": data.get("extract", "")[:200],
                            "platform": "Wikipedia",
                        }
    except Exception as e:
        logger.debug("Wikipedia failed for %s: %s", query, e)

    # Fallback: Wikipedia search
    search_url = f"https://{api_lang}.wikipedia.org/wiki/Special:Search?search={quote_plus(query)}"
    try:
        async with aiohttp.ClientSession(headers=_HEADERS) as session:
            async with session.get(f"https://{api_lang}.wikipedia.org/w/api.php",
                                   params={"action": "opensearch", "search": query, "limit": 1, "format": "json"},
                                   timeout=aiohttp.ClientTimeout(total=5)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if len(data) >= 4 and data[3]:
                        return {
                            "title": data[1][0] if data[1] else query,
                            "url": data[3][0],
                            "description": data[2][0] if data[2] else "",
                            "platform": "Wikipedia",
                        }
    except Exception:
        pass
    return None


# ─── OpenLibrary — real book URLs ────────────────────────────────────────
async def find_openlibrary_book(query: str) -> dict | None:
    """Search Open Library for a book - REAL URL."""
    url = f"https://openlibrary.org/search.json?q={quote_plus(query)}&limit=3"
    try:
        async with aiohttp.ClientSession(headers=_HEADERS) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=6)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    docs = data.get("docs", [])
                    if docs:
                        d = docs[0]
                        key = d.get("key", "")
                        if key:
                            return {
                                "title": d.get("title", query),
                                "url": f"https://openlibrary.org{key}",
                                "description": (d.get("author_name", [""])[0] if d.get("author_name") else "") + " · " + str(d.get("first_publish_year", "")),
                                "platform": "Open Library",
                            }
    except Exception as e:
        logger.debug("OpenLibrary failed: %s", e)
    return None


# ─── arXiv — academic papers ────────────────────────────────────────────
async def find_arxiv_paper(query: str) -> dict | None:
    """Search arXiv for academic papers - REAL URL."""
    url = f"http://export.arxiv.org/api/query?search_query=all:{quote_plus(query)}&max_results=1"
    try:
        async with aiohttp.ClientSession(headers=_HEADERS) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=6)) as resp:
                if resp.status == 200:
                    text = await resp.text()
                    # Parse minimal Atom feed
                    import re
                    title_m = re.search(r"<entry>.*?<title>([^<]+)</title>", text, re.DOTALL)
                    id_m = re.search(r"<entry>.*?<id>([^<]+)</id>", text, re.DOTALL)
                    if title_m and id_m:
                        return {
                            "title": title_m.group(1).strip(),
                            "url": id_m.group(1).strip(),
                            "description": "Academic paper from arXiv",
                            "platform": "arXiv",
                        }
    except Exception as e:
        logger.debug("arXiv failed: %s", e)
    return None


# ─── Curated catalog — known good direct URLs ──────────────────────────────
CURATED_PLATFORMS = {
    "freecodecamp": {
        "url": "https://www.freecodecamp.org/learn/",
        "name": "freeCodeCamp",
        "topics": {"programming", "web", "javascript", "python", "data", "frontend"},
    },
    "khanacademy": {
        "url": "https://www.khanacademy.org/",
        "name": "Khan Academy",
        "topics": {"math", "science", "physics", "chemistry", "biology", "economics", "history"},
    },
    "mdn": {
        "url": "https://developer.mozilla.org/",
        "name": "MDN Web Docs",
        "topics": {"web", "javascript", "html", "css", "frontend"},
    },
    "w3schools": {
        "url": "https://www.w3schools.com/",
        "name": "W3Schools",
        "topics": {"web", "javascript", "html", "css", "sql", "python"},
    },
    "duolingo": {
        "url": "https://www.duolingo.com/",
        "name": "Duolingo",
        "topics": {"languages", "english", "spanish", "french", "german"},
    },
    "coursera": {
        "url": "https://www.coursera.org/search?query=",
        "name": "Coursera",
        "topics": {"any"},
        "search_url": True,
    },
}


def find_curated(topic_text: str, topic_category: str) -> dict | None:
    """Match topic to a known good platform."""
    text = topic_text.lower()
    cat = topic_category.lower() if topic_category else ""

    for key, info in CURATED_PLATFORMS.items():
        if "any" in info["topics"]:
            continue
        if any(t in text or t in cat for t in info["topics"]):
            return {
                "title": f"{info['name']} — {topic_text}",
                "url": info["url"],
                "description": f"Free resources on {info['name']}",
                "platform": info["name"],
            }
    return None


# ─── Main: find best material for a given topic + type ──────────────────────
async def find_material(material_type: str, topic_query: str,
                         topic_category: str = "other", lang: str = "en") -> dict | None:
    """
    For a desired material_type (video/article/book/course/academic),
    return a REAL working URL with metadata.
    """
    material_type = (material_type or "").lower()

    if material_type in ("video", "playlist"):
        return await find_youtube_video(topic_query, lang)

    if material_type == "academic":
        return await find_arxiv_paper(topic_query)

    if material_type == "book":
        book = await find_openlibrary_book(topic_query)
        if book:
            return book
        # Fallback: Wikipedia
        return await find_wikipedia_article(topic_query, lang)

    if material_type in ("article", "documentation"):
        # Try Wikipedia first
        wiki = await find_wikipedia_article(topic_query, lang)
        if wiki:
            return wiki
        # Fallback: curated platform
        return find_curated(topic_query, topic_category)

    if material_type in ("course", "practice"):
        curated = find_curated(topic_query, topic_category)
        if curated:
            return curated
        # Fallback: YouTube tutorial
        return await find_youtube_video(topic_query + " tutorial", lang)

    # Unknown type — try Wikipedia + YouTube as fallback
    wiki = await find_wikipedia_article(topic_query, lang)
    if wiki:
        return wiki
    return await find_youtube_video(topic_query, lang)


# ─── Enrich entire route with real URLs ──────────────────────────────────────
async def enrich_route_with_real_urls(route: dict, lang: str = "en") -> dict:
    """
    Replace search-query URLs in the LLM output with REAL URLs from APIs.
    """
    topic_cat = route.get("topic_category", "other")
    tasks = []
    materials_to_update = []

    for step in route.get("steps", []):
        step_title = step.get("title", "")
        for m in step.get("materials", []):
            mtype = m.get("type", "article")
            # Topic query for search — prefer specific material title
            topic = m.get("title", "") or step_title or route.get("field", "")
            materials_to_update.append((m, topic))
            tasks.append(find_material(mtype, topic, topic_cat, lang))

    if not tasks:
        return route

    results = await asyncio.gather(*tasks, return_exceptions=True)

    enriched_count = 0
    for (material, topic), found in zip(materials_to_update, results):
        if found and isinstance(found, dict) and found.get("url"):
            old_url = material.get("url", "")
            material["url"] = found["url"]
            material["url_verified"] = True
            if found.get("title"):
                material["title"] = found["title"][:120]
            if found.get("description"):
                material["description"] = found["description"][:300]
            if found.get("platform"):
                material["platform"] = found["platform"]
            if found.get("duration") and not material.get("duration"):
                material["duration"] = found["duration"]
            enriched_count += 1
            logger.info("Enriched: %s → %s", old_url[:50], found["url"][:80])
        else:
            # Couldn't find specific URL — keep what LLM generated but mark unverified
            material["url_verified"] = False

    logger.info("Enriched %d/%d materials with real URLs", enriched_count, len(materials_to_update))
    return route
