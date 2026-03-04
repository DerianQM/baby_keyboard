#!/bin/bash
# Сборка BabyKeyboard для macOS
# Запускать на Mac: bash build_macos.sh

set -e

echo "=== Установка зависимостей ==="
pip3 install pygame pyobjc-framework-Quartz pyinstaller

echo "=== Сборка приложения ==="
python3 -m PyInstaller \
    --onefile \
    --noconsole \
    --name "BabyKeyboard" \
    --osx-bundle-identifier "com.babykeyboard.app" \
    baby_keyboard_macos.py

echo ""
echo "=== Готово! ==="
echo "Исполняемый файл: dist/BabyKeyboard"
echo ""
echo "ВАЖНО: Перед запуском дайте разрешение в"
echo "Системные настройки → Конфиденциальность → Универсальный доступ"
