#!/bin/bash
# Сборка BabyKeyboard2 для macOS
# Запускать на Mac: bash build_macos.sh

set -e

echo "=== Установка зависимостей ==="
pip3 install pygame pyobjc-framework-Quartz pyinstaller

echo "=== Сборка приложения ==="
python3 -m PyInstaller \
    --onefile \
    --noconsole \
    --name "BabyKeyboard2" \
    --osx-bundle-identifier "com.babykeyboard2.app" \
    baby_keyboard_macos.py

echo ""
echo "=== Готово! ==="
echo "Исполняемый файл: dist/BabyKeyboard2"
echo ""
echo "ВАЖНО: Перед запуском дайте разрешение в"
echo "Системные настройки → Конфиденциальность → Универсальный доступ"
