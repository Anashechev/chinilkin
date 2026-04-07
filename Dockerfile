# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости для PostgreSQL
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем проект
COPY . .

# Создаем директорию для логов
RUN mkdir -p logs

# Собираем статические файлы
RUN python manage.py collectstatic --noinput

# Применяем миграции
RUN python manage.py migrate

# Активируем существующих пользователей для обратной совместимости
RUN python manage.py activate_existing_users

# Открываем порт
EXPOSE 8000

# Запускаем gunicorn для production
CMD ["gunicorn", "chinilkin.wsgi:application", "--bind", "0.0.0.0:8000"]
