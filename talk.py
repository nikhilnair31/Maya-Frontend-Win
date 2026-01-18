import os
import sys
import time
import wave
import threading
import tkinter as tk
import requests
import pyaudio
import pygame
import shutil
from pathlib import Path
from pynput import keyboard
from dotenv import load_dotenv
from datetime import datetime

# --- EXE PATH HANDLING ---
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
load_dotenv(BASE_DIR / ".env")

MAYA_SERVER_IP = os.getenv("MAYA_SERVER_IP", "127.0.0.1")
API_URL = f"http://{MAYA_SERVER_IP}:8000/process"
TEMP_DIR = BASE_DIR / "temp_audio"
TEMP_AUDIO = TEMP_DIR / "input.wav"

recording = False
ui_state = "IDLE" 
current_ai_text = ""

def log_event(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def setup_temp_folder():
    try:
        if TEMP_DIR.exists():
            shutil.rmtree(TEMP_DIR)
        os.makedirs(TEMP_DIR, exist_ok=True)
    except Exception as e:
        log_event(f"Startup Cleanup Warning: {e}")

setup_temp_folder()

try:
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.init()
    pygame.mixer.init()
except Exception as e:
    log_event(f"Pygame Init Error: {e}")

class OverlayUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.withdraw() # Start hidden (Idle)
        
        # --- MAIN OVERLAY WINDOW ---
        self.width = 300
        self.height = 60
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Horizontal: screen_width - width - 20 (Matches the indicator)
        # Vertical: screen_height - 250
        self.root.geometry(
            f"{self.width}x{self.height}+{screen_width - self.width - 20}+{screen_height - 250}"
        )
        
        self.label = tk.Label(
            self.root, text="", fg="white", bg="black",
            font=("Arial", 10, "bold"), wraplength=self.width - 20, justify="center"
        )
        self.label.pack(expand=True, fill="both")

        # --- PERSISTENT INDICATOR WINDOW ---
        self.indicator = tk.Toplevel(self.root)
        self.indicator.overrideredirect(True)
        self.indicator.attributes("-topmost", True)
        
        # 40 width + 20 padding = 60. screen_width - 60 = aligned with the right of main box.
        self.indicator.geometry(f"40x20+{screen_width - 60}+{screen_height - 80}")
        self.indicator.configure(bg="#003366") 
        
        self.ind_label = tk.Label(
            self.indicator, text="MAYA", fg="white", bg="#003366", 
            font=("Arial", 7, "bold")
        )
        self.ind_label.pack(expand=True, fill="both")
        
        self.ind_label.bind("<Button-1>", lambda e: quit_app())

        self.update_ui()

    def update_ui(self):
        global ui_state, recording, current_ai_text
        
        # Keep indicator on top
        self.indicator.attributes("-topmost", True)

        if ui_state == "LISTENING":
            self.root.configure(bg="red")
            self.label.configure(text="● LISTENING...", bg="red", fg="white")
            self.indicator.configure(bg="red")
            self.ind_label.configure(bg="red")
        elif ui_state == "WAITING":
            self.root.configure(bg="#FFBF00") 
            self.label.configure(text="THINKING...", bg="#FFBF00", fg="black")
            self.indicator.configure(bg="#FFBF00")
            self.ind_label.configure(bg="#FFBF00", fg="black")
        elif ui_state == "RESPONSE":
            self.root.configure(bg="green")
            display_text = current_ai_text if len(current_ai_text) < 60 else current_ai_text[:57] + "..."
            self.label.configure(text=display_text, bg="green", fg="white")
            self.indicator.configure(bg="green")
            self.ind_label.configure(bg="green", fg="white")
        else:
            # IDLE STATE: Hide the main panel
            if self.root.winfo_viewable():
                self.root.withdraw()
            self.indicator.configure(bg="#003366")
            self.ind_label.configure(bg="#003366", fg="white")

        self.root.after(200, self.update_ui)
    
    def hide(self):
        self.root.withdraw()

    def show(self):
        self.root.deiconify()

    def run(self):
        self.root.mainloop()

ui = OverlayUI()

def record_audio():
    global recording, ui_state
    ui_state = "LISTENING"
    chunk = 1024
    sample_format = pyaudio.paInt16
    channels = 1
    fs = 16000
    p = pyaudio.PyAudio()
    
    try:
        stream = p.open(format=sample_format, channels=channels, rate=fs, frames_per_buffer=chunk, input=True)
        frames = []
        while recording:
            data = stream.read(chunk)
            frames.append(data)
                
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        if frames:
            with wave.open(str(TEMP_AUDIO), "wb") as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(p.get_sample_size(sample_format))
                wf.setframerate(fs)
                wf.writeframes(b"".join(frames))
            threading.Thread(target=process_voice_pipeline, daemon=True).start()
    except Exception as e:
        log_event(f"Recording Error: {e}")
        ui_state = "IDLE"

def process_voice_pipeline():
    global ui_state, current_ai_text
    ui_state = "WAITING"
    try:
        if not TEMP_AUDIO.exists():
            ui_state = "IDLE"
            return
            
        with open(TEMP_AUDIO, "rb") as f:
            files = {"audio_file": ("input.wav", f, "audio/wav")}
            data = {"return_audio": "true"}
            response = requests.post(API_URL, files=files, data=data, timeout=60)
        
        if TEMP_AUDIO.exists():
            os.remove(TEMP_AUDIO)

        if response.status_code == 200:
            current_ai_text = response.headers.get("X-LLM-Response", "...")
            ui_state = "RESPONSE"
            output_file = TEMP_DIR / f"res_{int(time.time())}.mp3"
            with open(output_file, "wb") as f:
                f.write(response.content)

            if pygame.mixer.get_init():
                pygame.mixer.music.load(str(output_file))
                pygame.mixer.music.play()
                threading.Thread(target=wait_for_audio_end, args=(output_file,), daemon=True).start()
        else:
            ui_state = "IDLE"
    except Exception as e:
        log_event(f"Pipeline Error: {e}")
        ui_state = "IDLE"

def wait_for_audio_end(path):
    global ui_state
    while pygame.mixer.music.get_busy():
        time.sleep(0.1)
    if ui_state == "RESPONSE":
        ui_state = "IDLE"
    safe_delete(path)

def safe_delete(path):
    try:
        pygame.mixer.music.unload()
        if os.path.exists(path): os.remove(path)
    except: pass

def stop_and_hide():
    global recording, ui_state
    recording = False
    ui_state = "IDLE"
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.stop()
    ui.hide()

def toggle_session():
    global recording
    ui.show()
    if pygame.mixer.music.get_busy():
        pygame.mixer.music.stop()

    if not recording:
        ui.show() # Make panel visible when recording starts
        recording = True
        threading.Thread(target=record_audio, daemon=True).start()
    else:
        recording = False
        # The update_ui loop will handle hiding it when state returns to IDLE

def quit_app():
    log_event("Shutting down Maya...")
    ui.root.quit()
    os._exit(0)

def start_hotkeys():
    with keyboard.GlobalHotKeys({
        '<ctrl>+q': toggle_session,
        '<ctrl>+z': stop_and_hide,
        '<ctrl>+<shift>+x': quit_app
    }) as h:
        h.join()

if __name__ == "__main__":
    threading.Thread(target=start_hotkeys, daemon=True).start()
    ui.run()