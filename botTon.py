import logging
import requests
from datetime import datetime, timedelta
import json
import os
import psutil
import time

API_TOKEN = '7800722038:AAFHllfItmbgQXh_CmDUrBgfpQzDw7f-678'
ADMIN_ID = 8089612452  # ваш ID для отримання звітів
DATA_FILE = 'bot_data.json'  # Файл для збереження даних

logging.basicConfig(level=logging.INFO)

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
def send_status_report():
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
    - Платформа: Linux x86_64
    - Перезапуск через: {str(bot_status['uptime']).split(".")[0]}
    - Автоматичне очищення лімітів: Увімкнено

    ⚠️ Якщо бот не активний більше 3 діб — аптайм обнуляється, ліміти скидаються.
    """

    # Надсилаємо повідомлення через Telegram API
    url = f'https://api.telegram.org/bot{API_TOKEN}/sendMessage'
    payload = {
        'chat_id': ADMIN_ID,
        'text': report
    }
    response = requests.post(url, data=payload)
    if response.status_code != 200:
        logging.error(f"Error sending report: {response.text}")

# Функція для перевірки медіа та обмежень
def check_media(message):
    user_id = message['from']['id']
    media_type = None

    if 'photo' in message:
        media_type = 'photo'
    elif 'video' in message:
        media_type = 'video'

    if media_type:
        user_data = user_limits.get(user_id, {'photo': 0, 'video': 0, 'last_reset': datetime.now()})
        limit = MEDIA_LIMITS[media_type]
        
        if user_data[media_type] >= limit:
            delete_message(message['message_id'])
            send_message(message['chat']['id'], f"🚫 Ви перевищили ліміт на {media_type}. Спробуйте пізніше.")
        else:
            user_data[media_type] += 1
            if datetime.now() - user_data['last_reset'] > timedelta(days=1):
                user_data[media_type] = 0
                user_data['last_reset'] = datetime.now()
            user_limits[user_id] = user_data

# Функція для надсилання повідомлень
def send_message(chat_id, text):
    url = f'https://api.telegram.org/bot{API_TOKEN}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': text
    }
    response = requests.post(url, data=payload)
    if response.status_code != 200:
        logging.error(f"Error sending message: {response.text}")

# Функція для видалення повідомлень
def delete_message(message_id):
    url = f'https://api.telegram.org/bot{API_TOKEN}/deleteMessage'
    payload = {
        'chat_id': message_id['chat']['id'],
        'message_id': message_id
    }
    response = requests.post(url, data=payload)
    if response.status_code != 200:
        logging.error(f"Error deleting message: {response.text}")

# Функція для обробки повідомлень
def handle_message(message):
    group_id = message['chat']['id']

    if group_id not in bot_status['groups']:
        bot_status['groups'][group_id] = {
            'name': message['chat']['title'],
            'user_limit': 5,  # За замовчуванням ліміт 5 користувачів
            'messages_processed': 0,
            'deleted': {'photo': 0, 'video': 0, 'links': 0, 'spam': 0}
        }

    group_data = bot_status['groups'][group_id]
    group_data['messages_processed'] += 1

    if 'text' in message:
        if 'http' in message['text'] or 'www' in message['text']:
            delete_message(message['message_id'])
            group_data['deleted']['links'] += 1
            save_data()  # Збереження після кожної операції
            return

    check_media(message)
    save_data()  # Збереження після кожної операції

# Основний цикл бота
if __name__ == '__main__':
    # Якщо більше 3 діб бездіяльності, скидаємо статистику
    if check_bot_uptime():
        bot_status['start_date'] = datetime.now()
        bot_status['uptime'] = timedelta()

    save_data()  # Збереження даних

    while True:
        # Потрібно отримати оновлення з Telegram API
        url = f'https://api.telegram.org/bot{API_TOKEN}/getUpdates'
        response = requests.get(url)
        if response.status_code == 200:
            updates = response.json().get('result', [])
            for update in updates:
                if 'message' in update:
                    handle_message(update['message'])

        time.sleep(1)  # Перевіряємо кожну секунду
