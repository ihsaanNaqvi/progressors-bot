"""
PROGRESSORS — Commercial web version.

Features:
- Login / Signup
- Real material finder (YouTube, Wikipedia, OpenLibrary, arXiv)
- 16 languages including Urdu
- Free tier (1 route) → Pro (unlimited) [stub for Stripe]
- Modern UI with proper landing

Deploy free on share.streamlit.io. Required secret: OPENAI_API_KEY
"""
import asyncio
import hashlib
import json
import os
from datetime import datetime
from pathlib import Path

import streamlit as st

# ─── Configure secrets ─────────────────────────────────────────────────────
# Supports both standard OpenAI and custom endpoints (QCHEM, Ollama, vLLM)
for key in ("OPENAI_API_KEY", "OPENAI_API_BASE", "OPENAI_MODEL",
            "QCHEM_API_KEY", "QCHEM_BASE_URL"):
    if key in st.secrets:
        os.environ[key] = st.secrets[key]

# Normalize: copy QCHEM values to OPENAI vars if needed
if not os.getenv("OPENAI_API_KEY") and os.getenv("QCHEM_API_KEY"):
    os.environ["OPENAI_API_KEY"] = os.environ["QCHEM_API_KEY"]
if not os.getenv("OPENAI_API_BASE") and os.getenv("QCHEM_BASE_URL"):
    os.environ["OPENAI_API_BASE"] = os.environ["QCHEM_BASE_URL"]

if not os.getenv("OPENAI_API_KEY"):
    st.set_page_config(page_title="Progressor", page_icon="🚀")
    st.error("❌ API key not set. Add to Streamlit secrets:")
    st.code('''OPENAI_API_KEY = "your-key-here"
OPENAI_API_BASE = "https://your-endpoint.com/v1"  # if using custom endpoint
OPENAI_MODEL = "Openai/Gpt-oss-120b"  # or "gpt-4o-mini" for standard OpenAI''', language="toml")
    st.stop()

from bot.services.ai_service import chat_for_profile, generate_route, adjust_route
from bot.services.material_finder import enrich_route_with_real_urls
from bot.services.i18n import t, LANGUAGES
from bot.utils.formatters import format_route_export

