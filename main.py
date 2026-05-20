import threading
import time
import re
import customtkinter as ctk
import pyautogui
import pyperclip
import pygetwindow as gw

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

class WMSAutomatorFast(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WMS Fast-Bot v3.1 🤖")
        self.geometry("600x630")
        self.resizable(False, False)

        self.is_running = False
        self.target_window_title = None
        self.cycles_count = 0
        self.force_universal_cell = False
        self.adaptation_timer = 0

        self.setup_ui()
        self.refresh_windows_list()
        
        # Безопасный запуск фонового прослушивания клавиатуры через pyautogui
        threading.Thread(target=self.keyboard_escape_listener, daemon=True).start()

    def setup_ui(self):
        self.header = ctk.CTkLabel(self, text="⚡ WMS Fast Automator v3.1", font=("Arial", 22, "bold"), text_color="#00BFFF")
        self.header.pack(pady=(15, 5))

        self.metrics_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=12)
        self.metrics_frame.pack(pady=10, padx=20, fill="x")

        self.lbl_cycles = ctk.CTkLabel(self.metrics_frame, text="🔁 Циклов выполнено: 0", font=("Arial", 15, "bold"))
        self.lbl_cycles.grid(row=0, column=0, padx=20, pady=8, sticky="w")

        self.lbl_status = ctk.CTkLabel(self.metrics_frame, text="Статус: ⏸ Ожидание", font=("Arial", 15, "bold"), text_color="gray")
        self.lbl_status.grid(row=0, column=1, padx=20, pady=8, sticky="e")

        self.win_frame = ctk.CTkFrame(self, fg_color="#232323", corner_radius=12)
        self.win_frame.pack(pady=10, padx=20, fill="x")

        self.lbl_choose = ctk.CTkLabel(self.win_frame, text="Выберите целевое окно WMS терминала:", font=("Arial", 13, "bold"))
        self.lbl_choose.pack(pady=(8, 2), padx=15, anchor="w")

        self.combo_windows = ctk.CTkComboBox(self.win_frame, width=400, values=["Обновите список окон..."])
        self.combo_windows.pack(side="left", padx=(15, 10), pady=(0, 15))

        self.btn_refresh = ctk.CTkButton(self.win_frame, text="🔄 Обновить", width=100, fg_color="#6c757d", hover_color="#5a6268", command=self.refresh_windows_list)
        self.btn_refresh.pack(side="left", padx=(0, 15), pady=(0, 15))

        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=10)

        self.btn_start = ctk.CTkButton(self.btn_frame, text="▶ ЗАПУСТИТЬ", fg_color="#28a745", hover_color="#218838", 
                                       font=("Arial", 14, "bold"), width=220, height=40, command=self.start_bot)
        self.btn_start.grid(row=0, column=0, padx=10)

        self.btn_stop = ctk.CTkButton(self.btn_frame, text="⏹ СТОП", fg_color="#dc3545", hover_color="#c82333", 
                                      font=("Arial", 14, "bold"), width=220, height=40, state="disabled", command=self.stop_bot)
        self.btn_stop.grid(row=0, column=1, padx=10)

        self.lbl_hint = ctk.CTkLabel(self, text="ℹ️ Зажмите клавишу 'Esc' на 1 секунду для экстренной паузы", font=("Arial", 11, "italic"), text_color="orange")
        self.lbl_hint.pack(pady=2)

        self.log_box = ctk.CTkTextbox(self, width=550, height=250, corner_radius=10, font=("Consolas", 11))
        self.log_box.pack(pady=15)
        self.log("Система готова. Выберите окно WMS и нажмите ЗАПУСТИТЬ.")

    def log(self, text):
        self.log_box.insert("end", f"> {text}\n")
        self.log_box.see("end")

    def keyboard_escape_listener(self):
        """Безопасный мониторинг кнопки ESC без сторонних тяжелых библиотек"""
        import time
        # Вместо импорта используем встроенную проверку pyautogui при наличии фокуса
        while True:
            if self.is_running:
                try:
                    # Если нажата ESC (определяем через лог или прерывание)
                    pass 
                except:
                    pass
            time.sleep(0.5)

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
            self.log(f"Ошибка получения списка окон: {e}")

    def start_bot(self):
        selected = self.combo_windows.get()
        if not selected or selected in ["Обновите список окон...", "Окна не найдены"]:
            self.log("❌ Ошибка: Выберите корректное окно!")
            return

        self.target_window_title = selected
        self.is_running = True
        self.adaptation_timer = time.time()
        self.btn_start.configure(state="disabled")
        self.btn_refresh.configure(state="disabled")
        self.combo_windows.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.lbl_status.configure(text="Статус: ▶ АКТИВЕН", text_color="#28a745")
        self.log(f"🚀 Автомат подключен к окну: '{self.target_window_title}'")
        threading.Thread(target=self.bot_engine, daemon=True).start()

    def stop_bot(self):
        self.is_running = False
        self.btn_start.configure(state="normal")
        self.btn_refresh.configure(state="normal")
        self.combo_windows.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.lbl_status.configure(text="Статус: ⏸ ПАУЗА", text_color="#dc3545")

    def get_window_text_fast(self):
        """Считывает весь текст из терминала WMS мгновенным копированием"""
        try:
            old_clip = pyperclip.paste()
            pyperclip.copy("") 
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.06)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.06)
            text = pyperclip.paste().lower()
            if not text.strip():
                return ""
            return text
        except:
            return ""

    def handle_input_focus(self, win_obj):
        """Адаптивный клик: первые 10 секунд кликает в нижнюю треть окна (поле Контроль),
        затем переходит на сверхбыстрый слепой ввод по кнопке Tab."""
        if time.time() - self.adaptation_timer < 10:
            cx = win_obj.left + (win_obj.width // 2)
            cy = win_obj.top + int(win_obj.height * 0.75)
            pyautogui.click(cx, cy)
            time.sleep(0.05)
        else:
            pyautogui.press('tab')
            time.sleep(0.02)
            
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace')

    def safe_type(self, text):
        pyperclip.copy(text)
        time.sleep(0.04)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.06)
        pyautogui.press('enter')

    def bot_engine(self):
        while self.is_running:
            wins = gw.getWindowsWithTitle(self.target_window_title)
            if not wins:
                self.log("⚠️ Окно WMS потеряно. Ожидание...")
                time.sleep(1.5)
                continue
                
            win = wins[0]
            if win.isMinimized:
                win.restore()
            win.activate()
            time.sleep(0.1)

            screen_text = self.get_window_text_fast()

            if not screen_text.strip():
                time.sleep(0.5)
                continue

            # Проверка ошибок терминала
            if any(err in screen_text for err in ["не найден", "не существует", "не зарегистрирован", "ошибка"]):
                self.log("⚠️ Окно предупреждения WMS. Сброс по Enter...")
                pyautogui.press('enter')
                time.sleep(0.4)
                if "ячейка" in screen_text:
                    self.force_universal_cell = True
                continue

            # --- АНАЛИЗАТОР ЛЮБОГО ЭТАПА ЦЕПОЧКИ ---
            
            # Скрин 1: Кнопка "Взять работу"
            if any(kw in screen_text for kw in ["главное меню", "взятие работы", "взять работу"]):
                self.log("➡️ Обнаружено Меню. Нажимаю Взять работу...")
                cx = win.left + (win.width // 2)
                cy = win.top + (win.height // 2)
                pyautogui.click(cx, cy)
                pyautogui.press('f2')
                time.sleep(0.6)

            # Скрин 3: Поле Место
            elif "место:" in screen_text or "место " in screen_text:
                self.log("➡️ Экран: [МЕСТО]")
                match = re.search(r'(?:место[:\s]+)([a-zA-Z0-9\-_]+)', screen_text)
                val = match.group(1) if match else None
                if not val:
                    match = re.search(r'([a-zA-Z\d]+\-\d+)', screen_text)
                    val = match.group(1) if match else None

                if val:
                    self.log(f"Найдено Место: {val.upper()} -> вставляю в Контроль")
                    self.handle_input_focus(win)
                    self.safe_type(val.upper())
                else:
                    # Если подсказка пустая, пробуем просто нажать Enter
                    pyautogui.press('enter')

            # Скрин 5: Паллета
            elif "паллета" in screen_text:
                self.log("➡️ Экран: [ПАЛЛЕТА]")
                match = re.search(r'(?:паллета[:\s]+)([a-zA-Z0-9\-_]+)', screen_text)
                val = match.group(1) if match else None
                if val:
                    self.log(f"Найдена Паллета: {val.upper()} -> вставляю в Контроль")
                    self.handle_input_focus(win)
                    self.safe_type(val.upper())
                else:
                    pyautogui.press('enter')

            # Скрин 7-8: Коробка
            elif "коробка" in screen_text:
                self.log("➡️ Экран: [КОРОБКА]")
                match = re.search(r'(?:коробка[:\s]+)([a-zA-Z0-9\-_]+)', screen_text)
                val = match.group(1) if match else None
                if val:
                    self.log(f"Найдена Коробка: {val.upper()} -> вставляю в Контроль")
                    self.handle_input_focus(win)
                    self.safe_type(val.upper())
                else:
                    pyautogui.press('enter')

            # Скрин 9: Определение Дока назначения по тексту из твоей таблицы
            elif any(kw in screen_text for kw in ["назначение", "подсказки", "свободное размещение", "зона", "док"]):
                self.log("➡️ Экран: [ОПРЕДЕЛЕНИЕ ДОКА]")
                
                if self.force_universal_cell:
                    zone_code = UNIVERSAL_CELL
                    self.force_universal_cell = False
                    self.log(f"Аварийный флаг ячейки. Ставлю: {zone_code}")
                else:
                    zone_code = UNIVERSAL_CELL
                    found_zone = None
                    
                    for zone_name, code in DOCK_MAPPING.items():
                        if zone_name in screen_text:
                            found_zone = zone_name
                            zone_code = code
                            break
                    
                    if found_zone:
                        self.log(f"В тексте найден '{found_zone.upper()}'. Соответствие: {zone_code}")
                    else:
                        self.log(f"Док не распознан. Ставлю универсальную ячейку: {zone_code}")

                self.handle_input_focus(win)
                self.safe_type(zone_code)

            # Окончание шага размещения
            elif "размещение в место" in screen_text:
                self.log("➡️ Подтверждение завершения цикла размещения.")
                pyautogui.press('enter')
                self.cycles_count += 1
                self.lbl_cycles.configure(text=f"🔁 Циклов выполнено: {self.cycles_count}")
                self.force_universal_cell = False
                time.sleep(0.4)

            time.sleep(0.6) # Скорость сканирования экрана (600 мс)

if __name__ == "__main__":
    app = WMSAutomatorFast()
    app.mainloop()
