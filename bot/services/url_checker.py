"""
URL validation service.
Checks if educational material URLs are alive and not blocked in Russia.
"""
import asyncio
import logging
from urllib.parse import urlparse

import aiohttp

logger = logging.getLogger(__name__)

# Domains that work reliably in Russia (whitelist)
RUSSIA_SAFE_DOMAINS = {
    "stepik.org", "youtube.com", "youtu.be",
    "practicum.yandex.ru", "yandex.ru",
    "openedu.ru", "lektorium.tv",
    "htmlacademy.ru", "ru.hexlet.io", "hexlet.io",
    "postnauka.ru", "habr.com", "proglib.io", "tproger.ru",
    "rutube.ru", "vk.com", "vk.video", "rus.codebasics.io",
    "github.com", "gitlab.com", "replit.com",
    "skillbox.ru", "geekbrains.ru", "netology.ru",
}

# Known blocked or unreliable in Russia (blacklist)
RUSSIA_BLOCKED_DOMAINS = {
    "coursera.org", "udemy.com", "edx.org",
    "linkedin.com", "pluralsight.com", "skillshare.com",
    "codecademy.com", "duolingo.com",  # Duolingo left Russia
}

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return ""


def is_blocked(url: str) -> bool:
    d = _domain(url)
    return any(b in d for b in RUSSIA_BLOCKED_DOMAINS)


def is_whitelisted(url: str) -> bool:
    d = _domain(url)
    return any(s in d for s in RUSSIA_SAFE_DOMAINS)


async def check_url(url: str, timeout: float = 5.0) -> bool:
    """Return True if URL is reachable and not blocked."""
    if not url or not url.lower().startswith("http"):
        return False
    if is_blocked(url):
        return False

    try:
        async with aiohttp.ClientSession(headers=_HEADERS) as session:
            async with session.head(
                url,
                timeout=aiohttp.ClientTimeout(total=timeout),
                allow_redirects=True,
            ) as resp:
                if resp.status < 400:
                    return True
                # Some sites block HEAD; fall back to GET
                if resp.status in (403, 405):
                    async with session.get(
                        url, timeout=aiohttp.ClientTimeout(total=timeout),
                        allow_redirects=True,
                    ) as gresp:
                        return gresp.status < 400
                return False
    except Exception as e:
        logger.debug("URL check failed for %s: %s", url, e)
        return False


async def validate_route(route: dict) -> dict:
    """
    Annotate every material in the route with `url_verified: bool`.
    Doesn't remove materials, just marks them so UI can show a badge.
    """
    tasks = []
    materials = []

    for step in route.get("steps", []):
        for m in step.get("materials", []):
            url = m.get("url", "")
            materials.append(m)
            if not url:
                tasks.append(asyncio.sleep(0, result=False))
            else:
                tasks.append(check_url(url))

    if not tasks:
        return route

    results = await asyncio.gather(*tasks, return_exceptions=True)

    for material, result in zip(materials, results):
        ok = result if isinstance(result, bool) else False
        material["url_verified"] = ok

    return route
