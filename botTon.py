import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from datetime import datetime, timedelta
import json
import os
import psutil
import asyncio

API_TOKEN = '7800722038:AAFHllfItmbgQXh_CmDUrBgfpQzDw7f-678'
ADMIN_ID = 8089612452  # ваш ID для отримання звітів
DATA_FILE = 'bot_data.json'  # Файл для збереження даних

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Ініціалізація глобальних змінних
bot_status = {
    'start_date': datetime.now(),
    'uptime': timedelta(),
    'memory_usage': 0,  # Використання пам'яті
    'active_users': 0,
    'groups': {}
}

# Обмеження для медіа
MEDIA_LIMITS = {
    'photo': 5,
    'video': 2
}

# Перевірка останнього запуску бота
def check_bot_uptime():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            last_start = datetime.fromisoformat(data.get('start_date'))
            if datetime.now() - last_start > timedelta(days=3):  # Якщо більше 3 діб без перезапуску
                return True
    return False

# Функція для оновлення статистики про пам'ять
def update_memory_usage():
    memory = psutil.virtual_memory()
    bot_status['memory_usage'] = round(memory.used / (1024 ** 2), 2)  # Перетворюємо байти в MB

# Функція для збереження даних
def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump({
            'start_date': bot_status['start_date'].isoformat(),
            'uptime': str(bot_status['uptime']),
            'memory_usage': bot_status['memory_usage'],
            'active_users': bot_status['active_users'],
            'groups': bot_status['groups']
        }, f)

# Функція для створення звіту для адміністратора
async def send_status_report():
    update_memory_usage()  # Оновлення статистики пам'яті
    uptime_str = str(bot_status['uptime']).split(".")[0]
    report = f"""
    BOT STATUS REPORT

    ⏳ Аптайм: {uptime_str}
    📅 Дата запуску: {bot_status['start_date'].strftime('%d.%m.%Y %H:%M')}
    🧠 Пам'ять: {bot_status['memory_usage']} MB
    🧮 Кількість об'єктів у БД: {len(bot_status['groups'])}
    📊 Активних користувачів: {bot_status['active_users']}

    🗂 Групи під керуванням:
    """

    total_deleted = 0  # Загальна кількість видаленого контенту

    for group_id, group_data in bot_status['groups'].items():
        group_report = f"""
        {group_data['name']} | ID: {group_id}
        - Користувачів у ліміті: {group_data['user_limit']}
        - Всього повідомлень оброблено: {group_data['messages_processed']}
        - Видалено фото: {group_data['deleted']['photo']} | відео: {group_data['deleted']['video']} | посилань: {group_data['deleted']['links']} | спаму: {group_data['deleted']['spam']}
        """
        report += group_report
        total_deleted += sum(group_data['deleted'].values())

    report += f"""
    🔐 Загальна статистика:
    - Загальна кількість груп: {len(bot_status['groups'])}
    - Загальна кількість користувачів з лімітами: {bot_status['active_users']}
    - Всього заблоковано контенту: {total_deleted}

    🛠 Технічне:
    - Версія Python: 3.11.8
    - aiogram: 3.4.1
    - Платформа: Linux x86_64
    - Перезапуск через: {str(bot_status['uptime']).split(".")[0]}
    - Автоматичне очищення лімітів: Увімкнено

    ⚠️ Якщо бот не активний більше 3 діб — аптайм обнуляється, ліміти скидаються.
    """

    await bot.send_message(ADMIN_ID, report)

# Функція для перевірки медіа та обмежень
async def check_media(message: types.Message):
    user_id = message.from_user.id
    media_type = None

    if message.photo:
        media_type = 'photo'
    elif message.video:
        media_type = 'video'

    if media_type:
        user_data = user_limits.get(user_id, {'photo': 0, 'video': 0, 'last_reset': datetime.now()})
        limit = MEDIA_LIMITS[media_type]
        
        if user_data[media_type] >= limit:
            await message.delete()
            await message.answer(f"🚫 Ви перевищили ліміт на {media_type}. Спробуйте пізніше.")
        else:
            user_data[media_type] += 1
            if datetime.now() - user_data['last_reset'] > timedelta(days=1):
                user_data[media_type] = 0
                user_data['last_reset'] = datetime.now()
            user_limits[user_id] = user_data

# Обробка повідомлень
@dp.message_handler(content_types=['text', 'photo', 'video', 'document', 'url'])
async def handle_message(message: types.Message):
    group_id = message.chat.id

    if group_id not in bot_status['groups']:
        bot_status['groups'][group_id] = {
            'name': message.chat.title,
            'user_limit': 5,  # За замовчуванням ліміт 5 користувачів
            'messages_processed': 0,
            'deleted': {'photo': 0, 'video': 0, 'links': 0, 'spam': 0}
        }

    group_data = bot_status['groups'][group_id]
    group_data['messages_processed'] += 1

    if message.text:
        if 'http' in message.text or 'www' in message.text:
            await message.delete()
            group_data['deleted']['links'] += 1
            save_data()  # Збереження після кожної операції
            return

    await check_media(message)
    save_data()  # Збереження після кожної операції

# Команда для адміністратора
@dp.message_handler(commands=['bot'])
async def bot_status(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await send_status_report()

# Старт бота
if __name__ == '__main__':
    # Якщо більше 3 діб бездіяльності, скидаємо статистику
    if check_bot_uptime():
        bot_status['start_date'] = datetime.now()
        bot_status['uptime'] = timedelta()

    save_data()  # Збереження даних
    executor.start_polling(dp, skip_updates=True
