"""Message formatters — i18n-aware."""

MATERIAL_EMOJI = {
    "course": "🎓", "video": "🎥", "article": "📄",
    "book": "📕", "playlist": "📺", "practice": "💻",
}


def format_route_overview(route: dict, completed: list[int] | None = None, lang: str = "ru") -> str:
    completed = completed or []
    steps = route.get("steps", [])
    total = route.get("total_steps", len(steps))
    progress = int(len(completed) / total * 100) if total else 0

    filled = int(progress / 10)
    bar = "🟩" * filled + "⬜" * (10 - filled)

    if lang == "en":
        lines = [
            f"🗺️ *Your personal learning route*\n",
            f"🎯 Goal: {route.get('career_goal', '—')}",
            f"📚 Field: {route.get('field', '—')}",
            f"⏱️ Time: {route.get('estimated_total_duration', '—')}",
            f"\n📊 Progress: {bar} {progress}%",
            f"_{route.get('profile_summary', '')}_\n",
            "━━━━━━━━━━━━━━━━━━━",
            "*Route steps:*\n",
        ]
    else:
        lines = [
            f"🗺️ *Твой персональный маршрут*\n",
            f"🎯 Цель: {route.get('career_goal', '—')}",
            f"📚 Область: {route.get('field', '—')}",
            f"⏱️ Время: {route.get('estimated_total_duration', '—')}",
            f"\n📊 Прогресс: {bar} {progress}%",
            f"_{route.get('profile_summary', '')}_\n",
            "━━━━━━━━━━━━━━━━━━━",
            "*Шаги маршрута:*\n",
        ]

    step_word = "Step" if lang == "en" else "Шаг"
    for step in steps:
        n = step["step_number"]
        done = "✅ " if n in completed else ""
        skills = ", ".join(step.get("skills", [])[:2])
        lines.append(
            f"{done}*{n}.* {step['title']}\n"
            f"   ⏱️ {step.get('duration', '—')}  •  🔧 {skills}\n"
        )

    if lang == "en":
        lines.append("👇 Tap a step for details and materials")
    else:
        lines.append("👇 Нажми на шаг для подробностей и материалов")
    return "\n".join(lines)


def format_step_detail(step: dict, step_number: int, total_steps: int, lang: str = "ru") -> str:
    if lang == "en":
        header = f"📖 *Step {step_number} of {total_steps}: {step['title']}*"
        dur_lbl = "⏱️ Duration:"
        why_lbl = "💡 *Why this matters:*"
        mat_lbl = "📚 *Materials:*"
        skill_lbl = "🔧 *Skills gained:*"
        career_lbl = "💼 *Career opportunities:*"
        task_lbl = "✏️ *Practice task:*"
        legend = "_✅ verified link · ⚠️ may be unavailable_"
    else:
        header = f"📖 *Шаг {step_number} из {total_steps}: {step['title']}*"
        dur_lbl = "⏱️ Продолжительность:"
        why_lbl = "💡 *Почему важно:*"
        mat_lbl = "📚 *Материалы:*"
        skill_lbl = "🔧 *Навыки после шага:*"
        career_lbl = "💼 *Открывает возможности:*"
        task_lbl = "✏️ *Практическое задание:*"
        legend = "_✅ ссылка проверена · ⚠️ может быть недоступна_"

    lines = [
        header + "\n",
        f"{step.get('description', '')}\n",
        f"{dur_lbl} *{step.get('duration', '—')}*\n",
        f"{why_lbl}\n{step.get('why_important', '—')}\n",
    ]

    materials = step.get("materials", [])
    if materials:
        lines.append(mat_lbl)
        for m in materials:
            emoji = MATERIAL_EMOJI.get(m.get("type", ""), "📌")
            title = m.get("title", "—")
            url = m.get("url", "")
            platform = m.get("platform", "")
            duration = m.get("duration", "")
            description = m.get("description", "")
            verified = m.get("url_verified")

            badge = " ✅" if verified else (" ⚠️" if verified is False and url else "")
            line = f"\n{emoji} [{title}]({url}){badge}"
            meta = [p for p in [platform, duration] if p]
            if meta:
                line += f"\n   📍 {' · '.join(meta)}"
            if description:
                line += f"\n   _{description}_"
            lines.append(line)

        if any(m.get("url_verified") is not None for m in materials):
            lines.append("\n" + legend)

    skills = step.get("skills", [])
    if skills:
        lines.append("\n" + skill_lbl)
        for s in skills:
            lines.append(f"   • {s}")

    career = step.get("career_opportunities", [])
    if career:
        lines.append("\n" + career_lbl)
        for c in career:
            lines.append(f"   • {c}")

    task = step.get("practical_task", "")
    if task:
        lines.append(f"\n{task_lbl}\n{task}")

    return "\n".join(lines)


