# 🚀 Progressor — Commercial AI Learning Platform

AI-powered personalized learning route assistant with **real verified URLs**, **16 languages**, **user authentication**, and **freemium model**.

**Live Demo:**
- 🌐 Web app: [Streamlit Cloud](https://aiedi-bot-q5lqublprujyypqqvmbgox.streamlit.app/)
- 🤖 Telegram: [@progressors_AI_Testbot](https://t.me/progressors_AI_Testbot)

---

## 🎯 Commercial Features

| Feature | Free | Pro ($4.99/mo) |
|---------|------|----------------|
| AI route generation | 2 routes | Unlimited |
| Real verified URLs | ✅ | ✅ |
| 16 languages | ✅ | ✅ |
| Achievements | ✅ | ✅ |
| Export route | ✅ | ✅ |
| Advanced AI (GPT-4o) | — | ✅ |
| PDF export | — | ✅ |
| Custom themes | — | ✅ |
| Priority support | — | ✅ |

---

## 🔥 What's New (Commercial Edition)

### 1. Real URLs Instead of Search Queries 🎯
The previous version generated URLs like `youtube.com/results?search_query=...` (search pages).
**Now** the bot uses real APIs to fetch:
- 🎥 **YouTube videos** — actual specific video URLs (via `youtube-search-python`)
- 📄 **Wikipedia articles** — real article pages (Wikipedia REST API)
- 📕 **Open Library books** — actual book URLs (OpenLibrary API)
- 🎓 **arXiv papers** — real academic papers
- 💻 **Curated platforms** — Coursera, freeCodeCamp, Khan Academy, MDN, W3Schools

### 2. International (Not Just Russia) 🌍
Removed Russia-only restrictions. Now uses **global open educational sources**:
- YouTube (all channels worldwide)
- Wikipedia (all languages)
- Coursera, edX, Khan Academy, freeCodeCamp
- Open Library, Project Gutenberg
- arXiv, MDN, W3Schools

### 3. OpenAI (GPT-4o-mini) ⚡
Switched from Groq to OpenAI for better structured outputs and reliability.

### 4. 16 Languages 🌐
RU, EN, ES, FR, DE, IT, PT, ZH, AR, HI, TR, JA, KO, UZ, KK, **+ UR (Urdu)**

### 5. User Authentication 🔐
Sign up / Log in with email + password. User accounts track:
- Routes created
- Tier (Free / Pro)
- Achievements
- Progress across sessions

### 6. Modern UI 🎨
Hero section, gradient buttons, hover effects, proper landing page.

---

## 🚀 Quick Start

### Telegram Bot (local)
```bash
git clone <repo>
cd progressors-bot
pip install -r requirements.txt
cp .env.example .env
# Set BOT_TOKEN and OPENAI_API_KEY
python main.py
```

### Web Version (local)
```bash
export OPENAI_API_KEY=sk-...
streamlit run web_app.py
```

### Deploy Web on Streamlit Cloud (free)
1. Push to GitHub
2. Go to share.streamlit.io
3. Main file: `progressors-bot/web_app.py`
4. Add secret: `OPENAI_API_KEY = "sk-..."`
5. Deploy

---

## 💰 Monetization

Current setup includes:
- ✅ Free tier (2 routes)
- ✅ Pro tier hook (upgrade button)
- ⏳ **Add Stripe integration** for real payments:
  - Get a Stripe account
  - Create a product "Progressor Pro" at $4.99/mo
  - Add Stripe checkout link to the upgrade button
  - Use Stripe webhooks to update user tier

### Future Monetization Ideas
- 💸 **Affiliate links** — Coursera/Udemy referral fees
- 🎯 **B2B** — sell to schools/universities
- 📚 **Course partnerships** — featured placements
- 🏢 **Enterprise plans** — for HR / L&D teams

---

## 🏗️ Architecture

```
progressors-bot/
├── main.py                       # Telegram entry point
├── web_app.py                    # Commercial Streamlit web app
├── config.py                     # env: OPENAI_API_KEY, BOT_TOKEN
├── bot/
│   ├── handlers/                 # Telegram handlers
│   ├── services/
│   │   ├── ai_service.py         # ⭐ OpenAI GPT-4o-mini (replaces Groq)
│   │   ├── material_finder.py    # ⭐ Real URL fetching (YouTube, Wiki, Books, arXiv)
│   │   ├── url_resolver.py       # Topic-aware fallback
│   │   ├── i18n.py               # 16 languages
│   │   └── database.py           # SQLite
│   └── utils/
└── data/
    └── web_users.json            # User accounts (file-based)
```

---

## 🌐 Real URL Sources

| Material Type | Source | Always Returns Real URL? |
|---------------|--------|--------------------------|
| Video | YouTube (search → top video) | ✅ Yes |
| Article | Wikipedia REST API | ✅ Yes |
| Book | Open Library API | ✅ Yes |
| Academic paper | arXiv API | ✅ Yes |
| Course | Curated catalog (Coursera, Khan Academy, freeCodeCamp, MDN) | ✅ Yes |
| Practice | Curated platforms | ✅ Yes |

---

## 👥 Team

**Ihsaan** · True Tech Arena 2026 — System Hack: Tomsk
Top position · 11 ЮНОВУС track · "Programming without limits"
