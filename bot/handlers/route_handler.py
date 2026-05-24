"""Route navigation: /route, overview, step display — bilingual."""
import json
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.services.database import get_completed_steps, get_language, get_user
from bot.services.i18n import t
from bot.states import RouteStates
from bot.utils.formatters import format_route_overview, format_step_detail
from bot.utils.keyboards import route_overview_kb, step_detail_kb

logger = logging.getLogger(__name__)
router = Router()


async def _send_route_overview(user_id: int, target, state: FSMContext):
    lang = await get_language(user_id)
    user = await get_user(user_id)
    if not user or not user.get("route"):
        text = t("no_route", lang)
        if isinstance(target, Message):
            await target.answer(text)
        else:
            await target.answer(text, show_alert=True)
        return

    route = json.loads(user["route"])
    completed = await get_completed_steps(user_id)
    overview = format_route_overview(route, completed, lang)
    kb = route_overview_kb(route["total_steps"], completed, lang)

    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(overview, reply_markup=kb, parse_mode="Markdown", disable_web_page_preview=True)
        except Exception:
            await target.message.answer(overview, reply_markup=kb, parse_mode="Markdown", disable_web_page_preview=True)
    else:
        await target.answer(overview, reply_markup=kb, parse_mode="Markdown", disable_web_page_preview=True)

    await state.set_state(RouteStates.viewing)


@router.message(Command("route"))
async def cmd_route(message: Message, state: FSMContext):
    await _send_route_overview(message.from_user.id, message, state)


@router.callback_query(F.data == "menu:route")
async def cb_show_route(callback: CallbackQuery, state: FSMContext):
    await _send_route_overview(callback.from_user.id, callback, state)
    await callback.answer()


@router.callback_query(F.data.startswith("step:"))
async def cb_show_step(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    lang = await get_language(user_id)
    try:
        step_number = int(callback.data.split(":")[1])
    except (IndexError, ValueError):
        await callback.answer("?", show_alert=True)
        return

    user = await get_user(user_id)
    if not user or not user.get("route"):
        await callback.answer(t("no_route", lang), show_alert=True)
        return

    route = json.loads(user["route"])
    steps = route.get("steps", [])
    total = route["total_steps"]

    if step_number < 1 or step_number > len(steps):
        await callback.answer("?", show_alert=True)
        return

    step = steps[step_number - 1]
    completed = await get_completed_steps(user_id)
    is_done = step_number in completed

    text = format_step_detail(step, step_number, total, lang)
    if is_done:
        completed_label = "✅ *This step is already completed!*\n\n" if lang == "en" else "✅ *Этот шаг уже выполнен!*\n\n"
        text = completed_label + text

    kb = step_detail_kb(step_number, total, is_done, lang)

    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown", disable_web_page_preview=True)
    except Exception as e:
        logger.warning("Edit failed: %s", e)
        await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown", disable_web_page_preview=True)

    await callback.answer()
    await state.set_state(RouteStates.viewing_step)
