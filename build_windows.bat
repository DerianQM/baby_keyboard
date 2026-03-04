@echo off
REM Сборка BabyKeyboard2.exe для Windows
REM Запуск: build_windows.bat

echo === Установка зависимостей ===
pip install pygame pyinstaller

echo === Сборка ===
python -m PyInstaller ^
    --onefile ^
    --noconsole ^
    --name "BabyKeyboard2" ^
    baby_keyboard.py

echo.
echo === Готово! ===
echo Исполняемый файл: dist\BabyKeyboard2.exe
pause
