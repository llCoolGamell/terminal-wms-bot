"""WMS Loop Automator v7.0.

Робот для повторяющихся операций в WMS-терминале (Windows).
Отличия от прошлых версий:

* верхняя цветная статусная панель (серый / зелёный / синий / красный);
* бот следует за всем НАБОРОМ заголовков WMS-окон, а не за одним —
  это устраняет баг, когда после первого нажатия заголовок диалога
  менялся и бот терял окно;
* OCR (Tesseract) подключается опционально через галку;
* две независимые регулировки скорости — интервал цикла и
  скорость клавиатуры;
* кнопка Пауза, глобальный hotkey ПРОБЕЛ = Пуск/Пауза;
* редактор маппинга доков прямо в UI (сохранение в JSON);
* сторож от зависания (auto-pause если экран не меняется);
* кнопка "Тест экрана" для диагностики;
* live-статистика и история циклов в CSV.
"""

from __future__ import annotations

import csv
import json
import os
import re
import sys
import threading
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Optional

import customtkinter as ctk
import pyautogui
import pyperclip
import pygetwindow as gw

try:
    from PIL import ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

try:
    import keyboard as kb
    KEYBOARD_AVAILABLE = True
except ImportError:
    KEYBOARD_AVAILABLE = False


APP_VERSION = "7.0"
APP_DIR = Path(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))))
# Все рантайм-файлы рядом с exe / скриптом (а не во временной папке PyInstaller)
RUNTIME_DIR = Path(os.path.dirname(os.path.abspath(sys.argv[0]))) if getattr(sys, "frozen", False) else Path.cwd()
DOCKS_JSON = RUNTIME_DIR / "wms_docks.json"
CYCLES_CSV = RUNTIME_DIR / "wms_cycles.csv"
LAST_SCREEN_PNG = RUNTIME_DIR / "last_screen.png"
LAST_OCR_TXT = RUNTIME_DIR / "last_ocr.txt"

DEFAULT_DOCK_MAPPING = {
    "аша дальняя": "D-A-DL-4-2",
    "миасс": "D-MIASS-1-1",
    "север 2": "D-SEV2-5-1",
    "самовывоз": "D-PICKUP",
    "вип": "D-VIP",
    "ленинский": "D-LR-2-4",
    "курган": "D-KURG-O",
    "златоуст": "D-ZLAT-4-4",
    "троицк дальний": "D-TR-DL-5-1",
    "бреды": "D-BRDY-3-4",
    "кизил": "D-KIZIL-2-2",
    "магнитогорск": "D-MG-P-1-1",
    "чтз": "D-4TZ-2-3",
    "северо запад": "D-SZ-1-2",
    "магнитогорск левый": "D-MG-L-2-3",
    "верхнеуральск": "D-V-UR-2-1",
    "чмз": "D-4MZ-2-1",
    "копейск": "D-KOP-2-3",
    "центр": "D-CNTR-2-1",
}

UNIVERSAL_CELL = "D-KM-1"

# Заголовки окон, на которые бот реагирует. Бот следует за любым из них —
# это и есть фикс главного бага.
WMS_TITLES = (
    "Главное меню",
    "Взятие работы",
    "Выбор работ",
    "Перемещение к источнику",
    "Поиск паллеты",
    "Поиск коробки",
    "Поиск места-приёмника",
    "Поиск места-приемника",  # вариант без ё
    "Размещение в место",
)

# Стандартные пути к Tesseract (Windows).
TESSERACT_CANDIDATES = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"C:\Tesseract-OCR\tesseract.exe",
)

ERROR_MARKERS = ("не найден", "не существует", "не зарегистрирован", "ошибк")

# Watchdog: сколько секунд экран должен не меняться, чтобы поставить паузу.
WATCHDOG_SECONDS = 30.0

# pyautogui — отключаем встроенную межоперационную задержку, мы сами управляем.
pyautogui.PAUSE = 0.0
pyautogui.FAILSAFE = True


# ---------------------- Утилиты ----------------------


def find_tesseract() -> Optional[str]:
    env = os.environ.get("TESSERACT_CMD")
    if env and os.path.isfile(env):
        return env
    for cand in TESSERACT_CANDIDATES:
        if os.path.isfile(cand):
            return cand
    return None


