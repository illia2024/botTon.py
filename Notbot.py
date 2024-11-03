import requests
import json
import os
from datetime import datetime, timedelta

# Вставте ваш токен бота
TOKEN = '7909956325:AAHhd9WKiyfmHUT7g2AnMxIgVHp6Gup-M30'
BASE_URL = f'https://api.telegram.org/bot{TOKEN}'

# ID адміністратора
ADMIN_ID = '1428115542'
DEVELOPER_USERNAME = 'xxqwer_x'

# Словники для відстеження станів
user_state = {}
blocked_users = {}
admin_reply_state = {}
user_bots = {}

# Завантаження стану блокування з файлу
if os.path.exists("blocked_users.json"):
    with open("blocked_users.json", "r") as file:
        blocked_users = json.load(file)

# Завантаження інформації про ботів користувачів
if os.path.exists("user_bots.json"):
    with open("user_bots.json", "r") as file:
        user_bots = json.load(file)

# Функція для надсилання повідомлень
def send_message(chat_id, text, reply_markup=None):
    url = f'{BASE_URL}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML'
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup
    requests.post(url, json=payload)

# Функція для збереження стану блокування
def save_blocked_users():
    with open("blocked_users.json", "w") as file:
        json.dump(blocked_users, file)

# Функція для збереження інформації про ботів користувачів
def save_user_bots():
    with open("user_bots.json", "w") as file:
        json.dump(user_bots, file)

# Функція для створення кнопок для адміністратора
def generate_admin_buttons(user_id):
    block_text = "🔓 Розблокувати" if blocked_users.get(user_id) else "🚫 Заблокувати"
    block_callback = f'unblock_{user_id}' if blocked_users.get(user_id) else f'block_{user_id}'
    return {
        'inline_keyboard': [
            [{'text': '✅ Відповісти', 'callback_data': f'reply_{user_id}'}, {'text': block_text, 'callback_data': block_callback}]
        ]
    }

# Функція для автоматичного видалення бота
def delete_inactive_bots():
    now = datetime.now()
    activity_timeout = timedelta(days=2)
    for user_id, bot_info in list(user_bots.items()):
        last_active = datetime.fromisoformat(bot_info['last_active'])
        if now - last_active > activity_timeout:
            del user_bots[user_id]
            save_user_bots()
            send_message(user_id, 'Ваш бот був видалений через відсутність активності протягом 2 днів.')

