"""Configuration — supports both standard OpenAI and custom OpenAI-compatible endpoints."""
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Support both QCHEM and standard OPENAI naming
OPENAI_API_KEY = (
    os.getenv("OPENAI_API_KEY", "")
    or os.getenv("QCHEM_API_KEY", "")
)
OPENAI_API_BASE = (
    os.getenv("OPENAI_API_BASE", "")
    or os.getenv("QCHEM_BASE_URL", "")
)
# Default to GPT-OSS-120B (works with QCHEM) — override via env if using standard OpenAI
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "Openai/Gpt-oss-120b")

DB_PATH = os.getenv("DB_PATH", "data/bot.db")