def load_docks() -> dict:
    if DOCKS_JSON.exists():
        try:
            with open(DOCKS_JSON, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return {str(k).lower(): str(v) for k, v in data.items()}
        except Exception:
            pass
    return dict(DEFAULT_DOCK_MAPPING)


def save_docks(mapping: dict) -> None:
    try:
        with open(DOCKS_JSON, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def detect_wms_title(title: str, extra_substr: str = "") -> Optional[str]:
    """Если title совпадает с одним из известных WMS-заголовков, вернуть его."""
    if not title:
        return None
    t = title.strip()
    for wt in WMS_TITLES:
        if wt.lower() in t.lower():
            return wt
    if extra_substr and extra_substr.lower() in t.lower():
        return t
    return None


def safe_activate(win) -> bool:
    """Активировать окно, обходя известный баг pygetwindow на Win10/11."""
    try:
        if win.isMinimized:
            win.restore()
        win.activate()
        return True
    except Exception:
        try:
            win.minimize()
            time.sleep(0.05)
            win.restore()
            return True
        except Exception:
            return False


# ---------------------- UI элементы ----------------------


class StatusPanel(ctk.CTkFrame):
    """Цветная панель сверху."""

    COLORS = {
        "idle":    ("#5f6368", "ОЖИДАНИЕ"),
        "running": ("#1e8e3e", "▶ ИДЁТ ПЕРЕМЕЩЕНИЕ"),
        "paused":  ("#1a73e8", "⏸ ПАУЗА"),
        "stopped": ("#d93025", "⏹ ОСТАНОВЛЕНО"),
    }

    def __init__(self, master):
        super().__init__(master, height=46, corner_radius=0, fg_color=self.COLORS["idle"][0])
        self.label = ctk.CTkLabel(self, text=self.COLORS["idle"][1],
                                  font=("Arial", 18, "bold"), text_color="white")
        self.label.pack(expand=True, fill="both", padx=10, pady=4)

    def set_state(self, state: str) -> None:
        color, text = self.COLORS.get(state, self.COLORS["idle"])
        self.configure(fg_color=color)
        self.label.configure(text=text)


class DockEditor(ctk.CTkToplevel):
    """Окно редактирования маппинга зон → код места."""

    def __init__(self, master, mapping: dict, on_save):
        super().__init__(master)
        self.title("Маппинг доков")
        self.geometry("560x560")
        self.transient(master)
        self.grab_set()
        self.on_save = on_save
        self.mapping = dict(mapping)

        ctk.CTkLabel(self, text="Зона (что показывает WMS) → код места",
                     font=("Arial", 14, "bold")).pack(pady=8)
        ctk.CTkLabel(self, text="Поиск идёт по подстроке без учёта регистра.",
                     font=("Arial", 10, "italic"), text_color="#a8a8a8").pack()

        self.list_frame = ctk.CTkScrollableFrame(self, height=380)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=6)

        self.rows: list[dict] = []
        for k, v in self.mapping.items():
            self._add_row(k, v)

        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="x", padx=10, pady=8)
        ctk.CTkButton(bottom, text="➕ Добавить строку", command=lambda: self._add_row("", "")).pack(side="left", padx=4)
        ctk.CTkButton(bottom, text="↺ Сброс к дефолту", fg_color="#6c757d",
                      command=self._reset_default).pack(side="left", padx=4)
        ctk.CTkButton(bottom, text="💾 Сохранить", fg_color="#1e8e3e", width=140,
                      command=self._save).pack(side="right", padx=4)

    def _add_row(self, key: str, val: str) -> None:
        row = ctk.CTkFrame(self.list_frame)
        row.pack(fill="x", pady=2, padx=2)
        ek = ctk.CTkEntry(row, width=240, placeholder_text="название зоны (нижний регистр)")
        ek.insert(0, key)
        ek.pack(side="left", padx=4, pady=4)
        ev = ctk.CTkEntry(row, width=160, placeholder_text="код места")
        ev.insert(0, val)
        ev.pack(side="left", padx=4, pady=4)
        record = {"frame": row, "key": ek, "val": ev}
        btn = ctk.CTkButton(row, text="✖", width=34, fg_color="#d93025",
                            command=lambda r=record: self._remove(r))
        btn.pack(side="left", padx=4, pady=4)
        self.rows.append(record)

    def _remove(self, record: dict) -> None:
        record["frame"].destroy()
        self.rows = [r for r in self.rows if r is not record]

    def _reset_default(self) -> None:
        for r in self.rows:
            r["frame"].destroy()
        self.rows.clear()
        for k, v in DEFAULT_DOCK_MAPPING.items():
            self._add_row(k, v)

    def _save(self) -> None:
        new_mapping: dict = {}
        for r in self.rows:
            k = r["key"].get().strip().lower()
            v = r["val"].get().strip().upper()
            if k and v:
                new_mapping[k] = v
        self.on_save(new_mapping)
        self.destroy()


# ---------------------- Основное приложение ----------------------


