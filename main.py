import os
import sys
import threading
import shutil
from pathlib import Path
from pynput import keyboard
from dotenv import load_dotenv
from datetime import datetime

from ui import OverlayUI
from audio import AudioEngine
from other import switch_to_laptop

# --- SETUP ---
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

load_dotenv(BASE_DIR / ".env")
MAYA_SERVER_IP = os.getenv("MAYA_SERVER_IP", "100.124.34.102")
API_URL = f"http://{MAYA_SERVER_IP}:8000/process"
TEMP_DIR = BASE_DIR / "temp_audio"

def setup_temp_folder():
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR, exist_ok=True)

setup_temp_folder()

# --- INITIALIZE ENGINES ---
audio_engine = AudioEngine(API_URL, TEMP_DIR)

def on_toggle():
    audio_engine.toggle_record(ui)

def on_stop():
    audio_engine.stop_everything(ui)

def on_monitor_switch():
    # Run in thread so UI doesn't freeze while talking to monitor hardware
    threading.Thread(target=switch_to_laptop, daemon=True).start()

def quit_app():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Shutting down...")
    ui.root.quit()
    os._exit(0)

# Create UI with callbacks
ui = OverlayUI(
    on_toggle=on_toggle, 
    on_stop=on_stop, 
    on_quit=quit_app,
    on_switch=on_monitor_switch
)

# --- HOTKEYS ---
def start_hotkeys():
    with keyboard.GlobalHotKeys({
        '<ctrl>+q': on_toggle,
        '<ctrl>+z': on_stop,
        '<ctrl>+<shift>+x': quit_app
    }) as h:
        h.join()

if __name__ == "__main__":
    threading.Thread(target=start_hotkeys, daemon=True).start()
    print("Maya Client Started.")
    ui.run()