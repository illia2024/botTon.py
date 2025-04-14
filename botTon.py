import logging
import json
import os
from telegram import Update, ChatPermissions
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext, CommandHandler
import time
import psutil
from datetime import timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ALLOWED_USERS_FILE = "allowed_users.json"
allowed_users = set()

# Антиспам
last_message_time = {}

# Час запуску бота
start_time = time.time()

def load_allowed_users():
    if os.path.exists(ALLOWED_USERS_FILE):
        with open(ALLOWED_USERS_FILE, "r") as f:
            ids = json.load(f)
            return set(ids)
    return set()

def save_allowed_users():
    with open(ALLOWED_USERS_FILE, "w") as f:
        json.dump(list(allowed_users), f)

allowed_users = load_allowed_users()

def group_connect(update: Update, context: CallbackContext) -> None:
    if update.message.new_chat_members:
        update.message.reply_text("🔌The group is connected")

def kick_command(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id not in allowed_users:
        return

    target = None

    if update.message.reply_to_message:
        target = update.message.reply_to_message.from_user.id
    elif context.args:
        if context.args[0].isdigit():
            target = int(context.args[0])
        elif context.args[0].startswith("@"):
            try:
                user = context.bot.get_chat_member(update.effective_chat.id, context.args[0])
                target = user.user.id
            except:
                pass

    if target:
        try:
            context.bot.kick_chat_member(update.effective_chat.id, target)
            context.bot.unban_chat_member(update.effective_chat.id, target)
            update.message.reply_text("✅ Користувача видалено.")
        except Exception as e:
            update.message.reply_text("❌ Не вдалося видалити користувача.")
    else:
        update.message.reply_text("⚠️ Вкажіть користувача для видалення.")

def add_allowed_users(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id != 1428115542:  # Заміни на свій Telegram ID
        return

    if not context.args:
        update.message.reply_text("Вкажи ID користувача(ів), розділені комами.")
        return

    ids = context.args[0].split(",")
    added = []
    for uid in ids:
        if uid.strip().isdigit():
            uid_int = int(uid.strip())
            allowed_users.add(uid_int)
            added.append(uid_int)
    save_allowed_users()
    update.message.reply_text(f"✅ Додано до дозволених: {', '.join(map(str, added))}")

def anti_spam(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    chat_id = update.effective_chat.id
    now = time.time()

    key = (chat_id, user_id)
    last = last_message_time.get(key, 0)

    if now - last < 2:
        try:
            context.bot.delete_message(chat_id=chat_id, message_id=update.message.message_id)
        except:
            pass
    else:
        last_message_time[key] = now

def admin_report(update: Update, context: CallbackContext) -> None:
    if update.message.from_user.id != 1428115542:  # Заміни на свій ID
        update.message.reply_text("У вас немає доступу до цього звіту.")
        return

    uptime_seconds = int(time.time() - start_time)
    uptime = str(timedelta(seconds=uptime_seconds))
    memory = psutil.Process().memory_info().rss / 1024 / 1024

    report = (
        f"🛠 <b>Звіт бота</b>:\n"
        f"⏱ Аптайм: <code>{uptime}</code>\n"
        f"👥 Дозволених користувачів (!кік): <code>{len(allowed_users)}</code>\n"
        f"🧠 Пам’ять: <code>{memory:.2f} MB</code>\n"
    )

    update.message.reply_text(report, parse_mode="HTML")

def main():
    updater = Updater("8190523982:AAE4xFlQo0tYuFV0bWW1qNOvpKrmfLjH-qM", use_context=True)
    dp = updater.dispatcher

    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, group_connect))
    dp.add_handler(MessageHandler(Filters.text & Filters.regex(r'^!кік'), kick_command))
    dp.add_handler(CommandHandler("u_ser_asd", add_allowed_users))
    dp.add_handler(CommandHandler("admin_report", admin_report))
    dp.add_handler(MessageHandler(Filters.text & Filters.group, anti_spam))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
