#!/bin/bash
# Сборка BabyKeyboard (v1, старый дизайн) и BabyKeyboard2 (v2, новый дизайн) для macOS
# Запускать на Mac: bash build_macos.sh

set -e

echo "=== Установка зависимостей ==="
pip3 install pygame pyobjc-framework-Quartz pyinstaller

echo ""
echo "=== Сборка v1 (старый дизайн) → BabyKeyboard ==="
python3 -m PyInstaller \
    --onefile \
    --noconsole \
    --name "BabyKeyboard" \
    --osx-bundle-identifier "com.babykeyboard.app" \
    baby_keyboard_macos_v1.py

echo ""
echo "=== Сборка v2 (новый дизайн) → BabyKeyboard2 ==="
python3 -m PyInstaller \
    --onefile \
    --noconsole \
    --name "BabyKeyboard2" \
    --osx-bundle-identifier "com.babykeyboard2.app" \
    baby_keyboard_macos.py

echo ""
echo "=== Готово! ==="
echo "  dist/BabyKeyboard   — старый дизайн (статичные пузырьки)"
echo "  dist/BabyKeyboard2  — новый дизайн (Aero glass, интерактивные пузырьки)"
echo ""
echo "ВАЖНО: Перед запуском дайте разрешение в"
echo "Системные настройки → Конфиденциальность → Универсальный доступ"
