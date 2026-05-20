import threading
import time
import re
import os
import customtkinter as ctk
import pyautogui
import pyperclip
import pygetwindow as gw
from PIL import ImageGrab
import numpy as np

# Пытаемся импортировать EasyOCR для точного чтения экрана
try:
    import easyocr
    # Инициализируем распознаватель для русского и английского языков
    reader = easyocr.Reader(['ru', 'en'], gpu=False)
    OCR_AVAILABLE = True
except Exception:
    OCR_AVAILABLE = False

# --- НАСТРОЙКИ UI ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# --- ТАБЛИЦА МАСШТАБИРОВАНИЯ ДОКОВ (СКРИН 9) ---
DOCK_MAPPING = {
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
    "центр": "D-CNTR-2-1"
}

UNIVERSAL_CELL = "D-KM-1"

class WMSPerfectBot(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WMS Ultimate Bot v5.0 🤖")
        self.geometry("600x650")
        self.resizable(False, False)

        self.is_running = False
        self.target_window_title = None
        self.cycles_count = 0
        self.error_fallback = False  # Переключение на D-KM-1 при ошибке
        self.adaptation_mode = True
        self.start_time = 0

        self.setup_ui()
        self.refresh_windows_list()

    def setup_ui(self):
        self.header = ctk.CTkLabel(self, text="⚡ WMS Из Полноценного Цикла v5.0", font=("Arial", 20, "bold"), text_color="#00BFFF")
        self.header.pack(pady=(15, 5))

        self.metrics_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=12)
        self.metrics_frame.pack(pady=10, padx=20, fill="x")

        self.lbl_cycles = ctk.CTkLabel(self.metrics_frame, text="🔁 Выполнено кругов: 0", font=("Arial", 14, "bold"))
        self.lbl_cycles.grid(row=0, column=0, padx=20, pady=8, sticky="w")

        self.lbl_status = ctk.CTkLabel(self.metrics_frame, text="Статус: ⏸ Пауза", font=("Arial", 14, "bold"), text_color="gray")
        self.lbl_status.grid(row=0, column=1, padx=20, pady=8, sticky="e")

        self.win_frame = ctk.CTkFrame(self, fg_color="#232323", corner_radius=12)
        self.win_frame.pack(pady=10, padx=20, fill="x")

        self.lbl_choose = ctk.CTkLabel(self.win_frame, text="Выберите окно терминала WMS:", font=("Arial", 12, "bold"))
        self.lbl_choose.pack(pady=(8, 2), padx=15, anchor="w")

        self.combo_windows = ctk.CTkComboBox(self.win_frame, width=400)
        self.combo_windows.pack(side="left", padx=(15, 10), pady=(0, 15))

        self.btn_refresh = ctk.CTkButton(self.win_frame, text="🔄 Обновить", width=100, fg_color="#6c757d", hover_color="#5a6268", command=self.refresh_windows_list)
        self.btn_refresh.pack(side="left", padx=(0, 15), pady=(0, 15))

        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=10)

        self.btn_start = ctk.CTkButton(self.btn_frame, text="▶ ЗАПУСТИТЬ БОТА", fg_color="#28a745", hover_color="#218838", 
                                       font=("Arial", 14, "bold"), width=220, height=40, command=self.start_bot)
        self.btn_start.grid(row=0, column=0, padx=10)

        self.btn_stop = ctk.CTkButton(self.btn_frame, text="⏹ ОСТАНОВИТЬ", fg_color="#dc3545", hover_color="#c82333", 
                                      font=("Arial", 14, "bold"), width=220, height=40, state="disabled", command=self.stop_bot)
        self.btn_stop.grid(row=0, column=1, padx=10)

        self.log_box = ctk.CTkTextbox(self, width=550, height=260, corner_radius=10, font=("Consolas", 11))
        self.log_box.pack(pady=15)
        
        if OCR_AVAILABLE:
            self.log("Система EasyOCR успешно подключена. Готова распознавать текст.")
        else:
            self.log("⚠️ Внимание: Модуль EasyOCR загружается. Сборка адаптирована.")

    def log(self, text):
        self.log_box.insert("end", f"> {text}\n")
        self.log_box.see("end")

    def refresh_windows_list(self):
        try:
            titles = [w.title for w in gw.getAllWindows() if w.title.strip()]
            titles = sorted(list(set(titles)))
            if titles:
                self.combo_windows.configure(values=titles)
                self.combo_windows.set(titles[0])
            else:
                self.combo_windows.configure(values=["Окна не найдены"])
        except Exception as e:
            self.log(f"Ошибка поиска окон: {e}")

    def start_bot(self):
        selected = self.combo_windows.get()
        if not selected or selected in ["Окна не найдены"]:
            self.log("❌ Сначала выберите окно терминала!")
            return

        self.target_window_title = selected
        self.is_running = True
        self.start_time = time.time()
        self.btn_start.configure(state="disabled")
        self.btn_refresh.configure(state="disabled")
        self.combo_windows.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.lbl_status.configure(text="Статус: ▶ РАБОТАЕТ", text_color="#28a745")
        self.log(f"🚀 Старт сканирования всех 12 шагов для окна: '{self.target_window_title}'")
        threading.Thread(target=self.bot_engine, daemon=True).start()

    def stop_bot(self):
        self.is_running = False
        self.btn_start.configure(state="normal")
        self.btn_refresh.configure(state="normal")
        self.combo_windows.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.lbl_status.configure(text="Статус: ⏸ ПАУЗА", text_color="#dc3545")

    def get_screen_text_by_ocr(self, win):
        """Делает скриншот окна и распознает текст оптически с разделением по строкам"""
        try:
            left, top, right, bottom = win.left, win.top, win.right, win.bottom
            if right - left <= 0 or bottom - top <= 0:
                return []
            
            # Захват картинки окна
            screenshot = ImageGrab.grab(bbox=(left, top, right, bottom))
            img_np = np.array(screenshot)
            
            if OCR_AVAILABLE:
                # Читаем картинку через EasyOCR
                results = reader.readtext(img_np, detail=0)
                return [line.lower().strip() for line in results if line.strip()]
            else:
                # Резервный буферный метод, если библиотека еще не инициализирована
                pyperclip.copy("")
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.04)
                pyautogui.hotkey('ctrl', 'c')
                return [line.lower().strip() for line in pyperclip.paste().split('\n') if line.strip()]
        except Exception:
            return []

    def focus_and_input(self, win, text_data):
        """Адаптивный ввод в активное поле 'Контроль'"""
        try:
            if time.time() - self.start_time < 10:
                # Первые 10 секунд кликаем в нижнюю треть (настройка под мышку)
                cx = win.left + (win.width // 2)
                cy = win.top + int(win.height * 0.73)
                pyautogui.click(cx, cy)
                time.sleep(0.05)
            else:
                # Затем используем мгновенный слепой фокус
                pyautogui.press('tab')

            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('backspace')
            time.sleep(0.02)
            
            # Пишем через буфер (чтобы не путать раскладку)
            pyperclip.copy(text_data)
            time.sleep(0.02)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.04)
            pyautogui.press('enter')
        except Exception as e:
            self.log(f"Ошибка ввода: {e}")

    def extract_code_after_keyword(self, lines, keyword):
        """Ищет строку со словом (место, паллета, коробка) и вытягивает код после него"""
        for line in lines:
            if keyword in line:
                # Ищем штрихкоды, номера ячеек (цифры, буквы, дефисы)
                match = re.search(r'(?:' + keyword + r'[:\s]+)([a-zA-Z0-9\-_\s]+)', line)
                if match:
                    res = match.group(1).strip().upper()
                    # Убираем лишние пробелы
                    return res.replace(" ", "")
                
                # Дополнительная проверка на поиск кода в следующей строке
                idx = lines.index(line)
                if idx + 1 < len(lines):
                    next_line = lines[idx + 1].strip().upper()
                    if len(next_line) > 2:
                        return next_line.replace(" ", "")
        return None

    def bot_engine(self):
        while self.is_running:
            wins = gw.getWindowsWithTitle(self.target_window_title)
            if not wins:
                time.sleep(1)
                continue
            
            win = wins[0]
            if win.isMinimized:
                win.restore()
            win.activate()
            
            # Читаем строки с экрана через OCR
            lines = self.get_screen_text_by_ocr(win)
            full_text = " ".join(lines)

            if not lines:
                time.sleep(0.5)
                continue

            # --- ПРОВЕРКА СКРИНА ОШИБКИ И СБОЕВ ---
            if any(err in full_text for err in ["не найден", "не существует", "не зарегистрирован", "ошибка"]):
                self.log("⚠️ Обнаружен экран ошибки! Нажимаю OK (Enter) и включаю аварийный D-KM-1...")
                pyautogui.press('enter')
                self.error_fallback = True
                time.sleep(0.5)
                continue

            # --- КАРТА ВСЕХ 12 ШАГОВ (ВХОД С ЛЮБОГО МЕСТА) ---

            # [Скрин 1-2] Главное меню или Окно "Взять работу"
            if "запросить работу" in full_text or "взять работу" in full_text or "главное меню" in full_text:
                self.log("[Шаг 1-2] Вижу меню запроса работы. Нажимаю Запросить/Взять работу (F2/Клик)...")
                cx = win.left + (win.width // 2)
                cy = win.top + (win.height // 2)
                pyautogui.click(cx, cy)
                pyautogui.press('f2')
                time.sleep(0.6)

            # [Скрин 3-4] Переместитесь к МЕСТУ
            elif "место" in full_text and "контроль" in full_text:
                self.log("[Шаг 3-4] Экран: [МЕСТО]. Извлекаю код ячейки...")
                code = self.extract_code_after_keyword(lines, "место")
                if code:
                    self.log(f"Успешно считано Место: {code} -> Вставляю в Контроль")
                    self.focus_and_input(win, code)
                else:
                    pyautogui.press('enter')

            # [Скрин 5-6] Возьмите ПАЛЛЕТУ
            elif "палет" in full_text or "контейнер" in full_text:
                self.log("[Шаг 5-6] Экран: [ПАЛЛЕТА]. Извлекаю код паллеты...")
                code = self.extract_code_after_keyword(lines, "палет")
                if not code:
                    code = self.extract_code_after_keyword(lines, "место") # Ищем код контейнера
                
                if code:
                    self.log(f"Успешно считана Паллета: {code} -> Вставляю в Контроль")
                    self.focus_and_input(win, code)
                else:
                    pyautogui.press('enter')

            # [Скрин 7-8] Возьмите КОРОБКУ
            elif "коробк" in full_text and not "размещение" in full_text:
                self.log("[Шаг 7-8] Экран: [КОРОБКА]. Извлекаю штрихкод коробки...")
                code = self.extract_code_after_keyword(lines, "коробк")
                if code:
                    self.log(f"Успешно считана Коробка: {code} -> Вставляю в Контроль")
                    self.focus_and_input(win, code)
                else:
                    pyautogui.press('enter')

            # [Скрин 9] Укажите коды места зоны / ДОК НАЗНАЧЕНИЯ
            elif "док" in full_text or "зона" in full_text or "назначение" in full_text:
                self.log("[Шаг 9] Экран: [ДОК НАЗНАЧЕНИЯ]")
                
                # Если до этого вылетала ошибка или включен принудительный сброс
                if self.error_fallback:
                    self.log(f"Сработала защита от ошибок. Применяю супер-ячейку: {UNIVERSAL_CELL}")
                    self.focus_and_input(win, UNIVERSAL_CELL)
                    self.error_fallback = False
                else:
                    # Ищем город дока на экране
                    target_code = UNIVERSAL_CELL
                    for city_name, code_val in DOCK_MAPPING.items():
                        if city_name in full_text:
                            self.log(f"EasyOCR определил Док: {city_name.upper()}")
                            target_code = code_val
                            break
                    
                    self.log(f"Вставляю код дока: {target_code}")
                    self.focus_and_input(win, target_code)

            # [Скрин 10-11] Размещение в место (Подтверждение)
            elif "размещение в место" in full_text:
                self.log("[Шаг 10-11] Подтверждаю размещение коробки на место по Enter.")
                pyautogui.press('enter')
                self.cycles_count += 1
                self.lbl_cycles.configure(text=f"Выполнено кругов: {self.cycles_count}")
                self.error_fallback = False
                time.sleep(0.5)

            # [Скрин 12] Финал (Коробок не осталось, последняя коробка)
            elif "последн" in full_text or "осталось" in full_text or "заверш" in full_text:
                self.log("[Шаг 12] Последняя коробка в цикле! Жестко ставим аварийный D-KM-1")
                self.focus_and_input(win, UNIVERSAL_CELL)
                time.sleep(0.5)

            else:
                # Если экран неочевидный, даем легкий Enter, чтобы продвинуть процесс
                pyautogui.press('enter')

            time.sleep(0.8) # Интервал «взгляда» робота на экран

if __name__ == "__main__":
    app = WMSPerfectBot()
    app.mainloop()
