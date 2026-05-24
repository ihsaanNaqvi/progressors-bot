"""
OpenAI integration (replaces Groq).
Uses GPT-4o-mini for cost efficiency.
Now international (not Russia-only) and uses real material finder afterwards.
"""
import re
import json
import logging
import asyncio
from openai import AsyncOpenAI
from config import OPENAI_API_KEY, OPENAI_API_BASE, OPENAI_MODEL

logger = logging.getLogger(__name__)

# Support custom OpenAI-compatible endpoints (QCHEM, Ollama, vLLM, etc.)
def _make_client():
    if not OPENAI_API_KEY:
        return None
    kwargs = {"api_key": OPENAI_API_KEY}
    if OPENAI_API_BASE:
        kwargs["base_url"] = OPENAI_API_BASE
    return AsyncOpenAI(**kwargs)

client = _make_client()


LANG_NAMES = {
    "en": "English", "ru": "Russian / русский", "es": "Spanish / español",
    "fr": "French / français", "de": "German / Deutsch", "it": "Italian / italiano",
    "pt": "Portuguese / português", "zh": "Chinese / 中文", "ar": "Arabic / العربية",
    "hi": "Hindi / हिन्दी", "tr": "Turkish / Türkçe", "ja": "Japanese / 日本語",
    "ko": "Korean / 한국어", "uz": "Uzbek / o'zbek", "kk": "Kazakh / қазақша",
    "ur": "Urdu / اردو",
}


def _profile_system(lang: str) -> str:
    lang_name = LANG_NAMES.get(lang, "English")
    return f"""You are a friendly educational assistant — the Progressor bot.
Through a natural conversation, collect information to build a personalized learning route.

Collect through 5-7 adaptive questions:
1. Goal — what and why they want to learn
2. Level — beginner / basic / intermediate / advanced
3. Experience and background
4. Hours per week available
5. Format preference — video / articles / courses / books / practice
6. Field — the broad area (programming, design, languages, cooking, business, science, etc.)

RULES:
- Ask ONE question at a time
- Warm, friendly, encouraging tone
- After 5-7 exchanges, you MUST output the JSON profile in tags:
<profile>{{"goal":"...","level":"beginner","experience":"...","time_per_week":"...","format_preference":"...","field":"...","motivation":"...","topic_category":"languages|programming|design|business|cooking|science|humanities|music|art|sports|math|finance|health|other"}}</profile>
- After the tags — short summary paragraph + "Is everything correct?" (in target language)
- NEVER show JSON to the user in plain text
- Respond ONLY in {lang_name}. All your output must be in {lang_name}."""


def _route_system(lang: str) -> str:
    lang_name = LANG_NAMES.get(lang, "English")
    return f"""You create personalized educational learning routes for international users worldwide.

GUIDELINES FOR MATERIAL SELECTION:
- Mix high-quality FREE sources from anywhere in the world
- For VIDEOS: prefer YouTube (most accessible globally) — channels like freeCodeCamp, Khan Academy, Crash Course, TED-Ed
- For ARTICLES: Wikipedia, official documentation (MDN, Python docs), Medium, freeCodeCamp News
- For BOOKS: Open Library, Project Gutenberg, free open textbooks
- For COURSES: Coursera (audit), edX (audit), freeCodeCamp, Khan Academy, Codecademy free, Scrimba
- For PRACTICE: LeetCode, HackerRank, Codewars, Codecademy free tier
- For ACADEMIC: arXiv papers, Google Scholar

⚠️ URL POLICY:
DO NOT make up specific course/article IDs. Use these patterns:
- YouTube SEARCH (will be replaced with real video by app): https://www.youtube.com/results?search_query=TOPIC
- Wikipedia: https://en.wikipedia.org/wiki/TOPIC_WITH_UNDERSCORES
- Official docs (real URLs OK): https://developer.mozilla.org/, https://docs.python.org/3/
- Coursera: https://www.coursera.org/search?query=TOPIC
- Khan Academy: https://www.khanacademy.org/
- freeCodeCamp: https://www.freecodecamp.org/learn/
The application will automatically fetch REAL working URLs based on the title and type — focus on QUALITY of titles, not URLs.

ROUTE REQUIREMENTS:
- 4-6 steps, simple → advanced, with natural progression
- 2-3 materials per step
- Mix of formats (video + reading + practice)
- Each step: title, description, why important, duration, materials, skills gained, career roles unlocked, practical task

OUTPUT: ONLY clean JSON (no markdown, no code blocks):
{{
  "profile_summary": "...",
  "field": "...",
  "career_goal": "...",
  "topic_category": "...",
  "total_steps": 5,
  "estimated_total_duration": "...",
  "steps": [
    {{
      "step_number": 1,
      "title": "...",
      "description": "...",
      "duration": "...",
      "why_important": "...",
      "materials": [
        {{
          "type": "video|article|book|course|practice|academic",
          "title": "Specific topic title for finding real URL",
          "url": "https://...",
          "platform": "YouTube|Wikipedia|Coursera|...",
          "description": "...",
          "duration": "..."
        }}
      ],
      "skills": ["..."],
      "career_opportunities": ["..."],
      "practical_task": "..."
    }}
  ]
}}

All TEXT FIELDS must be in {lang_name}.
Make material titles SPECIFIC and SEARCHABLE — they will be used to find real videos/articles."""


