@echo off
chcp 65001 >nul
echo ========================================
echo Выгрузка проекта на GitHub
echo ========================================
echo.

cd /d "%~dp0"

echo Проверка git...
git --version
echo.

echo Инициализация git (если нужно)...
if not exist .git (
    git init
    echo Git инициализирован
) else (
    echo Git уже инициализирован
)
echo.

echo Добавление файлов...
git add .
echo.

echo Создание коммита...
git commit -m "Initial commit: Telegram bot for cross-stitch cafe game with error handling and docstrings"
echo.

echo Проверка remote...
git remote -v
echo.

echo ========================================
echo ВАЖНО: Убедитесь, что remote настроен правильно!
echo Если remote не настроен, выполните:
echo   git remote add origin https://github.com/ВАШ_USERNAME/stitch-cafe.git
echo или
echo   git remote set-url origin https://github.com/ВАШ_USERNAME/stitch-cafe.git
echo ========================================
echo.

set /p PUSH="Выгрузить на GitHub? (y/n): "
if /i "%PUSH%"=="y" (
    echo Переименование ветки в main...
    git branch -M main
    echo.
    echo Выгрузка на GitHub...
    git push -u origin main
    echo.
    echo Готово!
) else (
    echo Выгрузка отменена. Выполните команды вручную.
)

pause
