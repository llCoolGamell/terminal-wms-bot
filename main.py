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

# --- МАППИНГ ЗОН (из твоего Excel) ---
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
        self.title("WMS Auto-Bot 🤖")
        self.geometry("550x550")
        self.resizable(False, False)

        self.is_running = False
        self.target_window = None
        self.cycles_count = 0
        self.force_universal_cell = False

        self.setup_ui()

    def setup_ui(self):
        # Header
        self.header = ctk.CTkLabel(self, text="⚡ Smart WMS Automator", font=("Arial", 24, "bold"), text_color="#00BFFF")
        self.header.pack(pady=(15, 10))

        # Metrics Card
        self.metrics_frame = ctk.CTkFrame(self, fg_color="#2b2b2b", corner_radius=15)
        self.metrics_frame.pack(pady=10, padx=20, fill="x")

        self.lbl_cycles = ctk.CTkLabel(self.metrics_frame, text="🔁 Циклов: 0", font=("Arial", 16))
        self.lbl_cycles.grid(row=0, column=0, padx=20, pady=10, sticky="w")

        self.lbl_app = ctk.CTkLabel(self.metrics_frame, text="🪟 Окно: Не выбрано", font=("Arial", 16), text_color="#FFD700")
        self.lbl_app.grid(row=0, column=1, padx=20, pady=10, sticky="e")

        self.lbl_status = ctk.CTkLabel(self.metrics_frame, text="Статус: ⏸ Ожидание", font=("Arial", 16, "bold"), text_color="gray")
        self.lbl_status.grid(row=1, column=0, columnspan=2, pady=10)

        # Buttons
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=10)

        self.btn_pick = ctk.CTkButton(self.btn_frame, text="🎯 Выбрать окно", fg_color="#17a2b8", hover_color="#138496", 
                                      font=("Arial", 14, "bold"), command=self.pick_window)
        self.btn_pick.grid(row=0, column=0, padx=10)

        self.btn_start = ctk.CTkButton(self.btn_frame, text="▶ СТАРТ", fg_color="#28a745", hover_color="#218838", 
                                       font=("Arial", 14, "bold"), state="disabled", command=self.start_bot)
        self.btn_start.grid(row=0, column=1, padx=10)

        self.btn_stop = ctk.CTkButton(self.btn_frame, text="⏹ СТОП", fg_color="#dc3545", hover_color="#c82333", 
                                      font=("Arial", 14, "bold"), state="disabled", command=self.stop_bot)
        self.btn_stop.grid(row=0, column=2, padx=10)

        # Logs
        self.log_box = ctk.CTkTextbox(self, width=500, height=200, corner_radius=10, font=("Consolas", 12))
        self.log_box.pack(pady=15)
        self.log("Привет! Сначала нажми '🎯 Выбрать окно' и кликни по приложению WMS.")

    def log(self, text):
        self.log_box.insert("end", f"> {text}\n")
        self.log_box.see("end")

    def pick_window(self):
        self.log("⏳ У тебя 3 секунды... Кликни по окну WMS!")
        self.btn_pick.configure(state="disabled")
        threading.Thread(target=self._pick_window_thread, daemon=True).start()

    def _pick_window_thread(self):
        time.sleep(3)
        active_window = gw.getActiveWindow()
        if active_window:
            self.target_window = active_window
            self.lbl_app.configure(text=f"🪟 Окно: {active_window.title[:15]}...", text_color="#28a745")
            self.log(f"✅ Окно захвачено: {active_window.title}")
            self.btn_start.configure(state="normal")
        else:
            self.log("❌ Не удалось захватить окно.")
        self.btn_pick.configure(state="normal")

    def start_bot(self):
        self.is_running = True
        self.btn_start.configure(state="disabled")
        self.btn_pick.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.lbl_status.configure(text="Статус: ▶ В РАБОТЕ", text_color="#28a745")
        self.log("🚀 БОТ ЗАПУЩЕН")
        threading.Thread(target=self.bot_engine, daemon=True).start()

    def stop_bot(self):
        self.is_running = False
        self.btn_start.configure(state="normal")
        self.btn_pick.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.lbl_status.configure(text="Статус: ⏸ ОСТАНОВЛЕН", text_color="#dc3545")
        self.log("🛑 БОТ ОСТАНОВЛЕН")

    def activate_wms_window(self):
        if self.target_window:
            try:
                self.target_window.activate()
                time.sleep(0.2)
                return True
            except:
                pass
        return False

    def get_screen_text(self):
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.1)
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(0.1)
        return pyperclip.paste().lower()

    def safe_copy(self):
        pyperclip.copy("")
        pyautogui.hotkey('ctrl', 'c')
        time.sleep(0.1)
        return pyperclip.paste().strip()

    def safe_paste(self, text):
        pyperclip.copy(text)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.1)

    def bot_engine(self):
        retry_delays = [1, 5, 5, 20, 20]
        attempt = 0

        while self.is_running:
            if not self.activate_wms_window():
                self.log("⚠️ Окно потеряно. Жду...")
                time.sleep(2)
                continue

            try:
                screen_text = self.get_screen_text()

                if any(err in screen_text for err in ["не найден", "не существует", "не зарегистрирован"]):
                    self.log("⚠️ Обнаружена ошибка (попап). Закрываю...")
                    pyautogui.press('enter')
                    time.sleep(0.5)
                    
                    if "не найден" in screen_text:
                        self.log("Универсальная ячейка активирована для следующего шага.")
                        self.force_universal_cell = True
                    
                    attempt = 0
                    continue

                if "главное меню" in screen_text or "взятие работы" in screen_text:
                    self.log("➡️ Экран: Меню. Нажимаю F2")
                    pyautogui.press('f2')
                    attempt = 0

                elif any(word in screen_text for word in ["место:", "паллета:", "коробка:"]):
                    self.log("➡️ Экран: Сканирование объекта.")
                    pyautogui.press('tab')
                    copied_data = self.safe_copy()
                    if copied_data:
                        self.log(f"Скопировано: {copied_data}")
                        pyautogui.press('tab')
                        self.safe_paste(copied_data)
                        pyautogui.press('enter')
                        attempt = 0
                    else:
                        raise Exception("Поле пустое")

                elif "назначение" in screen_text or "подсказки" in screen_text:
                    self.log("➡️ Экран: Поиск места-приемника.")
                    
                    if self.force_universal_cell:
                        zone_code = UNIVERSAL_CELL
                        self.force_universal_cell = False
                        self.log(f"Вставляю универсальный код: {zone_code}")
                    else:
                        found_zone = None
                        for zone_name in DOCK_MAPPING.keys():
                            if zone_name in screen_text:
                                found_zone = zone_name
                                break
                        
                        if found_zone:
                            zone_code = DOCK_MAPPING[found_zone]
                            self.log(f"Распознана зона: {found_zone} -> {zone_code}")
                        else:
                            self.log("Зона не найдена в базе, использую D-KM-1")
                            zone_code = UNIVERSAL_CELL

                    pyautogui.press('tab')
                    self.safe_paste(zone_code)
                    pyautogui.press('enter')
                    attempt = 0

                elif "размещение в место" in screen_text:
                    self.log("➡️ Экран: Финал размещения. Нажимаю Enter.")
                    pyautogui.press('enter')
                    self.cycles_count += 1
                    self.lbl_cycles.configure(text=f"🔁 Циклов: {self.cycles_count}")
                    self.force_universal_cell = False
                    attempt = 0

                else:
                    raise Exception("Экран не распознан")

                time.sleep(0.5)

            except Exception as e:
                delay = retry_delays[attempt] if attempt < len(retry_delays) else 60
                self.log(f"⌛ Ожидание экрана... Пауза {delay} сек. (Попытка {attempt + 1})")
                
                wait_time = 0
                while wait_time < delay and self.is_running:
                    time.sleep(0.5)
                    wait_time += 0.5
                    
                attempt += 1

if __name__ == "__main__":
    app = WMSAutomator()
    app.mainloop()
