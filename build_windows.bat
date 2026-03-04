@echo off
REM Сборка BabyKeyboard.exe (v1) и BabyKeyboard2.exe (v2) для Windows
REM Запуск: build_windows.bat

echo === Установка зависимостей ===
pip install pygame pyinstaller

echo.
echo === Сборка v1 (старый дизайн) - BabyKeyboard.exe ===
python -m PyInstaller --onefile --noconsole --name "BabyKeyboard" --distpath dist baby_keyboard_v1.py

echo.
echo === Сборка v2 (новый дизайн) - BabyKeyboard2.exe ===
python -m PyInstaller --onefile --noconsole --name "BabyKeyboard2" --distpath dist baby_keyboard.py

echo.
echo === Готово! ===
echo   dist\BabyKeyboard.exe  — старый дизайн (статичные пузырьки)
echo   dist\BabyKeyboard2.exe — новый дизайн (Aero glass, интерактивные)
pause
