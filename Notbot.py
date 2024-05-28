from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, MessageHandler, Filters
import sqlite3
from datetime import datetime, timedelta
import psutil

TOKEN = '7028486555:AAHVY4yW4_NhWw10kxhol6tRR3l6pt1P15E'
ADMIN_ID = '1428115542'
DB_NAME = 'bot_database.db'


def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    add_user_to_db(user_id, username)
    
    keyboard = [
        [KeyboardButton("Гаманець"), KeyboardButton("Інформація")],
        [KeyboardButton("Зібрати")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    update.message.reply_text(
        'Привіт! Я ваш бот. Ви можете переглянути свій баланс, заробляти TON, або дізнатися більше про мене за допомогою команд у меню.',
        reply_markup=reply_markup
    )

def wallet(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    user_info = get_user_info(user_id)
    if user_info:
        username, balance = user_info
        keyboard = [
            [InlineKeyboardButton("📥 Вивести", callback_data='withdraw')],
            [InlineKeyboardButton("🔶 Зібрати", callback_data='collect')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            f"👛 Гаманець\n\n🐳 Юзернейм: @{username}\n🔶 TON: {balance:.4f}",
            reply_markup=reply_markup
        )
    else:
        update.message.reply_text("Користувач не знайдений. Спробуйте команду /start.")

def collect_ton(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id if update.message else update.callback_query.from_user.id
    last_collected = get_last_collected_time(user_id)
    now = datetime.now()
    if last_collected is None or now - last_collected >= timedelta(hours=1):
        update_balance(user_id, 0.0001)
        update_last_collected_time(user_id, now)
        context.bot.send_message(chat_id=user_id, text="Ви зібрали 0.0001 TON.")
    else:
        context.bot.send_message(chat_id=user_id, text="Ви можете зібрати TON лише раз на годину.")

def withdraw(update: Update, context: CallbackContext) -> None:
    context.bot.send_message(chat_id=update.callback_query.from_user.id, text="""
    Привіт 😉
    --> Для того щоб вивести вам потрібно ввести свій /username 
    --> Потім ввести свій адрес Xrocket/Tonkeeper 
    --> І протягом від 2-10 годин вивід поступить на ваш гаманець.
    """)

def information(update: Update, context: CallbackContext) -> None:
    user_count = get_user_count()
    bot_start_date = get_bot_start_date()
    days_active = (datetime.now() - bot_start_date).days
    keyboard = [[InlineKeyboardButton("Новини", url='https://t.me/nFarmTon')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        f"🤖 Бот працює: {days_active} днів\n🔎 Користувачів: {user_count}",
        reply_markup=reply_markup
    )

def button(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    query.answer()
    if query.data == 'withdraw':
        withdraw(update, context)
    elif query.data == 'collect':
        collect_ton(update, context)
    elif query.data.startswith('block_'):
        block_user(update, context)
    elif query.data == 'broadcast':
        context.user_data['awaiting_broadcast'] = True
        context.bot.send_message(chat_id=query.from_user.id, text="Будь ласка, введіть повідомлення для розсилки.")
    elif query.data == 'transactions':
        view_transactions(update, context)
    elif query.data == 'ton_reward':
        context.user_data['awaiting_ton_reward'] = True
        context.bot.send_message(chat_id=query.from_user.id, text="Будь ласка, введіть нову суму нагороди за натискання на кнопку.")
    elif query.data == 'find_user':
        find_user(update, context)

def handle_message(update: Update, context: CallbackContext) -> None:
    if context.user_data.get('awaiting_broadcast'):
        broadcast_message(update, context)
    elif context.user_data.get('awaiting_ton_reward'):
        handle_ton_reward(update, context)
    elif context.user_data.get('awaiting_user_id'):
        handle_user_search(update, context)
    else:
        text = update.message.text
        if text == "Гаманець":
            wallet(update, context)
        elif text == "Інформація":
            information(update, context)
        elif text == "Зібрати":
            collect_ton(update, context)
        else:
            update.message.reply_text("Виберіть команду з меню.")

def admin_panel(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if str(user_id) == ADMIN_ID:
        uptime = datetime.now() - get_bot_start_date()
        memory_usage = psutil.Process().memory_info().rss / 1024 ** 2  # MB
        keyboard = [
            [InlineKeyboardButton("💌 Розсилка", callback_data='broadcast')],
            [InlineKeyboardButton("♻️ Транзакції", callback_data='transactions')],
            [InlineKeyboardButton("🖇️ За TON", callback_data='ton_reward')],
            [InlineKeyboardButton("🔍 Знайти користувача", callback_data='find_user')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(chat_id=user_id, text=(
            f"💻 Панель адміністратора\n"
            f"__________________\n"
            f"⏳ Аптайм бота: {uptime}\n"
            f"💾 Використано пам'яті: {memory_usage:.2f} MB\n"
        ), reply_markup=reply_markup)
    else:
        context.bot.send_message(chat_id=user_id, text="Ви не маєте доступу до цієї команди.")

def broadcast_message(update: Update, context: CallbackContext) -> None:
    message = update.message.text
    user_ids = get_all_user_ids()
    for user_id in user_ids:
        context.bot.send_message(chat_id=user_id, text=message)
    update.message.reply_text("Повідомлення надіслано всім користувачам.")
    context.user_data['awaiting_broadcast'] = False

def handle_ton_reward(update: Update, context: CallbackContext) -> None:
    if context.user_data.get('awaiting_ton_reward'):
        try:
            new_reward = float(update.message.text)
            context.user_data['ton_reward'] = new_reward
            update.message.reply_text(f"Нова плата за натискання на кнопку встановлена: {new_reward} TON.")
        except ValueError:
            update.message.reply_text("Будь ласка, введіть дійсне число.")
        context.user_data['awaiting_ton_reward'] = False

def find_user(update: Update, context: CallbackContext) -> None:
    user_id = update.callback_query.from_user.id
    if str(user_id) == ADMIN_ID:
        context.bot.send_message(chat_id=user_id, text="Введіть ID користувача:")
        context.user_data['awaiting_user_id'] = True
    else:
        context.bot.send_message(chat_id=user_id, text="Ви не маєте доступу до цієї команди.")

def handle_user_search(update: Update, context: CallbackContext) -> None:
    if context.user_data.get('awaiting_user_id'):
        try:
            search_user_id = int(update.message.text)
            user_info = get_user_info(search_user_id)
            if user_info:
                username, balance = user_info
                blocked = is_user_blocked(search_user_id)
                block_button_text = "🚫 Заблокувати" if not blocked else "🔓 Розблокувати"
                keyboard = [
                    [InlineKeyboardButton(block_button_text, callback_data=f'block_{search_user_id}')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                update.message.reply_text(
                    f"ID користувача: {search_user_id}\n"
                    f"Юзернейм: {username}\n"
                    f"Баланс: {balance:.4f} TON",
                    reply_markup=reply_markup
                )
            else:
                update.message.reply_text("Користувач не знайдений.")
        except ValueError:
            update.message.reply_text("Будь ласка, введіть дійсне ID.")
        context.user_data['awaiting_user_id'] = False

def block_user(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    admin_id = query.from_user.id
    if str(admin_id) == ADMIN_ID:
        target_user_id = int(query.data.split('_')[1])
        blocked = is_user_blocked(target_user_id)
        if blocked:
            unblock_user(target_user_id)
            context.bot.send_message(chat_id=target_user_id, text="⚠️ Ви розблоковані.")
            query.edit_message_text("Користувач розблокований.")
        else:
            block_user_in_db(target_user_id)
            context.bot.send_message(chat_id=target_user_id, text="⚠️ Ви заблоковані.")
            query.edit_message_text("Користувач заблокований.")
    else:
        query.edit_message_text("Ви не маєте доступу до цієї команди.")

def view_transactions(update: Update, context: CallbackContext) -> None:
    user_id = update.callback_query.from_user.id
    if str(user_id) == ADMIN_ID:
        transactions = get_all_transactions()
        transactions_text = "\n".join(f"{t[0]}: {t[1]} TON to {t[2]}" for t in transactions)
        context.bot.send_message(chat_id=user_id, text=f"Останні транзакції:\n{transactions_text}")
    else:
        context.bot.send_message(chat_id=user_id, text="Ви не маєте доступу до цієї команди.")

# Базові функції для роботи з базою даних
def create_database():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        balance REAL DEFAULT 0,
        last_collected TIMESTAMP,
        blocked INTEGER DEFAULT 0
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        amount REAL,
        to_address TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

def add_user_to_db(user_id, username):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
    conn.commit()
    conn.close()

def get_user_info(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT username, balance FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result

def update_balance(user_id, amount):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
    conn.commit()
    conn.close()

def get_last_collected_time(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT last_collected FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return datetime.fromisoformat(result[0]) if result and result[0] else None

def update_last_collected_time(user_id, time):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET last_collected = ? WHERE user_id=?", (time.isoformat(), user_id))
    conn.commit()
    conn.close()

def get_user_count():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]
    conn.close()
    return count

def get_all_user_ids():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    user_ids = [row[0] for row in c.fetchall()]
    conn.close()
    return user_ids

def get_bot_start_date():
    # Replace with the actual bot start date
    return datetime(2024, 5, 1)

def is_user_blocked(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT blocked FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] == 1 if result else False

def block_user_in_db(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET blocked = 1 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def unblock_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE users SET blocked = 0 WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()

def get_all_transactions():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT user_id, amount, to_address FROM transactions ORDER BY timestamp DESC")
    transactions = c.fetchall()
    conn.close()
    return transactions

# Основний код
def main():
    create_database()
    
    updater = Updater(TOKEN, use_context=True)

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("admin", admin_panel))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main(
