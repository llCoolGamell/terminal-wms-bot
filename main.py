import threading
import time
import re
import customtkinter as ctk
import pyautogui
import pyperclip
import pygetwindow as gw

# --- НАСТРОЙКИ ИНТЕРФЕЙСА ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# --- ТАБЛИЦА СООТВЕТСТВИЯ ДОКОВ (ДЛЯ ЭКРАНА 9) ---
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

class WMSUniversalLoopBot(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WMS Loop-Bot v4.0 🤖")
        self.geometry("600x640")
        self.resizable(False, False)

        self.is_running = False
        self.target_window_title = None
        self.cycles_count = 0
        self.force_universal_cell = False
        self.start_time = 0

        self.setup_ui()
        self.refresh_windows_list()

    def setup_ui(self):
        self.header = ctk.CTkLabel(self, text="⚡ WMS Universal Loop Automator v4.0", font=("Arial", 20, "bold"), text_color="#00BFFF")
        self.header.pack(pady=(15, 5))

        self.metrics_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=12)
        self.metrics_frame.pack(pady=10, padx=20, fill="x")

        self.lbl_cycles = ctk.CTkLabel(self.metrics_frame, text="🔁 Успешных циклов: 0", font=("Arial", 14, "bold"))
        self.lbl_cycles.grid(row=0, column=0, padx=20, pady=8, sticky="w")

        self.lbl_status = ctk.CTkLabel(self.metrics_frame, text="Статус: ⏸ Ожидание", font=("Arial", 14, "bold"), text_color="gray")
        self.lbl_status.grid(row=0, column=1, padx=20, pady=8, sticky="e")

        self.win_frame = ctk.CTkFrame(self, fg_color="#232323", corner_radius=12)
        self.win_frame.pack(pady=10, padx=20, fill="x")

        self.lbl_choose = ctk.CTkLabel(self.win_frame, text="Выберите запущенное окно WMS:", font=("Arial", 12, "bold"))
        self.lbl_choose.pack(pady=(8, 2), padx=15, anchor="w")

        self.combo_windows = ctk.CTkComboBox(self.win_frame, width=400)
        self.combo_windows.pack(side="left", padx=(15, 10), pady=(0, 15))

        self.btn_refresh = ctk.CTkButton(self.win_frame, text="🔄 Обновить", width=100, fg_color="#6c757d", hover_color="#5a6268", command=self.refresh_windows_list)
        self.btn_refresh.pack(side="left", padx=(0, 15), pady=(0, 15))

        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=10)

        self.btn_start = ctk.CTkButton(self.btn_frame, text="▶ ЗАПУСТИТЬ ЦИКЛ", fg_color="#28a745", hover_color="#218838", 
                                       font=("Arial", 14, "bold"), width=220, height=40, command=self.start_bot)
        self.btn_start.grid(row=0, column=0, padx=10)

        self.btn_stop = ctk.CTkButton(self.btn_frame, text="⏹ ОСТАНОВИТЬ", fg_color="#dc3545", hover_color="#c82333", 
                                      font=("Arial", 14, "bold"), width=220, height=40, state="disabled", command=self.stop_bot)
        self.btn_stop.grid(row=0, column=1, padx=10)

        self.log_box = ctk.CTkTextbox(self, width=550, height=270, corner_radius=10, font=("Consolas", 11))
        self.log_box.pack(pady=15)
        self.log("Интеллектуальная система готова. Бот определит любой экран из 12 автоматически.")

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
            self.log("❌ Ошибка: Выберите корректное окно терминала!")
            return

        self.target_window_title = selected
        self.is_running = True
        self.start_time = time.time()
        self.btn_start.configure(state="disabled")
        self.btn_refresh.configure(state="disabled")
        self.combo_windows.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.lbl_status.configure(text="Статус: ▶ ЦИКЛ АКТИВЕН", text_color="#28a745")
        self.log(f"🚀 Сканатор запущен. Поиск активного шага в окне: '{self.target_window_title}'")
        threading.Thread(target=self.bot_engine, daemon=True).start()

    def stop_bot(self):
        self.is_running = False
        self.btn_start.configure(state="normal")
        self.btn_refresh.configure(state="normal")
        self.combo_windows.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.lbl_status.configure(text="Статус: ⏸ СТОП", text_color="#dc3545")
        self.log("🛑 Робот остановлен пользователем.")

    def get_terminal_screen_text(self):
        """Продвинутый двухэтапный метод захвата текста из защищенных окон WMS"""
        text_content = ""
        try:
            # Метод 1: Прямое системное выделение данных через буфер
            pyperclip.copy("") 
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.05)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.05)
            text_content = pyperclip.paste().lower()
            
            # Метод 2: Если буфер пуст, пробуем альтернативный перехват фокуса
            if not text_content.strip():
                pyautogui.click() # Легкий клик для активации внутренних элементов
                pyautogui.hotkey('ctrl', 'a')
                time.sleep(0.04)
                pyautogui.hotkey('ctrl', 'c')
                text_content = pyperclip.paste().lower()
        except:
            pass
        return text_content

    def enter_data_to_control(self, win_obj, text_to_type):
        """Вбивает данные в поле Контроль. Первые 10 секунд использует физический клик мыши
        для подстройки, затем переходит на слепой мгновенный ввод клавиатурой."""
        try:
            if time.time() - self.start_time < 10:
                # Вариант А: Клик в нижнюю область окна (где находится поле Контроль)
                cx = win_obj.left + (win_obj.width // 2)
                cy = win_obj.top + int(win_obj.height * 0.75)
                pyautogui.click(cx, cy)
                time.sleep(0.05)
            else:
                # Вариант Б: Быстрый переход по Tab без задействования мыши
                pyautogui.press('tab')
                time.sleep(0.02)

            # Очищаем поле
            pyautogui.hotkey('ctrl', 'a')
            pyautogui.press('backspace')
            time.sleep(0.02)
            
            # Вставляем данные и подтверждаем
            pyperclip.copy(text_to_type)
            time.sleep(0.03)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.05)
            pyautogui.press('enter')
        except Exception as e:
            self.log(f"Ошибка ввода данных: {e}")

    def bot_engine(self):
        while self.is_running:
            wins = gw.getWindowsWithTitle(self.target_window_title)
            if not wins:
                self.log("⚠️ Окно WMS не на переднем плане. Ожидание...")
                time.sleep(1.5)
                continue
                
            win = wins[0]
            if win.isMinimized:
                win.restore()
            win.activate()
            time.sleep(0.1)

            # Читаем то, что сейчас находится на экране WMS
            screen_text = self.get_terminal_screen_text()

            if not screen_text.strip():
                # Если текст пустой, посылаем импульсный Enter, чтобы оживить зависший терминал
                pyautogui.press('enter')
                time.sleep(0.8)
                continue

            # Обработка окон всплывающих ошибок (Не найден/Не существует)
            if any(err in screen_text for err in ["не найден", "не существует", "не зарегистрирован", "ошибка"]):
                self.log("⚠️ Обнаружено окно предупреждения! Сбрасываю по Enter...")
                pyautogui.press('enter')
                time.sleep(0.5)
                if "ячейка" in screen_text:
                    self.force_universal_cell = True
                continue

            # =========================================================================
            # ДИНАМИЧЕСКИЙ АНАЛИЗАТОР 12 СКРИНОВ (ВХОД С ЛЮБОЙ ТОЧКИ ЦИКЛА)
            # =========================================================================

            # ШАГ 1: Главное меню / Экран запуска работы
            if any(kw in screen_text for kw in ["главное меню", "взятие работы", "взять работу"]):
                self.log("[Шаг 1] Вижу главное меню. Нажимаю кнопку активации (F2)...")
                cx = win.left + (win.width // 2)
                cy = win.top + (win.height // 2)
                pyautogui.click(cx, cy)
                pyautogui.press('f2')
                time.sleep(0.7)

            # ШАГ 2-3: Сканирование/Проверка поля МЕСТО
            elif "место:" in screen_text or "место " in screen_text:
                self.log("[Шаг 2-3] Окно затребовало МЕСТО. Извлекаю данные...")
                match = re.search(r'(?:место[:\s]+)([a-zA-Z0-9\-_]+)', screen_text)
                val = match.group(1) if match else None
                if not val:
                    match = re.search(r'([a-zA-Z\d]+\-\d+)', screen_text)
                    val = match.group(1) if match else None

                if val:
                    self.log(f"Найдено Место: {val.upper()} -> Копирую в Контроль")
                    self.enter_data_to_control(win, val.upper())
                else:
                    self.log("Подсказка пуста, пробиваю шаг через Enter")
                    pyautogui.press('enter')

            # ШАГ 4-5: Сканирование/Проверка поля ПАЛЛЕТА
            elif "паллета" in screen_text:
                self.log("[Шаг 4-5] Окно затребовало ПАЛЛЕТУ.")
                match = re.search(r'(?:паллета[:\s]+)([a-zA-Z0-9\-_]+)', screen_text)
                val = match.group(1) if match else None
                if val:
                    self.log(f"Найдена Паллета: {val.upper()} -> Копирую в Контроль")
                    self.enter_data_to_control(win, val.upper())
                else:
                    pyautogui.press('enter')

            # ШАГ 6-8: Сканирование/Проверка поля КОРОБКА / ШТРИХКОД ГРУЗА
            elif any(kw in screen_text for kw in ["коробка", "груз", "шб", "штрихкод"]):
                self.log("[Шаг 6-8] Окно затребовало КОРОБКУ/ГРУЗ.")
                match = re.search(r'(?:коробка[:\s]+)([a-zA-Z0-9\-_]+)', screen_text)
                val = match.group(1) if match else None
                if not val:
                    match = re.search(r'(?:груз[:\s]+)([a-zA-Z0-9\-_]+)', screen_text)
                    val = match.group(1) if match else None

                if val:
                    self.log(f"Найдена Коробка: {val.upper()} -> Копирую в Контроль")
                    self.enter_data_to_control(win, val.upper())
                else:
                    pyautogui.press('enter')

            # ШАГ 9: Определение ДОКА НАЗНАЧЕНИЯ (по твоей таблице городов)
            elif any(kw in screen_text for kw in ["назначение", "подсказки", "свободное размещение", "зона", "док"]):
                self.log("[Шаг 9] Окно определения ДОКА НАЗНАЧЕНИЯ.")
                
                if self.force_universal_cell:
                    zone_code = UNIVERSAL_CELL
                    self.force_universal_cell = False
                    self.log(f"Аварийный сброс ячейки. Ставлю: {zone_code}")
                else:
                    zone_code = UNIVERSAL_CELL
                    found_zone = None
                    
                    # Бежим по ключам городов из таблицы соответствия
                    for zone_name, code in DOCK_MAPPING.items():
                        if zone_name in screen_text:
                            found_zone = zone_name
                            zone_code = code
                            break
                    
                    if found_zone:
                        self.log(f"Распознан город '{found_zone.upper()}'. Код Дока: {zone_code}")
                    else:
                        self.log(f"Город не распознан. Ставлю универсальный док: {zone_code}")

                self.enter_data_to_control(win, zone_code)

            # ШАГ 10-12: Финальное подтверждение размещения в ячейку
            elif "размещение в место" in screen_text or "подтвердить" in screen_text:
                self.log("[Шаг 10-12] Финал цикла. Подтверждаю размещение.")
                pyautogui.press('enter')
                self.cycles_count += 1
                self.lbl_cycles.configure(text=f"Успешных циклов: {self.cycles_count}")
                self.force_universal_cell = False
                time.sleep(0.5)
            
            else:
                # Если на экране что-то неизвестное, просто жмем Enter, чтобы двинуть цикл вперед
                pyautogui.press('enter')

            time.sleep(0.6) # Задержка повторного круга сканирования (600 мс)

if __name__ == "__main__":
    app = WMSUniversalLoopBot()
    app.mainloop()