def format_profile(profile: dict, lang: str = "ru") -> str:
    if lang == "en":
        return "\n".join([
            "👤 *Your profile*\n",
            f"🎯 Goal: {profile.get('goal', '—')}",
            f"📚 Field: {profile.get('field', '—')}",
            f"📊 Level: {profile.get('level', '—')}",
            f"🎓 Experience: {profile.get('experience', '—')}",
            f"⏱️ Time/week: {profile.get('time_per_week', '—')}",
            f"📋 Format: {profile.get('format_preference', '—')}",
            f"💪 Motivation: {profile.get('motivation', '—')}",
        ])
    levels = {"beginner": "Новичок", "basic": "Начальный", "intermediate": "Средний", "advanced": "Продвинутый"}
    level = levels.get(profile.get("level", ""), profile.get("level", "—"))
    return "\n".join([
        "👤 *Твой профиль*\n",
        f"🎯 Цель: {profile.get('goal', '—')}",
        f"📚 Область: {profile.get('field', '—')}",
        f"📊 Уровень: {level}",
        f"🎓 Опыт: {profile.get('experience', '—')}",
        f"⏱️ Время в неделю: {profile.get('time_per_week', '—')}",
        f"📋 Формат: {profile.get('format_preference', '—')}",
        f"💪 Мотивация: {profile.get('motivation', '—')}",
    ])


def format_route_export(route: dict, lang: str = "ru") -> str:
    if lang == "en":
        lines = [
            "═══════════════════════════════════",
            "  PROGRESSOR — Your Learning Route",
            "═══════════════════════════════════\n",
            f"Field: {route.get('field', '—')}",
            f"Goal: {route.get('career_goal', '—')}",
            f"Time: {route.get('estimated_total_duration', '—')}",
            f"\n{route.get('profile_summary', '')}\n",
            "─" * 40,
        ]
        step_w, dur_w, why_w, mat_w, sk_w, op_w, pr_w = "STEP", "Duration:", "WHY THIS MATTERS:", "MATERIALS:", "SKILLS:", "OPENS:", "PRACTICE:"
    else:
        lines = [
            "═══════════════════════════════════",
            "  ПРОГРЕССОР — Твой маршрут обучения",
            "═══════════════════════════════════\n",
            f"Область: {route.get('field', '—')}",
            f"Цель: {route.get('career_goal', '—')}",
            f"Время: {route.get('estimated_total_duration', '—')}",
            f"\n{route.get('profile_summary', '')}\n",
            "─" * 40,
        ]
        step_w, dur_w, why_w, mat_w, sk_w, op_w, pr_w = "ШАГ", "Продолжительность:", "ПОЧЕМУ ЭТО ВАЖНО:", "МАТЕРИАЛЫ:", "НАВЫКИ:", "ОТКРЫВАЕТ:", "ПРАКТИКА:"

    for step in route.get("steps", []):
        n = step["step_number"]
        lines.append(f"\n[{step_w} {n}] {step['title']}")
        lines.append(f"  {dur_w} {step.get('duration', '—')}")
        lines.append(f"  {step.get('description', '')}")
        lines.append(f"\n  {why_w}")
        lines.append(f"  {step.get('why_important', '—')}")

        materials = step.get("materials", [])
        if materials:
            lines.append(f"\n  {mat_w}")
            for m in materials:
                lines.append(f"   • {m.get('title', '—')}")
                lines.append(f"     {m.get('url', '')}")
                lines.append(f"     [{m.get('platform', '—')} · {m.get('duration', '—')}]")

        skills = step.get("skills", [])
        if skills:
            lines.append(f"\n  {sk_w} {', '.join(skills)}")

        career = step.get("career_opportunities", [])
        if career:
            lines.append(f"  {op_w} {', '.join(career)}")

        task = step.get("practical_task", "")
        if task:
            lines.append(f"\n  {pr_w} {task}")

        lines.append("\n" + "─" * 40)

    lines.append("\nGenerated by @progressors_AI_Testbot" if lang == "en" else "\nСоздано ботом @progressors_AI_Testbot")
    lines.append("True Tech Arena — System Hack Tomsk 2026")
    return "\n".join(lines)