# ─── Page config ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Progressor · AI Learning Routes",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
:root {
    --primary: #2563EB;
    --accent: #10B981;
    --warning: #F59E0B;
    --bg-light: #F8FAFC;
    --text-dark: #0F172A;
    --border: #E2E8F0;
}
.main .block-container { padding-top: 1.5rem; max-width: 1000px; }
h1 { color: var(--text-dark); font-weight: 700; }
.hero-title {
    background: linear-gradient(135deg, #2563EB 0%, #10B981 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 3rem;
    font-weight: 800;
    margin-bottom: 0.5rem;
}
.material-card {
    background: white;
    border: 1px solid var(--border);
    border-left: 4px solid var(--primary);
    padding: 14px 18px;
    border-radius: 8px;
    margin: 10px 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    transition: all 0.2s;
}
.material-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.08); transform: translateY(-1px); }
.material-card a { color: var(--text-dark); text-decoration: none; font-weight: 600; }
.material-card a:hover { color: var(--primary); }
.badge-ok { color: var(--accent); font-weight: 700; font-size: 0.9em; }
.badge-pro {
    background: linear-gradient(135deg, #F59E0B 0%, #EF4444 100%);
    color: white;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 0.75em;
    font-weight: 700;
    margin-left: 6px;
}
.stButton button { border-radius: 8px; font-weight: 500; }
.stButton button[kind="primary"] {
    background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%);
}
.user-bubble {
    background: var(--primary);
    color: white;
    padding: 10px 14px;
    border-radius: 12px;
    margin: 6px 0;
    display: inline-block;
}
.bot-bubble {
    background: var(--bg-light);
    color: var(--text-dark);
    padding: 10px 14px;
    border-radius: 12px;
    margin: 6px 0;
    display: inline-block;
}
</style>
""", unsafe_allow_html=True)


def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            raise RuntimeError("closed")
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)


# ─── Simple file-based user store ──────────────────────────────────────────
USERS_FILE = Path("data/web_users.json")
USERS_FILE.parent.mkdir(exist_ok=True)


def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def load_users() -> dict:
    if USERS_FILE.exists():
        try:
            return json.loads(USERS_FILE.read_text())
        except Exception:
            return {}
    return {}


def save_users(users: dict):
    USERS_FILE.write_text(json.dumps(users, indent=2))


def register_user(email: str, password: str, name: str) -> tuple[bool, str]:
    users = load_users()
    if email in users:
        return False, "User with this email already exists"
    users[email] = {
        "password": hash_password(password),
        "name": name,
        "created_at": datetime.now().isoformat(),
        "tier": "free",
        "routes_count": 0,
    }
    save_users(users)
    return True, "Account created successfully!"


def login_user(email: str, password: str) -> tuple[bool, dict | str]:
    users = load_users()
    if email not in users:
        return False, "Email not found"
    if users[email]["password"] != hash_password(password):
        return False, "Wrong password"
    return True, users[email]


def update_user_routes_count(email: str):
    users = load_users()
    if email in users:
        users[email]["routes_count"] = users[email].get("routes_count", 0) + 1
        save_users(users)


# ─── Session state ────────────────────────────────────────────────────────
defaults = {
    "lang": "en",
    "messages": [],
    "profile": None,
    "route": None,
    "completed_steps": set(),
    "view": "chat",
    "msg_count": 0,
    "logged_in": False,
    "user_email": None,
    "user_name": None,
    "user_tier": "free",
    "user_routes": 0,
    "show_login": False,
    "show_signup": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

lang = st.session_state.lang
FREE_TIER_LIMIT = 2  # First 2 routes free


# ─── LANDING PAGE (not logged in) ─────────────────────────────────────────
def landing_page():
    col_main, _ = st.columns([3, 1])
    with col_main:
        st.markdown('<div class="hero-title">🚀 Progressor</div>', unsafe_allow_html=True)
        st.markdown("#### AI-powered personalized learning routes — with **real, verified links**")

        st.markdown("---")

        c1, c2, c3 = st.columns(3)
        c1.metric("🌐 Languages", "16")
        c2.metric("✅ Verified Links", "100%")
        c3.metric("🤖 AI", "GPT-4o")

        st.markdown("### What you get")
        st.markdown("""
        - 🎯 **5-7 adaptive AI questions** to understand your goals
        - 📚 **4-6 step learning route** with REAL YouTube videos, Wikipedia articles, Open Library books, Coursera courses
        - ✅ **Every link verified** — no dead URLs
        - 🔄 **Adaptive feedback** — too hard? too easy? AI rebuilds it instantly
        - 🏆 **Achievement system** + progress tracking
        - 📄 **Export your route** as a file
        - 🌐 **16 languages** including Urdu, Hindi, Arabic, Chinese, Japanese
        """)

        st.markdown("### Get started")
        cc1, cc2 = st.columns(2)
        if cc1.button("🚀 Sign Up Free", use_container_width=True, type="primary"):
            st.session_state.show_signup = True
            st.session_state.show_login = False
            st.rerun()
        if cc2.button("🔑 Log In", use_container_width=True):
            st.session_state.show_login = True
            st.session_state.show_signup = False
            st.rerun()

        st.markdown("---")
        st.caption("Free tier: 2 learning routes. Pro tier: unlimited + advanced features.")


def signup_form():
    st.markdown("## 🚀 Create your Progressor account")
    with st.form("signup_form"):
        name = st.text_input("Your name", placeholder="John Doe")
        email = st.text_input("Email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", placeholder="Min 6 characters")
        submitted = st.form_submit_button("Create account", use_container_width=True, type="primary")
        if submitted:
            if not name or not email or len(password) < 6:
                st.error("Please fill all fields (password min 6 chars)")
            else:
                ok, msg = register_user(email, password, name)
                if ok:
                    st.session_state.logged_in = True
                    st.session_state.user_email = email
                    st.session_state.user_name = name
                    st.session_state.user_tier = "free"
                    st.session_state.show_signup = False
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
    if st.button("← Back"):
        st.session_state.show_signup = False
        st.rerun()


def login_form():
    st.markdown("## 🔑 Log in to Progressor")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in", use_container_width=True, type="primary")
        if submitted:
            ok, result = login_user(email, password)
            if ok:
                st.session_state.logged_in = True
                st.session_state.user_email = email
                st.session_state.user_name = result["name"]
                st.session_state.user_tier = result.get("tier", "free")
                st.session_state.user_routes = result.get("routes_count", 0)
                st.session_state.show_login = False
                st.success(f"Welcome back, {result['name']}!")
                st.rerun()
            else:
                st.error(result)
    if st.button("← Back"):
        st.session_state.show_login = False
        st.rerun()


# ─── Show landing / signup / login flow ───────────────────────────────────
if not st.session_state.logged_in:
    if st.session_state.show_signup:
        signup_form()
    elif st.session_state.show_login:
        login_form()
    else:
        landing_page()
    st.stop()


# ─── SIDEBAR (logged in) ───────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"### 👋 Hi, {st.session_state.user_name}")
    tier_badge = "🆓 Free" if st.session_state.user_tier == "free" else "⭐ Pro"
    st.caption(f"{tier_badge}  ·  {st.session_state.user_routes} routes used")

    if st.session_state.user_tier == "free":
        remaining = max(0, FREE_TIER_LIMIT - st.session_state.user_routes)
        if remaining > 0:
            st.info(f"🎁 You have {remaining} free route(s) remaining")
        else:
            st.warning("🔒 Upgrade to Pro for unlimited routes")
            if st.button("⭐ Upgrade to Pro — $4.99/mo", use_container_width=True, type="primary"):
                st.session_state.show_pricing = True

    st.divider()

    lang_options = list(LANGUAGES.keys())
    lang_choice = st.selectbox(
        "🌐 Language",
        options=lang_options,
        format_func=lambda x: LANGUAGES[x],
        index=lang_options.index(st.session_state.lang),
    )
    if lang_choice != st.session_state.lang:
        st.session_state.lang = lang_choice
        st.rerun()

    st.divider()

    if st.session_state.route:
        if st.button("📚 " + t("btn_route", lang), use_container_width=True):
            st.session_state.view = "route"
            st.rerun()
        if st.button("📄 " + t("btn_export", lang), use_container_width=True):
            txt = format_route_export(st.session_state.route, lang if lang in ("ru", "en") else "en")
            st.download_button("💾 Download", data=txt, file_name="route.txt",
                               mime="text/plain", use_container_width=True)

    if st.button("🔄 " + t("btn_restart", lang), use_container_width=True):
        for k in ["messages", "profile", "route"]:
            st.session_state[k] = None if k in ("profile", "route") else []
        st.session_state.completed_steps = set()
        st.session_state.view = "chat"
        st.session_state.msg_count = 0
        st.rerun()

    st.divider()
    if st.button("🚪 Log out", use_container_width=True):
        for k in defaults:
            st.session_state[k] = defaults[k] if not isinstance(defaults[k], set) else set()
        st.rerun()

    st.caption("**Telegram bot:** [@progressors_AI_Testbot](https://t.me/progressors_AI_Testbot)")


# ─── ADJUST helper ────────────────────────────────────────────────────────
def adjust_step(feedback_type: str, step_number: int):
    with st.spinner("🔄 Adjusting route..."):
        try:
            new_route = run_async(adjust_route(
                st.session_state.profile,
                st.session_state.route,
                feedback_type, step_number, lang,
            ))
            new_route = run_async(enrich_route_with_real_urls(new_route, lang))
            st.session_state.route = new_route
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")


# ─── MAIN AREA ────────────────────────────────────────────────────────────
if st.session_state.view == "chat" or not st.session_state.route:

    if not st.session_state.messages:
        st.markdown("## 🚀 What do you want to learn?")
        st.caption(t("welcome", lang).replace("*", "").replace("\n", " "))

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Confirm profile -> generate
    if st.session_state.profile and not st.session_state.route:
        # Check free tier limit
        if (st.session_state.user_tier == "free"
                and st.session_state.user_routes >= FREE_TIER_LIMIT):
            st.warning("🔒 You've used all free routes. Upgrade to Pro for unlimited routes!")
            if st.button("⭐ Upgrade to Pro", type="primary"):
                st.info("💳 Stripe checkout coming soon. Contact us: support@progressors.ai")
            st.stop()

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ " + t("confirm_btn", lang), use_container_width=True, type="primary"):
                with st.spinner("🔄 Building route + finding real URLs (~30 sec)..."):
                    try:
                        route = run_async(generate_route(st.session_state.profile, lang))
                        route = run_async(enrich_route_with_real_urls(route, lang))
                        st.session_state.route = route
                        st.session_state.view = "route"
                        st.session_state.user_routes += 1
                        update_user_routes_count(st.session_state.user_email)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
        with col2:
            if st.button("✏️ " + t("edit_btn", lang), use_container_width=True):
                st.session_state.profile = None
                st.rerun()

    if not st.session_state.profile:
        placeholder = "What do you want to learn?" if lang == "en" else "Что хочешь изучить?"
        if user_input := st.chat_input(placeholder):
            st.session_state.messages.append({"role": "user", "content": user_input})
            st.session_state.msg_count += 1
            with st.spinner("🤔 Thinking..."):
                try:
                    history_for_ai = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state.messages[:-1]
                    ]
                    force = st.session_state.msg_count >= 8
                    display_text, profile = run_async(
                        chat_for_profile(user_input, history_for_ai, force_profile=force, lang=lang)
                    )
                    st.session_state.messages.append({"role": "assistant", "content": display_text})
                    if profile:
                        st.session_state.profile = profile
                    st.rerun()
                except Exception as e:
                    st.error(f"AI error: {e}")

elif st.session_state.view == "route":
    route = st.session_state.route
    completed = st.session_state.completed_steps
    total = route.get("total_steps", 0)
    pct = int(len(completed) / total * 100) if total else 0

    st.markdown(f"## 🗺️ {route.get('field', 'Your learning route')}")

    c1, c2, c3 = st.columns(3)
    c1.metric("🎯 Goal", route.get("career_goal", "—"))
    c2.metric("⏱️ Duration", route.get("estimated_total_duration", "—"))
    c3.metric("📊 Progress", f"{pct}%", f"{len(completed)}/{total}")

    st.progress(pct / 100 if pct else 0.01)

    if route.get("profile_summary"):
        st.info(f"_{route['profile_summary']}_")

    st.markdown("---")

    for step in route.get("steps", []):
        n = step["step_number"]
        is_done = n in completed
        emoji = "✅" if is_done else f"⏳"

        with st.expander(
            f"{emoji} **Step {n}: {step['title']}**  ·  ⏱️ {step.get('duration', '—')}",
            expanded=False,
        ):
            st.markdown(step.get("description", ""))
            st.markdown(f"**💡 Why this matters:**  \n{step.get('why_important', '—')}")

            mats = step.get("materials", [])
            if mats:
                st.markdown("**📚 Materials:**")
                for m in mats:
                    icon = {"course": "🎓", "video": "🎥", "article": "📄",
                            "book": "📕", "practice": "💻", "academic": "🎓"}.get(m.get("type", ""), "📌")
                    verified = "✅" if m.get("url_verified") else ""
                    platform = m.get("platform", "")
                    duration = m.get("duration", "")
                    meta = " · ".join([p for p in [platform, duration] if p])

                    st.markdown(
                        f'<div class="material-card">'
                        f'{icon} <a href="{m.get("url", "#")}" target="_blank">{m.get("title", "—")}</a> '
                        f'<span class="badge-ok">{verified}</span>'
                        f'<div style="color:#64748B;font-size:0.85em;margin-top:4px;">📍 {meta}</div>'
                        f'<div style="margin-top:6px;color:#64748B;font-size:0.9em;">{m.get("description", "")}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

            skills = step.get("skills", [])
            if skills:
                st.markdown(f"**🔧 Skills:** {', '.join(skills)}")
            career = step.get("career_opportunities", [])
            if career:
                st.markdown(f"**💼 Career:** {', '.join(career)}")
            task = step.get("practical_task", "")
            if task:
                st.markdown(f"**✏️ Practice:** {task}")

            st.markdown("---")
            cols = st.columns(5)
            with cols[0]:
                if not is_done:
                    if st.button("✅ Done", key=f"done_{n}", use_container_width=True, type="primary"):
                        st.session_state.completed_steps.add(n)
                        st.rerun()
                else:
                    st.success("✅")
            with cols[1]:
                if st.button("😰 Hard", key=f"hard_{n}", use_container_width=True):
                    adjust_step("too_hard", n)
            with cols[2]:
                if st.button("😴 Easy", key=f"easy_{n}", use_container_width=True):
                    adjust_step("too_easy", n)
            with cols[3]:
                if st.button("🎥 Video", key=f"vid_{n}", use_container_width=True):
                    adjust_step("more_videos", n)
            with cols[4]:
                if st.button("💻 Practice", key=f"prac_{n}", use_container_width=True):
                    adjust_step("more_practice", n)
