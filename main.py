import threading
import time
import re
import customtkinter as ctk
import pyautogui
import pyperclip
import pygetwindow as gw

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

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

class WMSLinearBot(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("WMS Loop Automator v6.0")
        self.geometry("600x600")
        self.resizable(False, False)

        self.is_running = False
        self.target_window_title = None
        self.cycles_count = 0
        self.fallback_active = False

        self.setup_ui()
        self.refresh_windows_list()

    def setup_ui(self):
        self.header = ctk.CTkLabel(self, text="⚡ WMS Robot v6.0", font=("Arial", 20, "bold"), text_color="#00BFFF")
        self.header.pack(pady=15)

        self.metrics_frame = ctk.CTkFrame(self, fg_color="#2b2b2b")
        self.metrics_frame.pack(pady=10, padx=20, fill="x")

        self.lbl_cycles = ctk.CTkLabel(self.metrics_frame, text="🔁 Циклы: 0", font=("Arial", 14, "bold"))
        self.lbl_cycles.grid(row=0, column=0, padx=20, pady=8)

        self.lbl_status = ctk.CTkLabel(self.metrics_frame, text="Статус: Ожидание", font=("Arial", 14, "bold"), text_color="gray")
        self.lbl_status.grid(row=0, column=1, padx=20, pady=8)

        self.win_frame = ctk.CTkFrame(self, fg_color="#232323")
        self.win_frame.pack(pady=10, padx=20, fill="x")

        self.combo_windows = ctk.CTkComboBox(self.win_frame, width=400)
        self.combo_windows.pack(side="left", padx=15, pady=15)

        self.btn_refresh = ctk.CTkButton(self.win_frame, text="🔄", width=50, command=self.refresh_windows_list)
        self.btn_refresh.pack(side="left", padx=5, pady=15)

        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=15)

        self.btn_start = ctk.CTkButton(self.btn_frame, text="▶ ПУСК", fg_color="#28a745", width=200, height=40, command=self.start_bot)
        self.btn_start.grid(row=0, column=0, padx=10)

        self.btn_stop = ctk.CTkButton(self.btn_frame, text="⏹ СТОП", fg_color="#dc3545", width=200, height=40, state="disabled", command=self.stop_bot)
        self.btn_stop.grid(row=0, column=1, padx=10)

        self.log_box = ctk.CTkTextbox(self, width=540, height=240)
        self.log_box.pack(pady=10)

    def log(self, text):
        self.log_box.insert("end", f"> {text}\n")
        self.log_box.see("end")

    def refresh_windows_list(self):
        titles = [w.title for w in gw.getAllWindows() if w.title.strip()]
        titles = sorted(list(set(titles)))
        if titles:
            self.combo_windows.configure(values=titles)
            self.combo_windows.set(titles[0])

    def start_bot(self):
        selected = self.combo_windows.get()
        if not selected: return
        self.target_window_title = selected
        self.is_running = True
        self.btn_start.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.lbl_status.configure(text="Статус: АКТИВЕН", text_color="#28a745")
        threading.Thread(target=self.bot_engine, daemon=True).start()

    def stop_bot(self):
        self.is_running = False
        self.btn_start.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.lbl_status.configure(text="Статус: СТОП", text_color="#dc3545")

    def get_clean_text(self):
        try:
            pyperclip.copy("")
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.05)
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.05)
            return pyperclip.paste().lower().strip()
        except:
            return ""

    def send_value(self, value):
        pyautogui.press('tab')
        time.sleep(0.02)
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('backspace')
        pyperclip.copy(value)
        time.sleep(0.02)
        pyautogui.hotkey('ctrl', 'v')
        time.sleep(0.05)
        pyautogui.press('enter')

    def bot_engine(self):
        while self.is_running:
            wins = gw.getWindowsWithTitle(self.target_window_title)
            if not wins:
                time.sleep(1)
                continue
            
            win = wins[0]
            if win.isMinimized: win.restore()
            win.activate()
            time.sleep(0.1)

            text = self.get_clean_text()

            if not text:
                pyautogui.press('enter')
                time.sleep(0.5)
                continue

            if any(x in text for x in ["не найден", "не существует", "ошибка", "зарегистрирован"]):
                self.log("Обнаружен попап ошибки. Сброс.")
                pyautogui.press('enter')
                self.fallback_active = True
                time.sleep(0.5)
                continue

            # Проверка условий по шагам (1-12)
            if any(x in text for x in ["главное меню", "запросить работу", "взять работу"]):
                self.log("Шаг 1-2: Запрос работы")
                pyautogui.press('f2')
                time.sleep(0.5)

            elif "место" in text and "контроль" in text:
                self.log("Шаг 3-4: Обработка места")
                match = re.search(r'место[:\s]+([a-z0-9\-]+)', text)
                if match:
                    self.send_value(match.group(1).upper())
                else:
                    pyautogui.press('enter')

            elif "палет" in text or "контейнер" in text:
                self.log("Шаг 5-6: Обработка паллеты")
                match = re.search(r'палет[:\s]+([a-z0-9\-]+)', text)
                if match:
                    self.send_value(match.group(1).upper())
                else:
                    pyautogui.press('enter')

            elif "коробк" in text and "размещение" not in text:
                self.log("Шаг 7-8: Обработка коробки")
                match = re.search(r'коробк[:\s]+([a-z0-9\-]+)', text)
                if match:
                    self.send_value(match.group(1).upper())
                else:
                    pyautogui.press('enter')

            elif any(x in text for x in ["док", "зона", "назначение"]):
                self.log("Шаг 9: Определение дока")
                if self.fallback_active:
                    self.send_value(UNIVERSAL_CELL)
                    self.fallback_active = False
                else:
                    target = UNIVERSAL_CELL
                    for k, v in DOCK_MAPPING.items():
                        if k in text:
                            target = v
                            break
                    self.send_value(target)

            elif "размещение в место" in text:
                self.log("Шаг 10-11: Подтверждение размещения")
                pyautogui.press('enter')
                self.cycles_count += 1
                self.lbl_cycles.configure(text=f"Циклы: {self.cycles_count}")
                time.sleep(0.5)

            elif any(x in text for x in ["последн", "осталось", "заверш"]):
                self.log("Шаг 12: Финал партии")
                self.send_value(UNIVERSAL_CELL)
                time.sleep(0.5)

            else:
                pyautogui.press('enter')

            time.sleep(0.7)

if __name__ == "__main__":
    app = WMSLinearBot()
    app.mainloop()
