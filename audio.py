import os
import time
import wave
import threading
import requests
import pyaudio
import pygame
from pathlib import Path

class AudioEngine:
    def __init__(self, api_url, temp_dir):
        self.api_url = api_url
        self.temp_dir = temp_dir
        self.temp_audio_path = temp_dir / "input.wav"
        self.recording = False
        
        # Initialize Pygame Mixer
        try:
            pygame.mixer.pre_init(44100, -16, 2, 2048)
            pygame.init()
            pygame.mixer.init()
        except Exception as e:
            print(f"Pygame Init Error: {e}")

    def toggle_record(self, ui_ref):
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()

        if not self.recording:
            self.recording = True
            threading.Thread(target=self._record_thread, args=(ui_ref,), daemon=True).start()
        else:
            self.recording = False

    def stop_everything(self, ui_ref):
        self.recording = False
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.stop()
        ui_ref.ui_state = "IDLE"

    def _record_thread(self, ui_ref):
        ui_ref.ui_state = "LISTENING"
        chunk, sample_format, channels, fs = 1024, pyaudio.paInt16, 1, 16000
        p = pyaudio.PyAudio()
        
        try:
            stream = p.open(format=sample_format, channels=channels, rate=fs, 
                            frames_per_buffer=chunk, input=True)
            frames = []
            while self.recording:
                frames.append(stream.read(chunk))
                
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            if frames:
                with wave.open(str(self.temp_audio_path), "wb") as wf:
                    wf.setnchannels(channels)
                    wf.setsampwidth(p.get_sample_size(sample_format))
                    wf.setframerate(fs)
                    wf.writeframes(b"".join(frames))
                threading.Thread(target=self._process_pipeline, args=(ui_ref,), daemon=True).start()
        except Exception as e:
            print(f"Recording Error: {e}")
            ui_ref.ui_state = "IDLE"

    def _process_pipeline(self, ui_ref):
        ui_ref.ui_state = "WAITING"
        try:
            with open(self.temp_audio_path, "rb") as f:
                files = {"audio_file": ("input.wav", f, "audio/wav")}
                response = requests.post(self.api_url, files=files, data={"return_audio": "true"}, timeout=60)
            
            if self.temp_audio_path.exists():
                os.remove(self.temp_audio_path)

            if response.status_code == 200:
                ui_ref.current_ai_text = response.headers.get("X-LLM-Response", "...")
                ui_ref.ui_state = "RESPONSE"
                
                out_file = self.temp_dir / f"res_{int(time.time())}.mp3"
                with open(out_file, "wb") as f:
                    f.write(response.content)

                pygame.mixer.music.load(str(out_file))
                pygame.mixer.music.play()
                
                # Wait for end and cleanup
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                if ui_ref.ui_state == "RESPONSE":
                    ui_ref.ui_state = "IDLE"
                
                pygame.mixer.music.unload()
                if out_file.exists():
                    os.remove(out_file)
            else:
                ui_ref.ui_state = "IDLE"
        except Exception as e:
            print(f"Pipeline Error: {e}")
            ui_ref.ui_state = "IDLE"