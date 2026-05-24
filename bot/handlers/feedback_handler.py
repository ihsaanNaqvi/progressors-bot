"""Step feedback + AI route adjustment with REAL URL fetching."""
import json
import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from bot.services.ai_service import adjust_route
from bot.services.database import (
    add_step_feedback, get_completed_steps, get_language, get_user,
    get_user_stats, mark_step_complete, update_route_only,
)
from bot.services.i18n import t
from bot.services.material_finder import enrich_route_with_real_urls
from bot.utils.achievements import get_desc, get_name, get_unlocked
from bot.utils.formatters import format_step_detail
from bot.utils.keyboards import step_detail_kb

logger = logging.getLogger(__name__)
router = Router()

ADJUSTABLE = {"too_hard", "too_easy", "not_useful",
              "more_videos", "more_articles", "more_practice"}


async def _check_new_achievements(user_id: int, prev_unlocked: list, send_fn, lang: str) -> None:
    stats = await get_user_stats(user_id)
    now_unlocked = get_unlocked(stats)
    prev_ids = {a["id"] for a in prev_unlocked}
    new_ones = [a for a in now_unlocked if a["id"] not in prev_ids]
    for a in new_ones:
        await send_fn(
            t("new_achievement", lang, icon=a["icon"], name=get_name(a, lang), desc=get_desc(a, lang)),
            parse_mode="Markdown",
        )


@router.callback_query(F.data.startswith("fb:"))
async def handle_feedback(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("?", show_alert=True)
        return

    _, feedback_type, step_str = parts
    try:
        step_number = int(step_str)
    except ValueError:
        await callback.answer("?", show_alert=True)
        return

    user_id = callback.from_user.id
    lang = await get_language(user_id)
    user = await get_user(user_id)
    if not user or not user.get("route"):
        await callback.answer(t("no_route", lang), show_alert=True)
        return

    route = json.loads(user["route"])
    total = route["total_steps"]

    ack_key = f"fb_{feedback_type}"
    await callback.answer(t(ack_key, lang), show_alert=False)

    if feedback_type == "done":
        stats_before = await get_user_stats(user_id)
        prev_unlocked = get_unlocked(stats_before)
        await mark_step_complete(user_id, step_number)
        completed = await get_completed_steps(user_id)

        if step_number >= total:
            await callback.message.edit_text(
                t("all_completed", lang, goal=route.get("career_goal", "—")),
                parse_mode="Markdown",
            )
        else:
            next_step = route["steps"][step_number]
            text = format_step_detail(next_step, step_number + 1, total, lang)
            await callback.message.edit_text(
                t("step_completed", lang, n=step_number) + "\n\n" + text,
                reply_markup=step_detail_kb(step_number + 1, total, False, lang),
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
        await _check_new_achievements(user_id, prev_unlocked, callback.message.answer, lang)
        return

    if feedback_type == "useful":
        await add_step_feedback(user_id, step_number, feedback_type)
        return

    if feedback_type in ADJUSTABLE:
        await add_step_feedback(user_id, step_number, feedback_type)
        adjusting_msg = await callback.message.answer(t("adjusting", lang), parse_mode="Markdown")

        try:
            profile = json.loads(user["profile"])
            new_route = await adjust_route(profile, route, feedback_type, step_number, lang)
            try:
                new_route = await enrich_route_with_real_urls(new_route, lang)
            except Exception as e:
                logger.warning("Material finder issue (non-fatal): %s", e)

            await update_route_only(user_id, new_route)
            await adjusting_msg.delete()

            updated_step = new_route["steps"][step_number - 1]
            completed = await get_completed_steps(user_id)
            text = format_step_detail(updated_step, step_number, new_route["total_steps"], lang)

            await callback.message.answer(
                t("route_updated", lang) + text,
                reply_markup=step_detail_kb(step_number, new_route["total_steps"], step_number in completed, lang),
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
        except Exception as exc:
            logger.error("Route adjustment error: %s", exc, exc_info=True)
            await adjusting_msg.edit_text(t("adjust_failed", lang))