# Обробник запитів
def handle_update(update):
    message = update.get('message', {})
    text = message.get('text', '')
    chat_id = message.get('chat', {}).get('id')

    # Обробка кнопок адміністратора
    callback_data = update.get('callback_query', {}).get('data')
    if callback_data:
        callback_query_id = update['callback_query']['id']
        from_id = update['callback_query']['from']['id']

        if callback_data.startswith("reply_"):
            user_id = int(callback_data.split("_")[1])
            admin_reply_state[from_id] = user_id
            send_message(from_id, 'Введіть вашу відповідь, і я надішлю її користувачу.')

        elif callback_data.startswith("block_"):
            user_id = int(callback_data.split("_")[1])
            blocked_users[user_id] = True
            save_blocked_users()
            send_message(from_id, 'Користувача заблоковано.', generate_admin_buttons(user_id))

        elif callback_data.startswith("unblock_"):
            user_id = int(callback_data.split("_")[1])
            blocked_users.pop(user_id, None)
            save_blocked_users()
            send_message(from_id, 'Користувача розблоковано.', generate_admin_buttons(user_id))

        return

    # Якщо адміністратор у режимі відповіді
    if chat_id == int(ADMIN_ID) and chat_id in admin_reply_state:
        target_user = admin_reply_state.pop(chat_id)
        send_message(target_user, f'Відповідь від адміністратора: {text}')
        send_message(chat_id, 'Відповідь надіслано користувачу.')

    # Якщо користувач натиснув "⚡Написати"
    elif text == '⚡Написати':
        if blocked_users.get(chat_id):
            send_message(chat_id, 'Вибачте, але ви заблоковані і не можете надсилати повідомлення.')
            return

        user_state[chat_id] = 'waiting_for_message'
        send_message(chat_id, 'Напишіть ваше повідомлення, і я надішлю його адміністратору.')

    # Якщо користувач натиснув "Анонімне повідомлення"
    elif text == 'Анонімне повідомлення':
        if blocked_users.get(chat_id):
            send_message(chat_id, 'Вибачте, але ви заблоковані і не можете надсилати повідомлення.')
            return

        user_state[chat_id] = 'waiting_for_anonymous_message'
        send_message(chat_id, 'Напишіть ваше повідомлення, і я надішлю його адміністратору анонімно.')

    # Якщо користувач у режимі "Написати"
    elif user_state.get(chat_id) == 'waiting_for_message':
        send_message(ADMIN_ID, f'Повідомлення від користувача @{message["chat"].get("username", "невідомий")}:\n\n{text}', generate_admin_buttons(chat_id))
        send_message(chat_id, '✨Повідомлення надіслано')
        user_state[chat_id] = None

    # Якщо користувач у режимі "Анонімне повідомлення"
    elif user_state.get(chat_id) == 'waiting_for_anonymous_message':
        send_message(ADMIN_ID, f'Анонімне повідомлення:\n\n{text}', generate_admin_buttons(chat_id))
        send_message(chat_id, '✨Анонімне повідомлення надіслано')
        user_state[chat_id] = None

    # Команда "🖇️ІнФо"
    elif text == '🖇️ІнФо':
        info_text = "🖇️ІнФо\n〰️〰️〰️〰️〰️〰️〰️〰️\n📌Старт бота: 30.10.2024 року"
        send_message(chat_id, info_text)

    # Команда "⚙️Хочу такого самого бота"
    elif text == '⚙️Хочу такого самого бота':
        send_message(chat_id, f'Перейдіть в чат із розробником: @{DEVELOPER_USERNAME}')

    # Команда для створення нового бота
    elif text.startswith('/create_my_bot'):
        user_state[chat_id] = 'waiting_for_bot_token'
        send_message(chat_id, 'Введіть токен вашого бота.')

    # Якщо користувач вводить токен
    elif user_state.get(chat_id) == 'waiting_for_bot_token':
        token = text
        user_state[chat_id] = 'waiting_for_user_id'
        user_bots[chat_id] = {
            'token': token,
            'username': message.get('chat', {}).get('username'),
            'last_active': datetime.now().isoformat()
        }
        save_user_bots()
        send_message(chat_id, 'Токен прийнято. Тепер введіть ваш ID.')

    # Якщо користувач вводить свій ID
    elif user_state.get(chat_id) == 'waiting_for_user_id':
        user_id = text
        user_bots[chat_id]['user_id'] = user_id
        save_user_bots()
        send_message(chat_id, f'⚙️Бот створено в: @{message.get("chat", {}).get("username")}\n'
                              f'🔸Бот створено для зв\'язку із @{DEVELOPER_USERNAME}')
        user_state[chat_id] = None

    # Головне меню для команди /start
    elif text == '/start':
        main_menu(chat_id)

# Головне меню з кнопками
def main_menu(chat_id):
    reply_markup = {
        'keyboard': [
            [{'text': '⚡Написати'}, {'text': 'Анонімне повідомлення'}, {'text': '🖇️ІнФо'}],
            [{'text': '⚙️Хочу такого самого бота'}]
        ],
        'resize_keyboard': True,
        'one_time_keyboard': True
    }
    welcome_text = "🔸Бот створено для зв'язку із @xxqwer_x"
    send_message(chat_id, welcome_text, reply_markup=reply_markup)

# Основна функція для запуску бота
def main():
    # Перевірка наявності нових оновлень
    last_update_id = None
    while True:
        updates = requests.get(f'{BASE_URL}/getUpdates?offset={last_update_id}').json()
        for update in updates['result']:
            handle_update(update)
            last_update_id = update['update_id'] + 1

        # Періодичне видалення неактивних ботів
        delete_inactive_bots()

# Запуск бота
if __name__ == '__main__':
    main()
