"""Achievement system — bilingual."""

ACHIEVEMENTS = [
    {"id": "first_step",   "icon": "🥉",
     "name_ru": "Первый шаг",   "desc_ru": "Выполнил первый шаг маршрута",
     "name_en": "First Step",   "desc_en": "Completed your first step",
     "check": lambda s: s["current_completed"] >= 1},
    {"id": "on_the_way",   "icon": "🥈",
     "name_ru": "На пути",      "desc_ru": "Выполнил 3 шага маршрута",
     "name_en": "On The Way",   "desc_en": "Completed 3 steps",
     "check": lambda s: s["current_completed"] >= 3},
    {"id": "maestro",      "icon": "🥇",
     "name_ru": "Маэстро",      "desc_ru": "Завершил весь маршрут!",
     "name_en": "Maestro",      "desc_en": "Completed the whole route!",
     "check": lambda s: s["current_completed"] >= 5},
    {"id": "active",       "icon": "📝",
     "name_ru": "Активный",     "desc_ru": "Оставил 5 отзывов",
     "name_en": "Active",       "desc_en": "Left 5 feedback messages",
     "check": lambda s: s["feedback_given"] >= 5},
    {"id": "explorer",     "icon": "🧭",
     "name_ru": "Исследователь","desc_ru": "Создал 2 разных маршрута",
     "name_en": "Explorer",     "desc_en": "Created 2 different routes",
     "check": lambda s: s["routes_count"] >= 2},
    {"id": "scholar",      "icon": "🎓",
     "name_ru": "Эрудит",       "desc_ru": "Выполнил 10 шагов за всё время",
     "name_en": "Scholar",      "desc_en": "Completed 10 steps lifetime",
     "check": lambda s: s["lifetime_completed"] >= 10},
]


def get_name(a: dict, lang: str = "ru") -> str:
    return a.get(f"name_{lang}", a.get("name_ru", ""))


def get_desc(a: dict, lang: str = "ru") -> str:
    return a.get(f"desc_{lang}", a.get("desc_ru", ""))


def get_unlocked(stats: dict) -> list[dict]:
    return [a for a in ACHIEVEMENTS if a["check"](stats)]


def get_locked(stats: dict) -> list[dict]:
    return [a for a in ACHIEVEMENTS if not a["check"](stats)]


def format_achievements(stats: dict, lang: str = "ru") -> str:
    unlocked = get_unlocked(stats)
    locked = get_locked(stats)

    if lang == "en":
        title = "🏆 *Your achievements*\n\n"
        none = "_No achievements yet._\n"
        unl, lck = "*Unlocked:*\n", "\n*To unlock:*\n"
    else:
        title = "🏆 *Твои достижения*\n\n"
        none = "_Пока нет достижений._\n"
        unl, lck = "*Получено:*\n", "\n*До открытия:*\n"

    text = title
    if unlocked:
        text += unl
        for a in unlocked:
            text += f"{a['icon']} *{get_name(a, lang)}* — _{get_desc(a, lang)}_\n"
    else:
        text += none

    if locked:
        text += lck
        for a in locked[:3]:
            text += f"🔒 *{get_name(a, lang)}* — _{get_desc(a, lang)}_\n"

    return text
