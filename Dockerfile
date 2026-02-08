FROM python:3.12-slim

WORKDIR /app

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Код приложения
COPY . .

# Папки для БД и логов (создаются при первом запуске)
RUN mkdir -p data logs

CMD ["python", "main.py"]
