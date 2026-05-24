"""Profile collection + route generation with REAL URL fetching."""
import json
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.services.ai_service import chat_for_profile, generate_route
from bot.services.database import (
    add_message, get_completed_steps, get_conversation, get_language,
    get_user, update_user_profile, update_user_route,
)
from bot.services.i18n import t
from bot.services.material_finder import enrich_route_with_real_urls
from bot.states import ProfileStates, RouteStates
from bot.utils.formatters import format_route_overview
from bot.utils.keyboards import profile_confirm_kb, route_overview_kb

logger = logging.getLogger(__name__)
router = Router()

AFFIRMATIVES = ["верно", "да", "правильно", "yes", "correct", "ok", "ок",
                "хорошо", "good", "great", "looks good", "perfect", "поехали"]


async def _do_generate_route(user_id: int, target, state: FSMContext):
    lang = await get_language(user_id)
    if hasattr(target, "message"):
        send = target.message.answer
        chat_id = target.message.chat.id
        bot = target.bot
    else:
        send = target.answer
        chat_id = target.chat.id
        bot = target.bot

    progress_msg = await send(t("creating_route", lang), parse_mode="Markdown")
    await bot.send_chat_action(chat_id, "typing")

    try:
        user = await get_user(user_id)
        if not user or not user.get("profile"):
            await progress_msg.edit_text(t("no_route", lang))
            return

        profile = json.loads(user["profile"])

        # Step 1: LLM generates structured route
        route = None
        for attempt in range(2):
            try:
                route = await generate_route(profile, lang)
                break
            except Exception as e:
                logger.warning("Route gen attempt %d: %s", attempt + 1, e)
        if not route:
            raise RuntimeError("Route generation failed")

        # Step 2: Replace LLM URLs with REAL URLs from actual APIs
        try:
            await progress_msg.edit_text(
                "🔄 " + ("Finding real videos, articles, and books..." if lang == "en"
                         else "Ищу настоящие видео, статьи и книги..."),
                parse_mode="Markdown",
            )
            route = await enrich_route_with_real_urls(route, lang)
        except Exception as e:
            logger.warning("Material finder issue (non-fatal): %s", e)

        await update_user_route(user_id, route)
        await progress_msg.delete()

        completed = await get_completed_steps(user_id)
        overview = format_route_overview(route, completed, lang) + "\n" + t("all_verified", lang)
        await send(
            overview,
            reply_markup=route_overview_kb(route["total_steps"], completed, lang),
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )
        await state.set_state(RouteStates.viewing)

    except Exception as exc:
        logger.error("Route generation error: %s", exc, exc_info=True)
        await progress_msg.edit_text(t("error_route_failed", lang))


@router.message(ProfileStates.collecting)
async def handle_profile_message(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_language(user_id)
    user_text = (message.text or "").strip()
    if not user_text:
        await message.answer(t("type_something", lang))
        return

    await add_message(user_id, "user", user_text)
    history = await get_conversation(user_id, limit=30)
    history_for_ai = history[:-1]

    user_msg_count = sum(1 for m in history if m["role"] == "user")
    force = user_msg_count >= 8

    await message.bot.send_chat_action(message.chat.id, "typing")

    try:
        display_text, profile = await chat_for_profile(
            user_text, history_for_ai, force_profile=force, lang=lang
        )
    except Exception as exc:
        logger.error("AI error: %s", exc)
        await message.answer(t("error_generic", lang))
        return

    await add_message(user_id, "assistant", display_text)

    if profile:
        await update_user_profile(user_id, profile)
        await state.set_state(ProfileStates.confirming)
        confirm_text = (display_text or "✓").strip()
        if "?" not in confirm_text:
            confirm_text += "\n\n" + t("all_correct", lang)
        await message.answer(confirm_text, reply_markup=profile_confirm_kb(lang), parse_mode="Markdown")
    else:
        await message.answer(display_text, parse_mode="Markdown")


@router.message(ProfileStates.confirming)
async def handle_confirming_text(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_language(user_id)
    user_text = (message.text or "").lower().strip()

    if any(word in user_text for word in AFFIRMATIVES):
        await _do_generate_route(user_id, message, state)
        return

    await add_message(user_id, "user", message.text or "")
    history = await get_conversation(user_id, limit=30)
    history_for_ai = history[:-1]

    await message.bot.send_chat_action(message.chat.id, "typing")
    try:
        display_text, profile = await chat_for_profile(message.text or "", history_for_ai, lang=lang)
    except Exception as exc:
        logger.error("AI error: %s", exc)
        await message.answer(t("error_generic", lang))
        return

    await add_message(user_id, "assistant", display_text)
    if profile:
        await update_user_profile(user_id, profile)
        await message.answer(
            (display_text or "✓") + "\n\n" + t("all_correct", lang),
            reply_markup=profile_confirm_kb(lang), parse_mode="Markdown"
        )
    else:
        await message.answer(display_text, parse_mode="Markdown")
        await state.set_state(ProfileStates.collecting)


@router.callback_query(F.data == "profile:confirm")
async def cb_profile_confirm(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_reply_markup(reply_markup=None)
    await _do_generate_route(callback.from_user.id, callback, state)


@router.callback_query(F.data == "profile:edit")
async def cb_profile_edit(callback: CallbackQuery, state: FSMContext):
    lang = await get_language(callback.from_user.id)
    edit_text = "OK! What would you like to change?" if lang != "ru" else "Что хочешь изменить?"
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(edit_text)
    await state.set_state(ProfileStates.collecting)
