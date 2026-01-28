#test.py

import requests
import subprocess
import json

# Configuration
OLLAMA_URL = "http://100.124.34.102:11434/api/generate" # Use your Tailscale IP
MODEL = "llama3"
PIPER_PATH = "./piper" # Path to piper executable
VOICE_MODEL = "en_US-lessac-medium.onnx"

def ask_and_speak(prompt):
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    print(f"Querying Ollama at {OLLAMA_URL}...")
    response = requests.post(OLLAMA_URL, json=payload)
    text = response.json().get("response", "")

    print(f"Ollama says: {text}")

    # Pipe text to Piper and play via aplayer (standard on Linux)
    piper_process = subprocess.Popen(
        [PIPER_PATH, "--model", VOICE_MODEL, "--output_raw"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE
    )
    
    play_process = subprocess.Popen(["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw"], stdin=piper_process.stdout)
    
    piper_process.stdin.write(text.encode('utf-8'))
    piper_process.stdin.close()
    play_process.wait()

if __name__ == "__main__":
    user_input = input("What should I ask the server? ")
    ask_and_speak(user_input)