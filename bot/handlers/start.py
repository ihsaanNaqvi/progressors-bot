"""All command handlers — bilingual."""
import json
import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from bot.services.database import (
    clear_conversation, create_user, get_completed_steps,
    get_language, get_user, get_user_stats, reset_user, set_language,
)
from bot.services.i18n import t
from bot.states import ProfileStates
from bot.utils.achievements import format_achievements
from bot.utils.formatters import format_route_export, format_profile
from bot.utils.keyboards import language_picker_kb, main_menu_kb, restart_confirm_kb

logger = logging.getLogger(__name__)
router = Router()


# ── /start ─────────────────────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name or str(user_id)
    await create_user(user_id, username)
    await state.clear()

    lang = await get_language(user_id)
    user = await get_user(user_id)

    if user and user.get("route"):
        route = json.loads(user["route"])
        completed = await get_completed_steps(user_id)
        total = route.get("total_steps", 0)
        pct = int(len(completed) / total * 100) if total else 0

        await message.answer(
            t("welcome_back", lang,
              field=route.get("field", "—"),
              goal=route.get("career_goal", "—"),
              pct=pct, done=len(completed), total=total),
            reply_markup=main_menu_kb(lang),
            parse_mode="Markdown",
        )
        return

    await message.answer(t("welcome", lang), parse_mode="Markdown")
    await state.set_state(ProfileStates.collecting)


# ── /language ──────────────────────────────────────────────────────────────

@router.message(Command("language"))
async def cmd_language(message: Message):
    lang = await get_language(message.from_user.id)
    await message.answer(t("language_picker", lang), reply_markup=language_picker_kb())


@router.callback_query(F.data.startswith("lang:"))
async def cb_lang_select(callback: CallbackQuery):
    user_id = callback.from_user.id
    new_lang = callback.data.split(":")[1]
    if new_lang not in ("ru", "en"):
        await callback.answer()
        return
    await create_user(user_id, callback.from_user.username or "")
    await set_language(user_id, new_lang)
    await callback.message.edit_text(t("language_set", new_lang))
    await callback.answer()


@router.callback_query(F.data == "menu:language")
async def cb_menu_language(callback: CallbackQuery):
    lang = await get_language(callback.from_user.id)
    await callback.message.answer(t("language_picker", lang), reply_markup=language_picker_kb())
    await callback.answer()


# ── /menu, /progress, /stats, /achievements, /export, /reflect, /help, /restart ──

@router.message(Command("menu"))
async def cmd_menu(message: Message):
    lang = await get_language(message.from_user.id)
    await message.answer(t("menu_title", lang), reply_markup=main_menu_kb(lang))


@router.message(Command("progress"))
async def cmd_progress(message: Message):
    await _show_progress(message.from_user.id, message.answer)


async def _show_progress(user_id: int, reply_fn):
    lang = await get_language(user_id)
    user = await get_user(user_id)
    if not user or not user.get("route"):
        await reply_fn(t("no_route", lang))
        return

    route = json.loads(user["route"])
    completed = await get_completed_steps(user_id)
    total = route.get("total_steps", 0)
    done = len(completed)
    pct = int(done / total * 100) if total else 0
    filled = int(pct / 10)
    bar = "🟩" * filled + "⬜" * (10 - filled)

    if lang == "en":
        step_word, done_word = "Step", "Completed:"
        of_word = "of"
    else:
        step_word, done_word = "Шаг", "Выполнено:"
        of_word = "из"

    steps_text = ""
    for step in route.get("steps", []):
        n = step["step_number"]
        mark = "✅" if n in completed else "⏳"
        steps_text += f"{mark} *{step_word} {n}:* {step['title']}\n"

    await reply_fn(
        f"{t('progress_title', lang)}\n\n"
        f"📚 {route.get('field', '—')}\n"
        f"🎯 {route.get('career_goal', '—')}\n\n"
        f"{bar} *{pct}%*\n"
        f"{done_word} *{done}* {of_word} *{total}*\n\n"
        f"{steps_text}",
        reply_markup=main_menu_kb(lang),
        parse_mode="Markdown",
    )


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    await _show_stats(message.from_user.id, message.answer)


