import threading
import time
import re
import customtkinter as ctk
import pyautogui
import pyperclip
import pygetwindow as gw

# Пытаемся импортировать pywinauto для глубокого чтения окон
try:
    from pywinauto import Application
    PYWINAUTO_AVAILABLE = True
except ImportError:
    PYWINAUTO_AVAILABLE = False

# --- НАСТРОЙКИ UI ---
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# --- МАППИНГ ЗОН (ДОКОВ) ---
DOCK_MAPPING = {
    "док аша дальняя": "D-A-DL-4-2",
    "док миасс": "D-MIASS-1-1",
    "док север 2": "D-SEV2-5-1",
    "док самовывоз": "D-PICKUP",
    "док вип": "D-VIP",
    "док ленинский": "D-LR-2-4",
    "док курган": "D-KURG-O",
    "док златоуст": "D-ZLAT-4-4",
    "док троицк дальний": "D-TR-DL-5-1",
    "док бреды": "D-BRDY-3-4",
    "док кизил": "D-KIZIL-2-2",
    "док магнитогорск": "D-MG-P-1-1",
    "док чтз": "D-4TZ-2-3",
    "док северо запад": "D-SZ-1-2",
    "док магнитогорск левый": "D-MG-L-2-3",
    "док верхнеуральск": "D-V-UR-2-1",
    "док чмз": "D-4MZ-2-1",
    "док копейск": "D-KOP-2-3",
    "док центр": "D-CNTR-2-1"
}

UNIVERSAL_CELL = "D-KM-1"

