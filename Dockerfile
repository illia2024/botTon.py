# Використовуємо базовий образ Python
FROM python:3.10

# Встановлюємо робочу директорію всередині контейнера
WORKDIR /app

# Копіюємо всі файли проєкту в контейнер
COPY . .

# Встановлюємо залежності
RUN pip install --no-cache-dir -r requirements.txt

# Запускаємо бота
CMD ["python", "bot.py"]