async def _show_stats(user_id: int, reply_fn):
    lang = await get_language(user_id)
    stats = await get_user_stats(user_id)
    joined = stats.get("joined", "")
    joined_short = joined[:10] if joined else "—"
    text = t("stats_title", lang,
             lifetime=stats["lifetime_completed"],
             current=stats["current_completed"],
             routes=stats["routes_count"],
             feedback=stats["feedback_given"],
             joined=joined_short)
    await reply_fn(text, reply_markup=main_menu_kb(lang), parse_mode="Markdown")


@router.message(Command("achievements"))
async def cmd_achievements(message: Message):
    await _show_achievements(message.from_user.id, message.answer)


async def _show_achievements(user_id: int, reply_fn):
    lang = await get_language(user_id)
    stats = await get_user_stats(user_id)
    text = format_achievements(stats, lang)
    await reply_fn(text, reply_markup=main_menu_kb(lang), parse_mode="Markdown")


@router.message(Command("export"))
async def cmd_export(message: Message):
    await _do_export(message.from_user.id, message)


async def _do_export(user_id: int, message):
    lang = await get_language(user_id)
    user = await get_user(user_id)
    if not user or not user.get("route"):
        await message.answer(t("no_route", lang))
        return
    route = json.loads(user["route"])
    text = format_route_export(route, lang)
    file = BufferedInputFile(
        text.encode("utf-8"),
        filename=f"progressors_route_{datetime.now().strftime('%Y%m%d')}.txt"
    )
    await message.answer_document(file, caption=t("export_caption", lang), parse_mode="Markdown")


@router.message(Command("reflect"))
async def cmd_reflect(message: Message):
    user_id = message.from_user.id
    lang = await get_language(user_id)
    completed = await get_completed_steps(user_id)
    if not completed:
        await message.answer(t("no_reflect", lang))
        return
    await message.answer(t("reflect", lang), parse_mode="Markdown", reply_markup=main_menu_kb(lang))


@router.message(Command("help"))
async def cmd_help(message: Message):
    lang = await get_language(message.from_user.id)
    await message.answer(t("help", lang), parse_mode="Markdown")


@router.message(Command("restart"))
async def cmd_restart(message: Message):
    lang = await get_language(message.from_user.id)
    await message.answer(
        t("restart_confirm", lang),
        reply_markup=restart_confirm_kb(lang),
        parse_mode="Markdown",
    )


# ── Menu callbacks ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "menu:restart")
async def cb_restart_prompt(callback: CallbackQuery):
    lang = await get_language(callback.from_user.id)
    await callback.message.edit_text(
        t("restart_confirm", lang), reply_markup=restart_confirm_kb(lang), parse_mode="Markdown",
    )


@router.callback_query(F.data == "menu:confirm_restart")
async def cb_confirm_restart(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await get_language(user_id)
    await clear_conversation(user_id)
    await reset_user(user_id)
    await state.clear()
    await callback.message.edit_text(t("restart_done", lang))
    await callback.message.answer(t("welcome", lang), parse_mode="Markdown")
    await state.set_state(ProfileStates.collecting)


@router.callback_query(F.data == "menu:stats")
async def cb_stats(callback: CallbackQuery):
    await _show_stats(callback.from_user.id, callback.message.answer)
    await callback.answer()


@router.callback_query(F.data == "menu:achievements")
async def cb_achievements(callback: CallbackQuery):
    await _show_achievements(callback.from_user.id, callback.message.answer)
    await callback.answer()


@router.callback_query(F.data == "menu:export")
async def cb_export(callback: CallbackQuery):
    await _do_export(callback.from_user.id, callback.message)
    await callback.answer("📄")


@router.callback_query(F.data == "menu:profile")
async def cb_profile(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = await get_language(user_id)
    user = await get_user(user_id)
    if not user or not user.get("profile"):
        await callback.answer("?", show_alert=True)
        return
    profile = json.loads(user["profile"])
    await callback.message.answer(
        format_profile(profile, lang), reply_markup=main_menu_kb(lang), parse_mode="Markdown"
    )
    await callback.answer()
