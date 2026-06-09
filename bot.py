import os
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, CommandHandler, filters, ContextTypes

from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)

MODEL = "qwen/qwen3-4b:free"

# ─── Доступ ───────────────────────────────────────────────────────────────────
ADMIN_ID = 6467846884
allowed_users: set[int] = {ADMIN_ID}

# ─── Промпт ───────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
CRITICAL RULE: You MUST respond in Russian language ONLY. No exceptions. Never use Chinese, English or any other language. ALWAYS Russian.
NO internal thoughts, NO reasoning, NO drafts. Only final answer.

Ты — Юля Посольская, строгий но справедливый репетитор по подготовке к ЕГЭ для учеников 11 класса.

Твои принципы:
1. Общаешься строго и по делу — никакой лишней болтовни
2. Требуешь чёткости в ответах — если ученик отвечает расплывчато, указываешь на это
3. Используешь метод Фейнмана — просишь объяснить тему своими словами
4. Применяешь интервальное повторение — напоминаешь повторить тему через день, три дня, неделю
5. После каждой темы даёшь 2-3 вопроса для самопроверки — без этого не двигаешься дальше
6. Хвалишь редко, но метко — только за реальные успехи
7. Если ученик ленится или отвлекается — делаешь строгое замечание
8. Знаешь все предметы ЕГЭ: математика, русский, физика, химия, биология, история, обществознание, английский, информатика

Стиль общения: строгий, лаконичный, на "ты", минимум эмодзи, максимум пользы. Никакой воды.
"""

# ─── История сообщений ────────────────────────────────────────────────────────
user_histories: dict[int, list] = {}


# ─── Проверка доступа ─────────────────────────────────────────────────────────
def is_allowed(user_id: int) -> bool:
    return user_id in allowed_users


# ─── Команды ──────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(
        "👋 Привет! Я Виктор Андреевич — твой репетитор по ЕГЭ!\n\n"
        "📚 Я помогу тебе:\n"
        "• Разобрать любую тему по всем предметам ЕГЭ\n"
        "• Запомнить формулы и даты через мнемоники\n"
        "• Проверить себя с помощью вопросов\n"
        "• Не сойти с ума во время подготовки 😄\n\n"
        "Просто напиши тему или вопрос — и поехали! 🚀"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    await update.message.reply_text(
        "📖 *Команды бота:*\n\n"
        "/start — начать заново\n"
        "/clear — очистить историю разговора\n"
        "/progress — советы по плану подготовки\n"
        "/tip — случайный лайфхак для учёбы\n"
        "/myid — узнать свой Telegram ID\n\n"
        "*Только для админа:*\n"
        "/add <user_id> — добавить пользователя\n"
        "/remove <user_id> — убрать пользователя\n"
        "/users — список допущенных пользователей",
        parse_mode="Markdown"
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text("🗑 История очищена! Начинаем с чистого листа ✅")


async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🪪 Твой Telegram ID: `{update.effective_user.id}`", parse_mode="Markdown")


async def progress(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    await update.message.reply_text(
        "📊 *План подготовки к ЕГЭ:*\n\n"
        "🗓 *За 3 месяца:*\n"
        "• Повтори все темы по разделам\n"
        "• Решай по 1 варианту в неделю\n\n"
        "🗓 *За месяц:*\n"
        "• Упор на слабые темы\n"
        "• Решай по 3 варианта в неделю\n\n"
        "🗓 *За неделю:*\n"
        "• Только практика, никакой новой теории\n"
        "• Повтори формулы и даты\n\n"
        "💡 Напиши свой предмет — дам конкретный план!",
        parse_mode="Markdown"
    )


async def tip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_allowed(update.effective_user.id):
        return
    tips = [
        "🍅 *Техника Помодоро:* 25 минут учишься — 5 минут отдыхаешь. После 4 циклов — 30 минут отдыха. Мозг скажет спасибо!",
        "🧠 *Метод Фейнмана:* Прочитал тему — закрой книгу и объясни её воображаемому другу простыми словами. Где запнулся — там пробел!",
        "📇 *Карточки:* Пиши термин на одной стороне, объяснение на другой. Повторяй пока не будешь знать все без подсказок.",
        "😴 *Сон важнее зубрёжки:* Мозг закрепляет знания во сне. Лучше поспать 8 часов, чем учить всю ночь!",
        "✍️ *Пиши от руки:* Конспекты от руки запоминаются на 40% лучше, чем печатные. Старая школа работает!",
        "🎯 *Правило 2 минут:* Если задача займёт меньше 2 минут — сделай сразу. Не откладывай мелкие дела!",
        "🔁 *Интервальное повторение:* Повтори тему через 1 день, потом через 3 дня, потом через неделю. Так оседает в долгосрочную память!",
    ]
    import random
    await update.message.reply_text(random.choice(tips), parse_mode="Markdown")


# ─── Управление доступом (только админ) ──────────────────────────────────────
async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Только администратор может добавлять пользователей.")
        return
    if not context.args:
        await update.message.reply_text("Использование: /add <user_id>")
        return
    try:
        new_id = int(context.args[0])
        allowed_users.add(new_id)
        await update.message.reply_text(f"✅ Пользователь {new_id} добавлен!")
    except ValueError:
        await update.message.reply_text("❌ Неверный ID. Используй цифры.")


async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Только администратор может удалять пользователей.")
        return
    if not context.args:
        await update.message.reply_text("Использование: /remove <user_id>")
        return
    try:
        rem_id = int(context.args[0])
        if rem_id == ADMIN_ID:
            await update.message.reply_text("❌ Нельзя удалить администратора!")
            return
        allowed_users.discard(rem_id)
        await update.message.reply_text(f"✅ Пользователь {rem_id} удалён.")
    except ValueError:
        await update.message.reply_text("❌ Неверный ID.")


async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    users_list = "\n".join([f"• {uid} {'(ты)' if uid == ADMIN_ID else ''}" for uid in allowed_users])
    await update.message.reply_text(f"👥 *Допущенные пользователи:*\n{users_list}", parse_mode="Markdown")


# ─── Основной обработчик сообщений ───────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    user_text = update.message.text

    if user_id not in user_histories:
        user_histories[user_id] = []

    user_histories[user_id].append({"role": "user", "content": user_text})

    if len(user_histories[user_id]) > 20:
        user_histories[user_id] = user_histories[user_id][-20:]

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            *user_histories[user_id]
        ],
        max_tokens=1024,
    )

    reply = response.choices[0].message.content
    user_histories[user_id].append({"role": "assistant", "content": reply})

    await update.message.reply_text(reply, parse_mode="Markdown")

# ─── Запуск ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    from telegram import BotCommand

    async def post_init(app):
        await app.bot.set_my_commands([
            BotCommand("start", "🏠 Начать заново"),
            BotCommand("help", "📖 Список команд"),
            BotCommand("tip", "💡 Лайфхак для учёбы"),
            BotCommand("progress", "📊 План подготовки"),
            BotCommand("clear", "🗑 Очистить историю"),
            BotCommand("myid", "🪪 Мой Telegram ID"),
            BotCommand("add", "✅ Добавить пользователя"),
            BotCommand("remove", "❌ Убрать пользователя"),
            BotCommand("users", "👥 Список пользователей"),
        ])

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = (
        ApplicationBuilder()
        .token(os.getenv("BOT_TOKEN"))
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("progress", progress))
    app.add_handler(CommandHandler("tip", tip))
    app.add_handler(CommandHandler("add", add_user))
    app.add_handler(CommandHandler("remove", remove_user))
    app.add_handler(CommandHandler("users", list_users))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Бот запущен... 🚀")
    app.run_polling()