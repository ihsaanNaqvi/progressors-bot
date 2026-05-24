"""Inline keyboards — i18n-aware."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.services.i18n import t, LANGUAGES


def profile_confirm_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("confirm_btn", lang), callback_data="profile:confirm"),
        InlineKeyboardButton(text=t("edit_btn", lang), callback_data="profile:edit"),
    ]])


def route_overview_kb(total_steps: int, completed: list[int] | None = None, lang: str = "ru") -> InlineKeyboardMarkup:
    completed = completed or []
    rows = []
    step_word = "Step" if lang == "en" else "Шаг"
    step_buttons = [
        InlineKeyboardButton(
            text=f"{'✅ ' if i in completed else ''}{step_word} {i}",
            callback_data=f"step:{i}"
        ) for i in range(1, total_steps + 1)
    ]
    for i in range(0, len(step_buttons), 3):
        rows.append(step_buttons[i:i + 3])

    rows.append([
        InlineKeyboardButton(text=t("btn_stats", lang), callback_data="menu:stats"),
        InlineKeyboardButton(text=t("btn_achievements", lang), callback_data="menu:achievements"),
    ])
    rows.append([
        InlineKeyboardButton(text=t("btn_export", lang), callback_data="menu:export"),
        InlineKeyboardButton(text=t("btn_profile", lang), callback_data="menu:profile"),
    ])
    rows.append([
        InlineKeyboardButton(text="🌐 Language", callback_data="menu:language"),
        InlineKeyboardButton(text=t("btn_restart", lang), callback_data="menu:restart"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def step_detail_kb(step_number: int, total_steps: int, is_completed: bool = False, lang: str = "ru") -> InlineKeyboardMarkup:
    rows = []
    if lang == "en":
        done_t, useful_t, not_t = "✅ Done!", "👍 Useful", "👎 Not useful"
        hard_t, easy_t = "😰 Too hard", "😴 Too easy"
        vid_t, art_t, prac_t = "🎥 More videos", "📄 More articles", "💻 More practice"
        prev_t, route_t, next_t = "⬅️ Prev", "📋 Route", "Next ➡️"
    else:
        done_t, useful_t, not_t = "✅ Выполнено!", "👍 Полезно", "👎 Не подходит"
        hard_t, easy_t = "😰 Слишком сложно", "😴 Слишком легко"
        vid_t, art_t, prac_t = "🎥 Больше видео", "📄 Больше статей", "💻 Больше практики"
        prev_t, route_t, next_t = "⬅️ Пред.", "📋 Маршрут", "След. ➡️"

    r1 = []
    if not is_completed:
        r1.append(InlineKeyboardButton(text=done_t, callback_data=f"fb:done:{step_number}"))
    r1.append(InlineKeyboardButton(text=useful_t, callback_data=f"fb:useful:{step_number}"))
    r1.append(InlineKeyboardButton(text=not_t, callback_data=f"fb:not_useful:{step_number}"))
    rows.append(r1)

    rows.append([
        InlineKeyboardButton(text=hard_t, callback_data=f"fb:too_hard:{step_number}"),
        InlineKeyboardButton(text=easy_t, callback_data=f"fb:too_easy:{step_number}"),
    ])
    rows.append([
        InlineKeyboardButton(text=vid_t, callback_data=f"fb:more_videos:{step_number}"),
        InlineKeyboardButton(text=art_t, callback_data=f"fb:more_articles:{step_number}"),
        InlineKeyboardButton(text=prac_t, callback_data=f"fb:more_practice:{step_number}"),
    ])

    nav = []
    if step_number > 1:
        nav.append(InlineKeyboardButton(text=prev_t, callback_data=f"step:{step_number - 1}"))
    nav.append(InlineKeyboardButton(text=route_t, callback_data="menu:route"))
    if step_number < total_steps:
        nav.append(InlineKeyboardButton(text=next_t, callback_data=f"step:{step_number + 1}"))
    rows.append(nav)

    return InlineKeyboardMarkup(inline_keyboard=rows)


def main_menu_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t("btn_route", lang), callback_data="menu:route")],
        [InlineKeyboardButton(text=t("btn_stats", lang), callback_data="menu:stats"),
         InlineKeyboardButton(text=t("btn_achievements", lang), callback_data="menu:achievements")],
        [InlineKeyboardButton(text=t("btn_export", lang), callback_data="menu:export"),
         InlineKeyboardButton(text=t("btn_profile", lang), callback_data="menu:profile")],
        [InlineKeyboardButton(text="🌐 Language", callback_data="menu:language"),
         InlineKeyboardButton(text=t("btn_restart", lang), callback_data="menu:restart")],
    ])


def restart_confirm_kb(lang: str = "ru") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t("restart_yes", lang), callback_data="menu:confirm_restart"),
        InlineKeyboardButton(text=t("restart_no", lang), callback_data="menu:route"),
    ]])


def language_picker_kb() -> InlineKeyboardMarkup:
    """2-column language picker for 15 languages."""
    items = list(LANGUAGES.items())
    rows = []
    for i in range(0, len(items), 2):
        row = [InlineKeyboardButton(text=label, callback_data=f"lang:{code}")
               for code, label in items[i:i+2]]
        rows.append(row)
    return InlineKeyboardMarkup(inline_keyboard=rows)
