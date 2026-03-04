# BabyKeyboard 2

Безопасная полноэкранная песочница для малышей. Ребёнок может нажимать любые клавиши и водить мышкой — приложение показывает символы поверх живой анимации пузырьков шампанского. Выйти из программы случайно невозможно.

## Что видит ребёнок

- **Пузырьки** — 18 стеклянных пузырей (стиль Windows Aero) медленно всплывают снизу вверх, слегка покачиваясь
- **Лопание** — наведи мышь на пузырь, и он лопнет на мелкие осколки, которые тоже всплывают вверх
- **Шипение** — в верхней части экрана постоянно появляется шипение, как у шампанского; вспышка шипения происходит каждый раз, когда пузырь достигает верха
- **Шлейф мыши** — движение мышки оставляет радужный светящийся след
- **Текст** — любые нажатые клавиши отображаются крупными буквами поверх всей анимации
- **Фон** — мягкий голубой градиент с акварельными пятнами, как в Telegram

## Как выйти

**Ctrl + Enter** — единственный способ закрыть программу. Все остальные системные комбинации заблокированы:

| Заблокировано | Причина |
|---|---|
| Win / Cmd+Tab | Переключение приложений |
| Alt+F4 / Cmd+Q | Закрытие приложения |
| Ctrl+Esc / Cmd+Space | Меню пуск / Spotlight |
| Cmd+H, Cmd+M | Скрыть / свернуть |
| Cmd+Alt+Esc | Force Quit |

## Установка и запуск

### Windows

```bash
pip install pygame
python baby_keyboard.py
```

### macOS

```bash
pip3 install pygame pyobjc-framework-Quartz
python3 baby_keyboard_macos.py
```

> **macOS**: После запуска дайте разрешение в
> *Системные настройки → Конфиденциальность → Универсальный доступ*

## Сборка исполняемых файлов

### Windows → `BabyKeyboard2.exe`

```bat
build_windows.bat
```

Результат: `dist\BabyKeyboard2.exe` — один файл, без установки Python.

### macOS → `BabyKeyboard2`

```bash
bash build_macos.sh
```

Результат: `dist/BabyKeyboard2` — один файл, без установки Python.

## Тесты

```bash
pip install pytest
python -m pytest test_baby_keyboard.py -v
```

Покрытие тестов:

| Класс тестов | Что проверяется |
|---|---|
| `TestCtrlEnterExit` | Выход **только** по Ctrl+Enter; Escape/Enter/Alt+F4 не закрывают; логика хука |
| `TestBubbleLifecycle` | Движение вверх, лопание по наведению, смерть за верхним краем, частицы, границы |
| `TestFizzSystem` | Spawn частиц, удаление мёртвых, burst, направление вверх |
| `TestBubbleCache` | Кэш возвращает одинаковый объект для одного радиуса, per-pixel alpha |
| `TestBackground` | Правильный размер, наличие градиента |
| `TestDrawing` | Отрисовка не падает при любых параметрах |
| `TestStability` | 10 сек симуляция @ 60 fps, dt-spike, нет утечки памяти |

## Файлы проекта

```
baby_keyboard/
├── baby_keyboard.py         — Windows-версия
├── baby_keyboard_macos.py   — macOS-версия
├── test_baby_keyboard.py    — тесты (Windows)
├── build_windows.bat        — сборка BabyKeyboard2.exe
├── build_macos.sh           — сборка BabyKeyboard2 (macOS)
└── README.md
```

## Технический стек

- **Python 3.9+**
- **pygame** — графика и события
- **ctypes / Win32** (Windows) — low-level keyboard hook, блокировка системных клавиш
- **pyobjc-framework-Quartz** (macOS) — CGEventTap, блокировка системных клавиш
- **PyInstaller** — сборка в один исполняемый файл
