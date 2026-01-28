import tkinter as tk
import os

class OverlayUI:
    def __init__(self, on_toggle=None, on_stop=None, on_quit=None, on_switch=None):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.withdraw()
        self.on_switch = on_switch

        # Callbacks to the main logic
        self.on_toggle = on_toggle
        self.on_stop = on_stop
        self.on_quit = on_quit

        # --- SETTINGS ---
        self.width = 300
        self.height = 60
        self.screen_width = self.root.winfo_screenwidth()
        self.screen_height = self.root.winfo_screenheight()

        # State Variables
        self.ui_state = "IDLE"
        self.current_ai_text = ""

        # --- MAIN RESPONSE PANEL (Shows AI Text) ---
        self.root.geometry(
            f"{self.width}x{self.height}+{self.screen_width - self.width - 20}+{self.screen_height - 250}"
        )
        self.label = tk.Label(
            self.root, text="", fg="white", bg="black",
            font=("Arial", 10, "bold"), wraplength=self.width - 20, justify="center"
        )
        self.label.pack(expand=True, fill="both")

        # --- HOVER INDICATOR / MENU SYSTEM ---
        self.menu_window = tk.Toplevel(self.root)
        self.menu_window.overrideredirect(True)
        self.menu_window.attributes("-topmost", True)
        
        # Initial Compact State
        self.is_expanded = False
        self.menu_window.configure(bg="#003366")
        
        # Main Indicator Label (MAYA)
        self.ind_label = tk.Label(
            self.menu_window, text="MAYA", fg="white", bg="#003366", 
            font=("Arial", 7, "bold"), width=6, height=1
        )
        self.ind_label.pack(side="top", fill="x")

        # Container for hidden buttons
        self.btn_frame = tk.Frame(self.menu_window, bg="#1a1a1a")
        
        self.add_menu_button("🎙 Start/Stop (Ctrl+Q)", self.on_toggle)
        self.add_menu_button("⏹ Silence (Ctrl+Z)", self.on_stop)
        self.add_menu_button("💻 Switch to Laptop", self.on_switch) # New Button
        self.add_menu_button("❌ Quit", self.on_quit)

        # Bind Hover Events
        self.menu_window.bind("<Enter>", lambda e: self.expand_menu())
        self.menu_window.bind("<Leave>", lambda e: self.collapse_menu())

        self.update_geometry()
        self.refresh_loop()

    def add_menu_button(self, text, command):
        btn = tk.Button(
            self.btn_frame, text=text, bg="#1a1a1a", fg="white",
            font=("Arial", 8), relief="flat", anchor="w",
            padx=10, command=command, activebackground="#333333",
            activeforeground="white"
        )
        btn.pack(fill="x")

    def expand_menu(self):
        self.is_expanded = True
        self.btn_frame.pack(fill="both", expand=True)
        self.update_geometry()

    def collapse_menu(self):
        self.is_expanded = False
        self.btn_frame.pack_forget()
        self.update_geometry()

    def update_geometry(self):
        # Position at bottom right
        h = 120 if self.is_expanded else 20
        w = 120 if self.is_expanded else 40
        x = self.screen_width - w - 20
        y = self.screen_height - h - 60
        self.menu_window.geometry(f"{w}x{h}+{x}+{y}")

    def refresh_loop(self):
        # Handle the logic for coloring based on state
        colors = {
            "LISTENING": ("red", "white", "● LISTENING..."),
            "WAITING": ("#FFBF00", "black", "THINKING..."),
            "RESPONSE": ("green", "white", self.current_ai_text),
            "IDLE": ("#003366", "white", "")
        }
        
        bg, fg, text = colors.get(self.ui_state, colors["IDLE"])

        # Update Indicators
        self.ind_label.configure(bg=bg, fg=fg)
        if not self.is_expanded:
            self.menu_window.configure(bg=bg)

        # Update Main Panel
        if self.ui_state != "IDLE":
            self.root.deiconify()
            display_text = text if len(text) < 60 else text[:57] + "..."
            self.label.configure(text=display_text, bg=bg, fg=fg)
            self.root.configure(bg=bg)
        else:
            self.root.withdraw()

        self.root.after(200, self.refresh_loop)

    def run(self):
        self.root.mainloop()