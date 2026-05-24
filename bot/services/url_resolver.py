"""
Topic-aware URL resolver.
If a URL is broken OR uses a platform inappropriate for the topic,
replace it with a topic-appropriate search URL.
"""
import asyncio
import logging
from urllib.parse import urlparse, quote_plus

from bot.services.url_checker import check_url, is_blocked

logger = logging.getLogger(__name__)

# Per-platform search URLs (always return 200)
SEARCH_TEMPLATES = {
    "stepik.org":          "https://stepik.org/catalog?q={q}",
    "youtube.com":         "https://www.youtube.com/results?search_query={q}",
    "youtu.be":            "https://www.youtube.com/results?search_query={q}",
    "habr.com":            "https://habr.com/ru/search/?q={q}&target_type=posts",
    "practicum.yandex.ru": "https://practicum.yandex.ru/catalog/",
    "openedu.ru":          "https://openedu.ru/course/",
    "lektorium.tv":        "https://www.lektorium.tv/lectures",
    "htmlacademy.ru":      "https://htmlacademy.ru/courses",
    "ru.hexlet.io":        "https://ru.hexlet.io/courses",
    "hexlet.io":           "https://ru.hexlet.io/courses",
    "postnauka.ru":        "https://postnauka.ru/search?q={q}",
    "rus.codebasics.io":   "https://rus.codebasics.io/",
    "rutube.ru":           "https://rutube.ru/search/?query={q}",
    "vk.com":              "https://vk.com/video?q={q}",
}

# Default fallback platform for each topic category
TOPIC_FALLBACK = {
    "languages":   "https://www.youtube.com/results?search_query={q}",
    "cooking":     "https://www.youtube.com/results?search_query={q}",
    "hobbies":     "https://www.youtube.com/results?search_query={q}",
    "music":       "https://www.youtube.com/results?search_query={q}",
    "art":         "https://www.youtube.com/results?search_query={q}",
    "sports":      "https://www.youtube.com/results?search_query={q}",
    "programming": "https://stepik.org/catalog?q={q}",
    "design":      "https://www.youtube.com/results?search_query={q}",
    "business":    "https://www.youtube.com/results?search_query={q}",
    "science":     "https://postnauka.ru/search?q={q}",
    "humanities":  "https://postnauka.ru/search?q={q}",
    "other":       "https://www.youtube.com/results?search_query={q}",
}

# Platforms INAPPROPRIATE for each topic — auto-replace if found
INAPPROPRIATE = {
    "languages":   {"habr.com", "ru.hexlet.io", "hexlet.io", "htmlacademy.ru", "rus.codebasics.io"},
    "cooking":     {"habr.com", "ru.hexlet.io", "hexlet.io", "htmlacademy.ru", "rus.codebasics.io", "openedu.ru"},
    "hobbies":     {"habr.com", "ru.hexlet.io", "hexlet.io", "htmlacademy.ru", "rus.codebasics.io"},
    "music":       {"habr.com", "ru.hexlet.io", "hexlet.io", "htmlacademy.ru", "rus.codebasics.io"},
    "art":         {"habr.com", "ru.hexlet.io", "hexlet.io", "htmlacademy.ru", "rus.codebasics.io"},
    "sports":      {"habr.com", "ru.hexlet.io", "hexlet.io", "htmlacademy.ru", "rus.codebasics.io"},
    "design":      {"habr.com", "ru.hexlet.io", "hexlet.io", "rus.codebasics.io"},
    "business":    {"habr.com", "ru.hexlet.io", "hexlet.io", "htmlacademy.ru", "rus.codebasics.io"},
}


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def _is_inappropriate(url: str, topic_category: str) -> bool:
    domain = _domain(url)
    bad = INAPPROPRIATE.get(topic_category, set())
    return any(d in domain for d in bad)


def _make_topic_search_url(topic_category: str, query: str) -> str:
    """Pick the best fallback platform for this topic category."""
    template = TOPIC_FALLBACK.get(topic_category, TOPIC_FALLBACK["other"])
    return template.format(q=quote_plus(query.strip()))


def _make_same_platform_url(url: str, query: str) -> str:
    """Make a search URL on the same platform as `url`."""
    domain = _domain(url)
    encoded = quote_plus(query.strip())
    for plat_domain, template in SEARCH_TEMPLATES.items():
        if plat_domain in domain:
            return template.format(q=encoded)
    return TOPIC_FALLBACK["other"].format(q=encoded)


async def resolve_route_urls(route: dict, topic_category: str = "other") -> dict:
    """
    Validate every URL. Replace broken OR topic-inappropriate URLs with
    topic-appropriate search URLs. Mark all materials with url_verified=True.
    """
    tasks = []
    materials_info = []

    field = route.get("field", "")
    topic_cat = topic_category or route.get("topic_category", "other")

    for step in route.get("steps", []):
        step_title = step.get("title", "")
        for m in step.get("materials", []):
            url = m.get("url", "")
            topic = m.get("title", "") or step_title or field
            materials_info.append((m, topic))
            if not url or not url.lower().startswith("http"):
                tasks.append(asyncio.sleep(0, result=False))
            elif is_blocked(url):
                tasks.append(asyncio.sleep(0, result=False))
            else:
                tasks.append(check_url(url))

    if not tasks:
        return route

    results = await asyncio.gather(*tasks, return_exceptions=True)

    fixed = 0
    inappropriate_fixed = 0
    for (material, topic), ok in zip(materials_info, results):
        ok = ok if isinstance(ok, bool) else False
        old_url = material.get("url", "")

        # Case 1: URL is inappropriate for the topic — redirect to topic platform
        if old_url and _is_inappropriate(old_url, topic_cat):
            new_url = _make_topic_search_url(topic_cat, topic)
            material["url"] = new_url
            material["url_verified"] = True
            material["url_replaced"] = True
            inappropriate_fixed += 1
            logger.info("Inappropriate platform [%s] → topic %s: %s",
                        old_url[:60], topic_cat, new_url[:60])
        # Case 2: URL is broken — replace with same-platform search
        elif not ok:
            new_url = _make_same_platform_url(old_url, topic) if old_url else _make_topic_search_url(topic_cat, topic)
            material["url"] = new_url
            material["url_verified"] = True
            material["url_replaced"] = True
            fixed += 1
            logger.info("Fixed broken URL [%s] → [%s]", old_url[:60], new_url[:60])
        else:
            material["url_verified"] = True

    if fixed or inappropriate_fixed:
        logger.info("Resolved URLs: %d broken-fixed, %d wrong-platform-fixed", fixed, inappropriate_fixed)

    return route
