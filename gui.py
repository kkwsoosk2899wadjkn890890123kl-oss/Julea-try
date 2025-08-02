import tkinter as tk
from tkinter import filedialog, ttk
import threading
import autotuner

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("File-Based Autotuner")
        self.geometry("400x250")

        # --- Variables ---
        self.input_path = tk.StringVar()
        self.output_path = tk.StringVar()
        self.scale_var = tk.StringVar(value='C-major')
        self.strength_var = tk.DoubleVar(value=1.0)
        self.status_var = tk.StringVar(value="Ready")

        # --- UI Elements ---
        # Input File
        ttk.Label(self, text="Input File:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(self, textvariable=self.input_path, width=40).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(self, text="Browse...", command=self.browse_input).grid(row=0, column=2, padx=5, pady=5)

        # Output File
        ttk.Label(self, text="Output File:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(self, textvariable=self.output_path, width=40).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(self, text="Browse...", command=self.browse_output).grid(row=1, column=2, padx=5, pady=5)

        # Scale
        ttk.Label(self, text="Scale:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        scales = [f"{root}-{stype}" for stype in ['major', 'minor'] for root in autotuner.NOTES] + ['chromatic']
        ttk.Combobox(self, textvariable=self.scale_var, values=scales, state="readonly").grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        # Strength
        ttk.Label(self, text="Strength:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        ttk.Scale(self, from_=0.0, to=1.0, variable=self.strength_var, orient="horizontal").grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        # Run Button
        self.run_button = ttk.Button(self, text="Run Processing", command=self.run_processing_thread)
        self.run_button.grid(row=4, column=1, padx=5, pady=10)

        # Status Bar
        ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN).grid(row=5, column=0, columnspan=3, sticky="ew")

    def browse_input(self):
        path = filedialog.askopenfilename(filetypes=[("WAV files", "*.wav")])
        if path:
            self.input_path.set(path)

    def browse_output(self):
        path = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV files", "*.wav")])
        if path:
            self.output_path.set(path)

    def run_processing_thread(self):
        """Runs the audio processing in a separate thread to keep the GUI responsive."""
        input_p = self.input_path.get()
        output_p = self.output_path.get()
        if not input_p or not output_p:
            self.status_var.set("Error: Please select input and output files.")
            return

        self.run_button.config(state="disabled")
        self.status_var.set("Processing...")

        thread = threading.Thread(target=self.processing_worker, args=(input_p, output_p))
        thread.start()
        # Periodically check if the thread is done
        self.after(100, self.check_thread, thread)

    def processing_worker(self, input_p, output_p):
        """The actual work done in the thread."""
        try:
            autotuner.process_file(
                input_filename=input_p,
                output_filename=output_p,
                scale_name=self.scale_var.get(),
                strength=self.strength_var.get()
            )
            self.status_var.set("Processing complete!")
        except Exception as e:
            self.status_var.set(f"Error: {e}")

    def check_thread(self, thread):
        """If the thread is finished, re-enable the run button."""
        if not thread.is_alive():
            self.run_button.config(state="normal")
        else:
            self.after(100, self.check_thread, thread)

if __name__ == "__main__":
    app = App()
    app.mainloop()
