# Инструкция по выгрузке на GitHub

## Шаги для выгрузки кода:

1. Откройте терминал в директории проекта:
   ```
   cd "C:\Users\Красавчик\Documents\GitHub\stitch-cafe"
   ```

2. Инициализируйте git (если еще не инициализирован):
   ```
   git init
   ```

3. Добавьте remote репозиторий (замените URL на ваш):
   ```
   git remote add origin https://github.com/ВАШ_USERNAME/stitch-cafe.git
   ```
   или если репозиторий уже существует:
   ```
   git remote set-url origin https://github.com/ВАШ_USERNAME/stitch-cafe.git
   ```

4. Добавьте все файлы:
   ```
   git add .
   ```

5. Создайте первый коммит:
   ```
   git commit -m "Initial commit: Telegram bot for cross-stitch cafe game"
   ```

6. Переименуйте ветку в main (если нужно):
   ```
   git branch -M main
   ```

7. Выгрузите на GitHub:
   ```
   git push -u origin main
   ```

## Если репозиторий уже существует на GitHub:

Если на GitHub уже есть файлы (например, README), используйте:
```
git pull origin main --allow-unrelated-histories
```
Затем разрешите конфликты (если есть) и:
```
git push -u origin main
```