class WMSAutomator(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WMS Auto-Bot v2.0 🤖")
        self.geometry("600x620")
        self.resizable(False, False)

        self.is_running = False
        self.target_window_title = None
        self.cycles_count = 0
        self.force_universal_cell = False

        self.setup_ui()
        self.refresh_windows_list()

    def setup_ui(self):
        self.header = ctk.CTkLabel(self, text="⚡ Smart WMS Automator v2.0", font=("Arial", 22, "bold"), text_color="#00BFFF")
        self.header.pack(pady=(15, 5))

        self.metrics_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=12)
        self.metrics_frame.pack(pady=10, padx=20, fill="x")

        self.lbl_cycles = ctk.CTkLabel(self.metrics_frame, text="🔁 Выполнено циклов: 0", font=("Arial", 15, "bold"))
        self.lbl_cycles.grid(row=0, column=0, padx=20, pady=8, sticky="w")

        self.lbl_status = ctk.CTkLabel(self.metrics_frame, text="Статус: ⏸ Ожидание запуска", font=("Arial", 15, "bold"), text_color="gray")
        self.lbl_status.grid(row=0, column=1, padx=20, pady=8, sticky="e")

        self.win_frame = ctk.CTkFrame(self, fg_color="#232323", corner_radius=12)
        self.win_frame.pack(pady=10, padx=20, fill="x")

        self.lbl_choose = ctk.CTkLabel(self.win_frame, text="Выпадающий список — выберите окно вашей WMS:", font=("Arial", 13, "bold"))
        self.lbl_choose.pack(pady=(8, 2), padx=15, anchor="w")

        self.combo_windows = ctk.CTkComboBox(self.win_frame, width=400, values=["Сначала обновите список..."])
        self.combo_windows.pack(side="left", padx=(15, 10), pady=(0, 15))

        self.btn_refresh = ctk.CTkButton(self.win_frame, text="🔄 Обновить", width=100, fg_color="#6c757d", hover_color="#5a6268", command=self.refresh_windows_list)
        self.btn_refresh.pack(side="left", padx=(0, 15), pady=(0, 15))

        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=10)

        self.btn_start = ctk.CTkButton(self.btn_frame, text="▶ ЗАПУСТИТЬ АВТОМАТ", fg_color="#28a745", hover_color="#218838", 
                                       font=("Arial", 14, "bold"), width=220, height=40, command=self.start_bot)
        self.btn_start.grid(row=0, column=0, padx=10)

        self.btn_stop = ctk.CTkButton(self.btn_frame, text="⏹ ОСТАНОВИТЬ", fg_color="#dc3545", hover_color="#c82333", 
                                      font=("Arial", 14, "bold"), width=220, height=40, state="disabled", command=self.stop_bot)
        self.btn_stop.grid(row=0, column=1, padx=10)

        self.log_box = ctk.CTkTextbox(self, width=550, height=240, corner_radius=10, font=("Consolas", 12))
        self.log_box.pack(pady=15)
        self.log("Система готова. Выберите окно WMS из списка выше и нажмите ЗАПУСТИТЬ.")

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
                self.log(f"Список окон обновлен. Найдено окон: {len(titles)}")
            else:
                self.combo_windows.configure(values=["Окна не найдены"])
        except Exception as e:
            self.log(f"Ошибка получения списка окон: {e}")

    def start_bot(self):
        selected = self.combo_windows.get()
        if not selected or selected in ["Сначала обновите список...", "Окна не найдены"]:
            self.log("❌ Ошибка: Пожалуйста, выберите корректное окно приложения!")
            return

        self.target_window_title = selected
        self.is_running = True
        self.btn_start.configure(state="disabled")
        self.btn_refresh.configure(state="disabled")
        self.combo_windows.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.lbl_status.configure(text="Статус: ▶ РАБОТАЕТ", text_color="#28a745")
        self.log(f"🚀 Робот привязан к окну: '{self.target_window_title}'")
        threading.Thread(target=self.bot_engine, daemon=True).start()

    def stop_bot(self):
        self.is_running = False
        self.btn_start.configure(state="normal")
        self.btn_refresh.configure(state="normal")
        self.combo_windows.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.lbl_status.configure(text="Статус: ⏸ ОСТАНОВЛЕН", text_color="#dc3545")
        self.log("🛑 Робот успешно остановлен.")

    def activate_target_window(self):
        try:
            wins = gw.getWindowsWithTitle(self.target_window_title)
            if wins:
                win = wins[0]
                if win.isMinimized:
                    win.restore()
                win.activate()
                time.sleep(0.3)
                return True
        except:
            pass
        return False

    def get_screen_text_advanced(self):
        text_content = ""
        if PYWINAUTO_AVAILABLE:
            try:
                for backend in ["uia", "win32"]:
                    try:
                        app = Application(backend=backend).connect(title_re=re.escape(self.target_window_title), timeout=0.3)
                        top_win = app.top_window()
                        elements_text = [ctrl.window_text() for ctrl in top_win.descendants() if ctrl.window_text()]
                        if elements_text:
                            text_content = " ".join(elements_text).lower()
                            if text_content.strip():
                                return text_content
                    except:
                        continue
            except:
                pass
        try:
            pyperclip.copy("") 
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.1)
            text_content = pyperclip.paste().lower()
        except:
            pass
        return text_content

    def safe_paste(self, text):
        pyperclip.copy(text)
        time.sleep(0.05)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.1)

    def bot_engine(self):
        retry_delays = [1, 4, 4, 15]
        attempt = 0

        while self.is_running:
            if not self.activate_target_window():
                self.log("⚠️ Окно WMS потеряно. Ожидание фокусировки...")
                time.sleep(2)
                continue

            try:
                screen_text = self.get_screen_text_advanced()

                if not screen_text.strip():
                    raise Exception("Текст с экрана не считался")

                if any(err in screen_text for err in ["не найден", "не существует", "не зарегистрирован", "ошибка"]):
                    self.log("⚠️ Окно предупреждения! Нажимаю Enter...")
                    pyautogui.press('enter')
                    time.sleep(0.5)
                    if "ячейка" in screen_text:
                        self.force_universal_cell = True
                    attempt = 0
                    continue

                # --- ЛОГИКА ЭКРАНОВ ---
                if any(kw in screen_text for kw in ["главное меню", "взятие работы", "взять работу"]):
                    self.log("➡️ Найдено меню. Нажимаю Взять работу (F2)...")
                    pyautogui.press('f2')
                    attempt = 0

                elif "место:" in screen_text or "место " in screen_text:
                    self.log("➡️ Экран: МЕСТО.")
                    match = re.search(r'(?:место[:\s]+)([a-zA-Z0-9\-_]+)', screen_text)
                    val = match.group(1) if match else None
                    if not val:
                        match = re.search(r'([a-zA-Z\d]+\-\d+)', screen_text)
                        val = match.group(1) if match else None

                    if val:
                        self.log(f"Копирую и вставляю Место: {val.upper()}")
                        pyautogui.hotkey('ctrl', 'a')
                        pyautogui.press('backspace')
                        self.safe_paste(val.upper())
                        pyautogui.press('enter')
                        attempt = 0
                    else:
                        raise Exception("Код Места не найден в тексте")

                elif "паллета" in screen_text:
                    self.log("➡️ Экран: ПАЛЛЕТА.")
                    match = re.search(r'(?:паллета[:\s]+)([a-zA-Z0-9\-_]+)', screen_text)
                    val = match.group(1) if match else None
                    if val:
                        self.log(f"Копирую и вставляю Паллету: {val.upper()}")
                        pyautogui.hotkey('ctrl', 'a')
                        pyautogui.press('backspace')
                        self.safe_paste(val.upper())
                        pyautogui.press('enter')
                        attempt = 0
                    else:
                        raise Exception("Код Паллеты не найден")

                elif "коробка" in screen_text:
                    self.log("➡️ Экран: КОРОБКА.")
                    match = re.search(r'(?:коробка[:\s]+)([a-zA-Z0-9\-_]+)', screen_text)
                    val = match.group(1) if match else None
                    if val:
                        self.log(f"Копирую и вставляю Коробку: {val.upper()}")
                        pyautogui.hotkey('ctrl', 'a')
                        pyautogui.press('backspace')
                        self.safe_paste(val.upper())
                        pyautogui.press('enter')
                        attempt = 0
                    else:
                        raise Exception("Код Коробки не найден")

                elif any(kw in screen_text for kw in ["назначение", "подсказки", "свободное размещение", "зона"]):
                    self.log("➡️ Экран: Определение Дока назначения.")
                    if self.force_universal_cell:
                        zone_code = UNIVERSAL_CELL
                        self.force_universal_cell = False
                        self.log(f"Принудительный фолбек на: {zone_code}")
                    else:
                        zone_code = UNIVERSAL_CELL
                        found_zone = None
                        for zone_name, code in DOCK_MAPPING.items():
                            if zone_name in screen_text:
                                found_zone = zone_name
                                zone_code = code
                                break
                        if found_zone:
                            self.log(f"Распознан Док '{found_zone}' -> Вставляю: {zone_code}")
                        else:
                            self.log(f"Док не определен, ставлю по умолчанию: {zone_code}")

                    pyautogui.hotkey('ctrl', 'a')
                    pyautogui.press('backspace')
                    self.safe_paste(zone_code)
                    pyautogui.press('enter')
                    attempt = 0

                elif "размещение в место" in screen_text:
                    self.log("➡️ Финал шага. Подтверждаю размещение (Enter).")
                    pyautogui.press('enter')
                    self.cycles_count += 1
                    self.lbl_cycles.configure(text=f"🔁 Выполнено циклов: {self.cycles_count}")
                    self.force_universal_cell = False
                    attempt = 0
                else:
                    raise Exception("Неизвестный шаг интерфейса")

                time.sleep(0.5)

            except Exception as e:
                delay = retry_delays[attempt] if attempt < len(retry_delays) else 30
                self.log(f"⌛ Ожидание обновления экрана... Пауза {delay} сек. ({e})")
                wait_time = 0
                while wait_time < delay and self.is_running:
                    time.sleep(0.2)
                    wait_time += 0.2
                attempt = min(attempt + 1, len(retry_delays) - 1)

if __name__ == "__main__":
    app = WMSAutomator()
    app.mainloop()