def _adjust_system(lang: str) -> str:
    return f"""Adjust the learning route based on user feedback.
Same rules as before — international free resources, structured JSON output.
Output only the FULL updated JSON. Text in {LANG_NAMES.get(lang, 'English')}."""


def _strip_json_from_text(text: str) -> str:
    text = re.sub(r'\{["\']goal["\'].*?\}', '', text, flags=re.DOTALL)
    text = re.sub(r'```(?:json)?\s*\{.*?\}\s*```', '', text, flags=re.DOTALL)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def _parse_json(raw: str) -> dict:
    clean = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    clean = re.sub(r"\s*```$", "", clean, flags=re.MULTILINE)
    clean = clean.strip()
    start = clean.find("{")
    end = clean.rfind("}")
    if start != -1 and end != -1:
        clean = clean[start:end + 1]
    return json.loads(clean)


async def _ask(system: str, messages: list[dict], max_tokens: int = 2048,
                retries: int = 2, json_mode: bool = False) -> str:
    if not client:
        raise RuntimeError("OPENAI_API_KEY is not set")
    last_err = None
    for attempt in range(retries + 1):
        try:
            kwargs = {
                "model": OPENAI_MODEL,
                "messages": [{"role": "system", "content": system}] + messages,
                "max_tokens": max_tokens,
                "temperature": 0.7,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            resp = await client.chat.completions.create(**kwargs)
            return resp.choices[0].message.content
        except Exception as e:
            last_err = e
            logger.warning("OpenAI call failed (attempt %d): %s", attempt + 1, e)
            if attempt < retries:
                await asyncio.sleep(1.5 * (attempt + 1))
    raise last_err


async def chat_for_profile(user_message, history, force_profile=False, lang="en"):
    msg = user_message
    if force_profile:
        msg += f"\n\n[SYSTEM: You have enough information. Output the JSON profile in <profile>...</profile> tags immediately, all text in {LANG_NAMES.get(lang, 'English')}.]"
    messages = history + [{"role": "user", "content": msg}]
    full_text = await _ask(_profile_system(lang), messages, max_tokens=600)

    profile = None
    match = re.search(r"<profile>(.*?)</profile>", full_text, re.DOTALL)
    if match:
        try:
            profile = json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            logger.warning("Failed to parse profile JSON")
        full_text = full_text.replace(match.group(0), "").strip()

    return _strip_json_from_text(full_text), profile


async def generate_route(profile, lang="en"):
    topic_cat = profile.get("topic_category", "other")
    lang_name = LANG_NAMES.get(lang, "English")
    prompt = (
        f"Create a personalized learning route in {lang_name}:\n"
        f"• Goal: {profile.get('goal', '—')}\n"
        f"• Field: {profile.get('field', '—')}\n"
        f"• Topic category: {topic_cat}\n"
        f"• Level: {profile.get('level', 'beginner')}\n"
        f"• Experience: {profile.get('experience', '—')}\n"
        f"• Time/week: {profile.get('time_per_week', '—')}\n"
        f"• Format: {profile.get('format_preference', 'any')}\n"
        f"• Motivation: {profile.get('motivation', '—')}\n\n"
        f"Make material TITLES specific and searchable — the app will use them to find real URLs."
    )
    raw = await _ask(_route_system(lang), [{"role": "user", "content": prompt}],
                     max_tokens=3500, json_mode=True)
    route = _parse_json(raw)
    route["topic_category"] = topic_cat
    return route


async def adjust_route(profile, route, feedback_type, step, lang="en"):
    labels = {
        "too_hard": "too hard — find easier materials",
        "too_easy": "too easy — replace with more advanced",
        "not_useful": "not useful — try different format or platform",
        "more_videos": "user wants more video materials",
        "more_articles": "user wants more articles",
        "more_practice": "user wants more practice and exercises",
    }
    prompt = (
        f"Profile: {json.dumps(profile, ensure_ascii=False)}\n"
        f"Route: {json.dumps(route, ensure_ascii=False)}\n"
        f"Step {step}: {labels.get(feedback_type, 'improve')}\n"
        f"Return full updated JSON with high-quality, specific material titles."
    )
    raw = await _ask(_adjust_system(lang), [{"role": "user", "content": prompt}],
                     max_tokens=3500, json_mode=True)
    new_route = _parse_json(raw)
    new_route["topic_category"] = route.get("topic_category", "other")
    return new_route