class WMSBot(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(f"WMS Loop Automator v{APP_VERSION}")
        self.geometry("740x820")
        self.resizable(False, False)

        # ---- состояние ----
        self.is_running = False
        self.is_paused = False
        self.cycles_count = 0
        self.errors_count = 0
        self.fallbacks_count = 0
        self.cycle_times: deque = deque(maxlen=30)
        self.fallback_active = False
        self.target_title_substring: str = ""
        self.docks = load_docks()

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._is_typing = False  # пока True, hotkey-callback игнорирует Space

        self.tesseract_path = find_tesseract()
        if self.tesseract_path and PYTESSERACT_AVAILABLE:
            pytesseract.pytesseract.tesseract_cmd = self.tesseract_path

        self._last_screen_signature = ""
        self._last_screen_change_ts = time.time()
        self._cycle_start_ts: Optional[float] = None
        self._current_cycle = self._fresh_cycle()

        # ---- UI ----
        self._build_ui()
        self._register_hotkey()
        self._refresh_windows_list()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- UI build ----------

    def _build_ui(self) -> None:
        self.status_panel = StatusPanel(self)
        self.status_panel.pack(fill="x")

        # метрики + сброс счётчика + live-stats
        metrics = ctk.CTkFrame(self, fg_color="#2b2b2b")
        metrics.pack(fill="x", padx=10, pady=(8, 4))
        self.lbl_cycles = ctk.CTkLabel(metrics, text="🔁 Циклов: 0",
                                       font=("Arial", 14, "bold"))
        self.lbl_cycles.pack(side="left", padx=12, pady=8)
        ctk.CTkButton(metrics, text="↺ Сброс", width=70,
                      fg_color="#6c757d", command=self._reset_counter).pack(side="left", padx=4)
        self.lbl_stats = ctk.CTkLabel(metrics,
                                      text="📊 Среднее: — | Ошибок: 0 | Фоллбеков: 0",
                                      font=("Arial", 12))
        self.lbl_stats.pack(side="right", padx=12, pady=8)

        # окно
        win_block = ctk.CTkFrame(self, fg_color="#232323")
        win_block.pack(fill="x", padx=10, pady=4)
        ctk.CTkLabel(win_block, text="Окно WMS (выбор вручную или 🎯 Автодетект):",
                     font=("Arial", 12)).pack(anchor="w", padx=10, pady=(8, 2))
        win_row = ctk.CTkFrame(win_block, fg_color="transparent")
        win_row.pack(fill="x", padx=10, pady=(0, 8))
        self.combo_windows = ctk.CTkComboBox(win_row, width=350, values=["—"])
        self.combo_windows.pack(side="left")
        ctk.CTkButton(win_row, text="🔄", width=42,
                      command=self._refresh_windows_list).pack(side="left", padx=4)
        ctk.CTkButton(win_row, text="🎯 Автодетект", width=130,
                      command=self._auto_detect).pack(side="left", padx=4)
        ctk.CTkButton(win_row, text="🔍 Тест", width=80, fg_color="#6c757d",
                      command=self._test_screen).pack(side="left", padx=4)

        # OCR + редактор доков
        ocr_row = ctk.CTkFrame(self, fg_color="transparent")
        ocr_row.pack(fill="x", padx=10, pady=2)
        self.var_ocr = ctk.BooleanVar(value=False)
        self.chk_ocr = ctk.CTkCheckBox(
            ocr_row,
            text="Использовать Tesseract OCR (точнее, но требует установки)",
            variable=self.var_ocr,
            command=self._on_ocr_toggle,
        )
        self.chk_ocr.pack(side="left", padx=10)
        ctk.CTkButton(ocr_row, text="📋 Доки", width=100,
                      command=self._open_dock_editor).pack(side="right", padx=10)

        self.lbl_ocr_status = ctk.CTkLabel(self, text=self._ocr_status_text(),
                                           font=("Arial", 11, "italic"),
                                           text_color="#a8a8a8")
        self.lbl_ocr_status.pack(pady=(0, 4))

        # слайдеры
        sliders = ctk.CTkFrame(self, fg_color="#232323")
        sliders.pack(fill="x", padx=10, pady=4)

        self.var_loop = ctk.DoubleVar(value=0.5)
        self.lbl_loop = ctk.CTkLabel(sliders, text="Интервал цикла: 0.50 с",
                                     font=("Arial", 12))
        self.lbl_loop.pack(anchor="w", padx=12, pady=(8, 0))
        self.sl_loop = ctk.CTkSlider(sliders, from_=0.1, to=2.0,
                                     number_of_steps=19, variable=self.var_loop,
                                     command=self._on_loop_change)
        self.sl_loop.pack(fill="x", padx=12, pady=2)

        self.var_kbd = ctk.DoubleVar(value=0.10)
        self.lbl_kbd = ctk.CTkLabel(sliders, text="Скорость клавиатуры: 0.10 с",
                                    font=("Arial", 12))
        self.lbl_kbd.pack(anchor="w", padx=12, pady=(8, 0))
        self.sl_kbd = ctk.CTkSlider(sliders, from_=0.05, to=1.0,
                                    number_of_steps=19, variable=self.var_kbd,
                                    command=self._on_kbd_change)
        self.sl_kbd.pack(fill="x", padx=12, pady=(2, 10))

        # кнопки
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.pack(pady=8)
        self.btn_start = ctk.CTkButton(btns, text="▶ ПУСК", fg_color="#1e8e3e",
                                       width=180, height=44,
                                       font=("Arial", 14, "bold"),
                                       command=self.start)
        self.btn_start.grid(row=0, column=0, padx=8)
        self.btn_pause = ctk.CTkButton(btns, text="⏸ ПАУЗА", fg_color="#1a73e8",
                                       width=180, height=44,
                                       state="disabled",
                                       font=("Arial", 14, "bold"),
                                       command=self.pause_toggle)
        self.btn_pause.grid(row=0, column=1, padx=8)
        self.btn_stop = ctk.CTkButton(btns, text="⏹ СТОП", fg_color="#d93025",
                                      width=180, height=44,
                                      state="disabled",
                                      font=("Arial", 14, "bold"),
                                      command=self.stop)
        self.btn_stop.grid(row=0, column=2, padx=8)

        hint = ("Глобальная горячая клавиша: ПРОБЕЛ = Пуск/Пауза"
                if KEYBOARD_AVAILABLE
                else "Библиотека 'keyboard' не установлена — глобальные хоткеи отключены")
        ctk.CTkLabel(self, text=hint, font=("Arial", 10, "italic"),
                     text_color="#a8a8a8").pack(pady=(0, 4))

        self.log_box = ctk.CTkTextbox(self, width=720, height=240, font=("Consolas", 11))
        self.log_box.pack(padx=10, pady=8)
        self._log(f"Готов. Версия {APP_VERSION}. "
                  f"Tesseract: {'найден' if self.tesseract_path else 'НЕ найден'}.")

    # ---------- UI helpers ----------

    def _ocr_status_text(self) -> str:
        if not self.var_ocr.get():
            return "OCR выключен — бот работает через буфер обмена (упрощённо)."
        if not PYTESSERACT_AVAILABLE:
            return "⚠ Модуль pytesseract не установлен — OCR не сработает."
        if not self.tesseract_path:
            return ("⚠ Tesseract.exe не найден. Установи с "
                    "https://github.com/UB-Mannheim/tesseract/wiki "
                    "(нужен пакет 'Russian').")
        return f"OCR активен. Tesseract: {self.tesseract_path}"

    def _log(self, msg: str) -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.insert("end", f"[{ts}] {msg}\n")
        self.log_box.see("end")
        # кольцевая обрезка лога — чтоб не разрасталось
        try:
            lines = int(float(self.log_box.index("end-1c").split(".")[0]))
            if lines > 500:
                self.log_box.delete("1.0", f"{lines - 500}.0")
        except Exception:
            pass

    def _log_thread(self, msg: str) -> None:
        self.after(0, lambda: self._log(msg))

    def _set_status(self, state: str) -> None:
        self.after(0, lambda: self.status_panel.set_state(state))

    def _update_stats(self) -> None:
        avg = (f"{sum(self.cycle_times) / len(self.cycle_times):.2f} с"
               if self.cycle_times else "—")
        text = (f"📊 Среднее: {avg} | Ошибок: {self.errors_count} "
                f"| Фоллбеков: {self.fallbacks_count}")
        self.after(0, lambda: self.lbl_stats.configure(text=text))

    def _update_cycles_label(self) -> None:
        self.after(0, lambda: self.lbl_cycles.configure(text=f"🔁 Циклов: {self.cycles_count}"))

    # ---------- UI events ----------

    def _on_ocr_toggle(self) -> None:
        if self.var_ocr.get() and (not PYTESSERACT_AVAILABLE or not self.tesseract_path):
            self._log("⚠ OCR не доступен — Tesseract или pytesseract отсутствуют. "
                      "Бот продолжит через буфер обмена.")
        self.lbl_ocr_status.configure(text=self._ocr_status_text())

    def _on_loop_change(self, value) -> None:
        self.lbl_loop.configure(text=f"Интервал цикла: {float(value):.2f} с")

    def _on_kbd_change(self, value) -> None:
        self.lbl_kbd.configure(text=f"Скорость клавиатуры: {float(value):.2f} с")

    def _refresh_windows_list(self) -> None:
        try:
            titles = sorted({w.title for w in gw.getAllWindows() if w.title and w.title.strip()})
        except Exception as e:
            self._log(f"Ошибка получения списка окон: {e}")
            titles = []
        if titles:
            self.combo_windows.configure(values=titles)
            # если ничего не выбрано — попробуем найти WMS-окно автоматически
            current = self.combo_windows.get()
            if not current or current == "—":
                wms_default = next((t for t in titles if detect_wms_title(t)), titles[0])
                self.combo_windows.set(wms_default)
        else:
            self.combo_windows.configure(values=["—"])
            self.combo_windows.set("—")

    def _auto_detect(self) -> None:
        self._refresh_windows_list()
        wins = gw.getAllWindows()
        for w in wins:
            if w.title and detect_wms_title(w.title):
                self.combo_windows.set(w.title)
                self.target_title_substring = ""
                self._log(f"🎯 Автодетект: '{w.title}'")
                return
        self._log("🎯 Автодетект: WMS-окно не найдено. Открой терминал и нажми снова.")

    def _open_dock_editor(self) -> None:
        DockEditor(self, self.docks, self._save_docks_from_editor)

    def _save_docks_from_editor(self, new_mapping: dict) -> None:
        self.docks = new_mapping
        save_docks(self.docks)
        self._log(f"📋 Маппинг доков сохранён: {len(self.docks)} записей.")

    def _reset_counter(self) -> None:
        self.cycles_count = 0
        self.errors_count = 0
        self.fallbacks_count = 0
        self.cycle_times.clear()
        self._update_cycles_label()
        self._update_stats()
        self._log("Счётчики сброшены.")

    def _test_screen(self) -> None:
        """Берёт скриншот выбранного окна, OCR-распознавание (если включено)
        и сохраняет результат рядом с exe для диагностики."""
        win = self._find_window_for_test()
        if not win:
            self._log("Тест экрана: окно не найдено. Выбери его в списке.")
            return
        try:
            safe_activate(win)
            time.sleep(0.2)
            bbox = (win.left, win.top, win.right, win.bottom)
            img = ImageGrab.grab(bbox=bbox) if PIL_AVAILABLE else None
            if img is not None:
                img.save(LAST_SCREEN_PNG)
                self._log(f"📷 Скриншот окна сохранён: {LAST_SCREEN_PNG}")
            else:
                self._log("⚠ Pillow не установлен — скриншот недоступен.")
            ocr_text = ""
            if self.var_ocr.get() and PYTESSERACT_AVAILABLE and self.tesseract_path and img is not None:
                try:
                    ocr_text = pytesseract.image_to_string(img, lang="rus+eng")
                except Exception as e:
                    self._log(f"⚠ OCR ошибка: {e}")
            buffer_text = self._read_via_clipboard()
            payload = (
                f"Заголовок окна: {win.title}\n"
                f"Размер: {win.width}x{win.height} @ ({win.left},{win.top})\n"
                f"---- OCR ----\n{ocr_text}\n"
                f"---- БУФЕР ----\n{buffer_text}\n"
            )
            with open(LAST_OCR_TXT, "w", encoding="utf-8") as f:
                f.write(payload)
            self._log(f"📝 OCR/буфер сохранены: {LAST_OCR_TXT}")
        except Exception as e:
            self._log(f"Тест экрана: ошибка {e}")

    def _find_window_for_test(self):
        selected = self.combo_windows.get()
        if not selected or selected == "—":
            return None
        wins = gw.getWindowsWithTitle(selected)
        return wins[0] if wins else None

    # ---------- Hotkey ----------

    def _register_hotkey(self) -> None:
        if not KEYBOARD_AVAILABLE:
            return
        try:
            kb.add_hotkey("space", self._on_space_hotkey)
        except Exception as e:
            self._log(f"⚠ Не удалось зарегистрировать ПРОБЕЛ: {e}")

    def _on_space_hotkey(self) -> None:
        # Игнорируем, если бот сейчас сам что-то печатает (синтетические клики).
        if self._is_typing:
            return
        # Только переключаем Пауза когда бот уже запущен — иначе любая печать
        # пробела в других приложениях случайно запускала бы бота.
        if self.is_running:
            self.pause_toggle()

    # ---------- Управление ----------

    def start(self) -> None:
        if self.is_running and not self.is_paused:
            return
        if self.is_running and self.is_paused:
            # резюм
            self.is_paused = False
            self._set_status("running")
            self.btn_pause.configure(text="⏸ ПАУЗА")
            self._log("▶ Возобновлено.")
            return

        selected = self.combo_windows.get()
        if not selected or selected == "—":
            self._log("❌ Выбери окно WMS из списка или нажми 🎯 Автодетект.")
            return

        # Если выбранный заголовок — кастомный (не из WMS_TITLES), запомним подстроку.
        self.target_title_substring = "" if detect_wms_title(selected) else selected

        self.is_running = True
        self.is_paused = False
        self._stop_event.clear()
        self.btn_start.configure(state="disabled")
        self.btn_pause.configure(state="normal", text="⏸ ПАУЗА")
        self.btn_stop.configure(state="normal")
        self._set_status("running")
        self._last_screen_signature = ""
        self._last_screen_change_ts = time.time()
        self._cycle_start_ts = None
        self._current_cycle = self._fresh_cycle()
        self._log(f"🚀 Запуск. Цель: '{selected}'. OCR: {'ON' if self.var_ocr.get() else 'OFF'}")
        self._thread = threading.Thread(target=self._engine_loop, daemon=True)
        self._thread.start()

    def pause_toggle(self) -> None:
        if not self.is_running:
            return
        self.is_paused = not self.is_paused
        if self.is_paused:
            self._set_status("paused")
            self.btn_pause.configure(text="▶ Продолжить")
            self._log("⏸ Пауза.")
        else:
            self._set_status("running")
            self.btn_pause.configure(text="⏸ ПАУЗА")
            self._log("▶ Возобновлено.")

    def stop(self) -> None:
        if not self.is_running:
            return
        self.is_running = False
        self.is_paused = False
        self._stop_event.set()
        self.btn_start.configure(state="normal")
        self.btn_pause.configure(state="disabled", text="⏸ ПАУЗА")
        self.btn_stop.configure(state="disabled")
        self._set_status("stopped")
        self._log("⏹ Остановлено.")

    def _on_close(self) -> None:
        self.is_running = False
        self._stop_event.set()
        try:
            if KEYBOARD_AVAILABLE:
                kb.unhook_all_hotkeys()
        except Exception:
            pass
        self.destroy()

    # ---------- Низкоуровневые операции ----------

    def _kbd_delay(self) -> float:
        return max(0.01, float(self.var_kbd.get()))

    def _loop_delay(self) -> float:
        return max(0.05, float(self.var_loop.get()))

    def _press(self, key: str) -> None:
        self._is_typing = True
        try:
            pyautogui.press(key)
            time.sleep(self._kbd_delay())
        finally:
            self._is_typing = False

    def _hotkey(self, *keys: str) -> None:
        self._is_typing = True
        try:
            pyautogui.hotkey(*keys)
            time.sleep(self._kbd_delay())
        finally:
            self._is_typing = False

    def _click(self, x: int, y: int) -> None:
        self._is_typing = True
        try:
            pyautogui.click(x, y)
            time.sleep(self._kbd_delay())
        finally:
            self._is_typing = False

    def _paste(self, text: str) -> None:
        self._is_typing = True
        try:
            pyperclip.copy(text)
            time.sleep(self._kbd_delay() * 0.5)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(self._kbd_delay())
        finally:
            self._is_typing = False

    def _read_via_clipboard(self) -> str:
        """Универсальное чтение содержимого текущего фокуса через буфер."""
        self._is_typing = True
        try:
            pyperclip.copy("")
            time.sleep(self._kbd_delay() * 0.3)
            pyautogui.hotkey("ctrl", "a")
            time.sleep(self._kbd_delay() * 0.3)
            pyautogui.hotkey("ctrl", "c")
            time.sleep(self._kbd_delay() * 0.5)
            return pyperclip.paste().strip()
        except Exception:
            return ""
        finally:
            self._is_typing = False

    def _ocr_window(self, win) -> str:
        if not (self.var_ocr.get() and PYTESSERACT_AVAILABLE
                and self.tesseract_path and PIL_AVAILABLE):
            return ""
        try:
            bbox = (win.left, win.top, win.right, win.bottom)
            if bbox[2] - bbox[0] <= 0 or bbox[3] - bbox[1] <= 0:
                return ""
            img = ImageGrab.grab(bbox=bbox)
            return pytesseract.image_to_string(img, lang="rus+eng")
        except Exception as e:
            self._log_thread(f"⚠ OCR ошибка: {e}")
            return ""

    # ---------- Поиск целевого окна WMS ----------

    def _find_target_window(self):
        """Перебирает все видимые окна и возвращает первое, чей заголовок
        матчится с одним из известных WMS-заголовков. Это и есть фикс
        главного бага — бот следует за сменой диалогов."""
        try:
            wins = gw.getAllWindows()
        except Exception:
            wins = []
        # 1) известные WMS-окна
        for w in wins:
            if w.title and detect_wms_title(w.title):
                return w, detect_wms_title(w.title)
        # 2) кастомная подстрока, если задана пользователем
        if self.target_title_substring:
            sub = self.target_title_substring.lower()
            for w in wins:
                if w.title and sub in w.title.lower():
                    return w, w.title
        return None, None

    # ---------- Логика по экранам ----------

    @staticmethod
    def _fresh_cycle() -> dict:
        return {"pallet": "", "box": "", "zone": "", "code": "", "error": ""}

    def _extract_value(self, win, field_label: str) -> str:
        """Достаёт значение поля по подписи. Если OCR — то по тексту,
        иначе через Tab навигацию и буфер обмена."""
        # 1) OCR
        ocr_text = self._ocr_window(win)
        if ocr_text:
            patterns = [
                rf"{field_label}\s*[:.]?\s*([A-ZА-Я0-9\-]+)",
                rf"{field_label}\s*\n\s*([A-ZА-Я0-9\-]+)",
            ]
            for pat in patterns:
                m = re.search(pat, ocr_text, re.IGNORECASE)
                if m:
                    return m.group(1).strip().upper()
        # 2) Fallback через Tab/буфер: предполагаем что фокус сейчас в Контроль,
        # Shift+Tab возвращает на предыдущее поле (источник).
        try:
            self._is_typing = True
            pyautogui.hotkey("shift", "tab")
            time.sleep(self._kbd_delay() * 0.5)
            pyautogui.hotkey("ctrl", "a")
            time.sleep(self._kbd_delay() * 0.3)
            pyautogui.hotkey("ctrl", "c")
            time.sleep(self._kbd_delay() * 0.5)
            val = pyperclip.paste().strip()
            # вернуться на Контроль
            pyautogui.press("tab")
            time.sleep(self._kbd_delay() * 0.5)
            return re.sub(r"\s+", "", val).upper() if val else ""
        except Exception:
            return ""
        finally:
            self._is_typing = False

    def _extract_zone(self, win) -> str:
        ocr_text = self._ocr_window(win)
        if ocr_text:
            patterns = [
                r"Зона\s*[:.]?\s*([^\n\r]+)",
                r"Назначение[^:\n]*:\s*Зона[:.]?\s*([^\n\r]+)",
                r"в\s+Зона[:.]?\s*([^\n\r]+)",
                r"Дока?\s+([А-Яа-я][^\n\r]+)",
            ]
            for pat in patterns:
                m = re.search(pat, ocr_text)
                if m:
                    return m.group(1).strip(" .,;\u00A0").lower()
        # без OCR — пусто, бот применит UNIVERSAL_CELL
        return ""

    def _resolve_dock_code(self, zone_text: str) -> tuple[str, bool]:
        """Вернёт (код, использован_ли_фоллбек)."""
        if not zone_text:
            return UNIVERSAL_CELL, True
        zone_lower = zone_text.lower()
        for key, code in self.docks.items():
            if key in zone_lower:
                return code, False
        return UNIVERSAL_CELL, True

    def _fill_control_and_submit(self, value: str) -> None:
        """Считаем что фокус уже в Контроль (так дизайнят дизайны WinForms-диалоги).
        Чистим поле и вставляем значение, затем Enter."""
        self._hotkey("ctrl", "a")
        self._press("backspace")
        self._paste(value)
        self._press("enter")

    def _check_error_popup(self, win) -> bool:
        """Если на экране попап ошибки — закрыть Enter-ом и пометить флаг
        fallback_active. Возвращает True если был обнаружен попап."""
        ocr_text = self._ocr_window(win)
        text = ocr_text.lower() if ocr_text else ""
        if not text:
            # без OCR попап не отлавливаем, но и не блокируем
            return False
        if any(marker in text for marker in ERROR_MARKERS):
            self._log_thread(f"⚠ Попап ошибки: '{text[:60].strip()}…' → Enter, фоллбек.")
            self.errors_count += 1
            self.fallback_active = True
            self._update_stats()
            self._press("enter")
            return True
        return False

    # ---------- Главный цикл ----------

    def _engine_loop(self) -> None:
        loop_delay = self._loop_delay()
        while self.is_running and not self._stop_event.is_set():
            # пауза
            if self.is_paused:
                time.sleep(0.15)
                continue

            # обновляем delays на каждой итерации (юзер мог подтянуть слайдер)
            loop_delay = self._loop_delay()

            win, wms_title = self._find_target_window()
            if win is None:
                self._log_thread("⚠ WMS-окно не найдено. Жду 1с…")
                self._tick_watchdog("")
                time.sleep(1.0)
                continue

            if not safe_activate(win):
                self._log_thread(f"⚠ Не удалось активировать окно '{win.title}'.")
                time.sleep(0.5)
                continue
            time.sleep(self._kbd_delay() * 0.5)

            # сигнатура экрана для watchdog: title + первые 80 символов содержимого
            content = self._ocr_window(win) or self._read_via_clipboard()
            signature = f"{wms_title}|{content[:80].strip()}"
            self._tick_watchdog(signature)

            try:
                self._dispatch_screen(win, wms_title or win.title)
            except Exception as e:
                self._log_thread(f"⚠ Исключение в обработке экрана: {e}")
                self.errors_count += 1
                self._update_stats()

            time.sleep(loop_delay)

        self._log_thread("Поток бота завершён.")

    def _dispatch_screen(self, win, title: str) -> None:
        # 0) попап ошибки — приоритет
        if self._check_error_popup(win):
            return

        if "Главное меню" in title:
            self._log_thread("📺 Главное меню → F2 (Запросить работу)")
            if self._cycle_start_ts is None:
                self._cycle_start_ts = time.time()
            self._press("f2")
            return

        if "Взятие работы" in title:
            self._log_thread("📺 Взятие работы → F2")
            self._press("f2")
            return

        if "Выбор работ" in title:
            self._log_thread("📺 Выбор работ → Enter (Ок)")
            self._press("enter")
            return

        if "Перемещение к источнику" in title:
            val = self._extract_value(win, "Место")
            if not val:
                self._log_thread("⚠ Не получилось извлечь Место — Enter без значения.")
                self._press("enter")
                return
            self._log_thread(f"📺 Перемещение → Место={val}")
            self._fill_control_and_submit(val)
            return

        if "Поиск паллеты" in title:
            val = self._extract_value(win, "Паллета")
            if not val:
                self._log_thread("⚠ Не получилось извлечь Паллета — Enter.")
                self._press("enter")
                return
            self._current_cycle["pallet"] = val
            self._log_thread(f"📺 Паллета → {val}")
            self._fill_control_and_submit(val)
            return

        if "Поиск коробки" in title:
            val = self._extract_value(win, "Коробка")
            if not val:
                self._log_thread("⚠ Не получилось извлечь Коробка — Enter.")
                self._press("enter")
                return
            self._current_cycle["box"] = val
            self._log_thread(f"📺 Коробка → {val}")
            self._fill_control_and_submit(val)
            return

        if "Поиск места" in title:  # ловит и "Поиск места-приёмника", и без ё
            if self.fallback_active:
                code, used_fb = UNIVERSAL_CELL, True
                self.fallback_active = False
                zone_text = "(аварийный фоллбек)"
            else:
                zone_text = self._extract_zone(win)
                code, used_fb = self._resolve_dock_code(zone_text)
            if used_fb:
                self.fallbacks_count += 1
            self._current_cycle["zone"] = zone_text
            self._current_cycle["code"] = code
            self._log_thread(f"📺 Место-приёмник → Зона='{zone_text}' → {code}")
            self._fill_control_and_submit(code)
            self._update_stats()
            return

        if "Размещение в место" in title:
            self._log_thread("📺 Размещение → Enter ✔ цикл завершён")
            self._press("enter")
            self._on_cycle_complete()
            return

        # неопознанный экран — на всякий случай Enter
        self._log_thread(f"❓ Неопознанный экран '{title}' → Enter")
        self._press("enter")

    def _on_cycle_complete(self) -> None:
        self.cycles_count += 1
        duration = None
        if self._cycle_start_ts is not None:
            duration = time.time() - self._cycle_start_ts
            self.cycle_times.append(duration)
        self._cycle_start_ts = time.time()

        self._update_cycles_label()
        self._update_stats()

        # CSV
        try:
            is_new = not CYCLES_CSV.exists()
            with open(CYCLES_CSV, "a", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                if is_new:
                    w.writerow(["timestamp", "duration_sec", "pallet",
                                "box", "zone", "code"])
                w.writerow([
                    datetime.now().isoformat(timespec="seconds"),
                    f"{duration:.2f}" if duration is not None else "",
                    self._current_cycle.get("pallet", ""),
                    self._current_cycle.get("box", ""),
                    self._current_cycle.get("zone", ""),
                    self._current_cycle.get("code", ""),
                ])
        except Exception as e:
            self._log_thread(f"⚠ Не удалось записать CSV: {e}")
        self._current_cycle = self._fresh_cycle()

    # ---------- Watchdog ----------

    def _tick_watchdog(self, signature: str) -> None:
        if signature and signature != self._last_screen_signature:
            self._last_screen_signature = signature
            self._last_screen_change_ts = time.time()
            return
        if not self.is_running or self.is_paused:
            return
        if time.time() - self._last_screen_change_ts > WATCHDOG_SECONDS:
            self._log_thread(
                f"⚠ Watchdog: экран не меняется {WATCHDOG_SECONDS:.0f}с. "
                "Ставлю на паузу — проверь WMS.")
            self.after(0, self._watchdog_pause)
            # сбросим таймер чтобы не спамить
            self._last_screen_change_ts = time.time()

    def _watchdog_pause(self) -> None:
        if self.is_running and not self.is_paused:
            self.pause_toggle()


def main() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = WMSBot()
    app.mainloop()


if __name__ == "__main__":
    main()
