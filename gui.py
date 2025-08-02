import sys
import threading
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QComboBox, QLabel,
                             QStatusBar, QFrame)
from PyQt6.QtCore import QThread, QObject, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QPainter, QColor, QFont, QPen, QBrush, QPainterPath
import autotuner
import numpy as np

class AudioWorker(QObject):
    """
    Worker thread for handling the audio stream to prevent GUI freezing.
    """
    finished = pyqtSignal()
    pitch_update = pyqtSignal(float, float)  # original_pitch, corrected_pitch
    key_update = pyqtSignal(str)
    status_update = pyqtSignal(str)

    def __init__(self, input_device, output_device, scale, strength):
        super().__init__()
        self.input_device = input_device
        self.output_device = output_device
        self.scale = scale
        self.strength = strength
        self.running = False
        self.audio_stream = None

    def run(self):
        """Start processing audio."""
        self.running = True
        try:
            self.audio_stream = autotuner.AudioStream(scale=self.scale, strength=self.strength)

            # Monkey-patch the callback to emit signals
            original_callback = self.audio_stream.callback
            self.audio_stream.callback = lambda *args, **kwargs: self._callback_wrapper(original_callback, *args, **kwargs)

            self.audio_stream.start(self.input_device, self.output_device)
            self.status_update.emit("Processing audio...")

            # Keep the thread alive while the stream is active
            while self.running and self.audio_stream.stream.is_active():
                # Check for key detection updates
                if self.scale == 'auto' and self.audio_stream.key_detector.detected_key != "Unknown":
                    self.key_update.emit(self.audio_stream.key_detector.detected_key)

                QThread.msleep(100) # Sleep to prevent a busy loop
        except Exception as e:
            self.status_update.emit(f"Error: {e}")
        finally:
            self.finished.emit()

    def _callback_wrapper(self, original_callback, *args, **kwargs):
        """Wraps the original callback to extract and emit pitch data."""
        # --- Pre-computation to get original pitch ---
        in_data = args[0]
        samples = np.frombuffer(in_data, dtype=np.float32)
        original_pitch = self.audio_stream.pitch_o(samples)[0]

        # --- Call the original callback to get processed data ---
        out_data, flag = original_callback(*args, **kwargs)

        # --- Post-computation to get corrected pitch ---
        if original_pitch > 0:
            target_pitch = self.audio_stream.shift.get_pitch()
            self.pitch_update.emit(original_pitch, target_pitch)
        else:
            self.pitch_update.emit(0.0, 0.0)

        return out_data, flag

    def stop(self):
        """Stop the audio stream."""
        self.running = False
        if self.audio_stream:
            self.audio_stream.stop()
        self.status_update.emit("Ready")

class PitchWidget(QWidget):
    """A custom widget to visualize pitch."""
    def __init__(self):
        super().__init__()
        self.setMinimumSize(300, 150)
        self.original_pitch = 0.0
        self.corrected_pitch = 0.0
        self.note_labels = {}

    def update_pitch(self, original, corrected):
        self.original_pitch = original
        self.corrected_pitch = corrected
        self.update() # Trigger a repaint

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Background
        painter.fillRect(self.rect(), QColor("#2c3e50"))

        # Center line for the target note
        painter.setPen(QPen(QColor("#3498db"), 2))
        painter.drawLine(width // 2, 20, width // 2, height - 50)

        # Draw note display
        self._draw_note_display(painter)

        # Draw pitch indicator
        if self.original_pitch > 0:
            self._draw_pitch_indicator(painter)

    def _draw_note_display(self, painter):
        if self.corrected_pitch > 0:
            midi_note = int(round(self.corrected_pitch))
            note_name = autotuner.NOTES[midi_note % 12]

            painter.setPen(QColor("#ecf0f1"))
            font = QFont("Arial", 24, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(self.rect(), 0, note_name)

    def _draw_pitch_indicator(self, painter):
        width = self.width()
        height = self.height()

        # Calculate cents deviation
        cents_dev = 1200 * np.log2(self.original_pitch / autotuner.librosa.midi_to_hz(self.corrected_pitch)) if self.corrected_pitch > 0 else 0

        # Clamp deviation to a range (e.g., -50 to +50 cents)
        clamped_dev = max(-50, min(50, cents_dev))

        # Map deviation to a position
        x_pos = (width // 2) + (clamped_dev / 50.0) * (width // 2 - 20)

        # Draw indicator line
        painter.setPen(QPen(QColor("#e74c3c"), 4))
        painter.drawLine(int(x_pos), 20, int(x_pos), height - 50)

        # Draw deviation text
        painter.setPen(QColor("#ecf0f1"))
        font = QFont("Arial", 10)
        painter.setFont(font)
        painter.drawText(int(x_pos) - 15, height - 30, f"{cents_dev:.1f} cents")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-Time Autotuner")
        self.setGeometry(100, 100, 450, 400)

        # --- Central Widget and Layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- UI Elements ---
        self.pitch_widget = PitchWidget()
        self.input_combo = QComboBox()
        self.output_combo = QComboBox()
        self.start_stop_button = QPushButton("Start Processing")
        self.detected_key_label = QLabel("Detected Key: N/A")

        # Styling
        self.setStyleSheet("""
            QMainWindow { background-color: #34495e; }
            QLabel { color: #ecf0f1; font-size: 14px; }
            QComboBox { padding: 5px; background-color: #2c3e50; color: #ecf0f1; border: 1px solid #7f8c8d; }
            QPushButton {
                background-color: #27ae60; color: white; font-size: 16px;
                padding: 10px; border: none; border-radius: 5px;
            }
            QPushButton:hover { background-color: #2ecc71; }
            QPushButton:pressed { background-color: #27ae60; }
        """)

        # --- Layouts ---
        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("Input:"))
        control_layout.addWidget(self.input_combo)
        control_layout.addWidget(QLabel("Output:"))
        control_layout.addWidget(self.output_combo)

        main_layout.addLayout(control_layout)
        main_layout.addWidget(self.pitch_widget)
        main_layout.addWidget(self.detected_key_label)
        main_layout.addWidget(self.start_stop_button)

        # --- Status Bar ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

        # --- Populate Devices ---
        self.populate_devices()

        # --- Threading ---
        self.audio_thread = None
        self.audio_worker = None

        # --- Connections ---
        self.start_stop_button.clicked.connect(self.toggle_processing)

    def populate_devices(self):
        try:
            inputs, outputs = autotuner.get_audio_devices()
            for device in inputs:
                self.input_combo.addItem(device['name'], device['index'])
            for device in outputs:
                self.output_combo.addItem(device['name'], device['index'])
        except Exception as e:
            self.status_bar.showMessage(f"Could not load audio devices: {e}")

    @pyqtSlot()
    def toggle_processing(self):
        if self.audio_worker is None or not self.audio_worker.running:
            input_idx = self.input_combo.currentData()
            output_idx = self.output_combo.currentData()

            self.audio_thread = QThread()
            self.audio_worker = AudioWorker(input_idx, output_idx, scale='auto', strength=1.0)
            self.audio_worker.moveToThread(self.audio_thread)

            # --- Connect signals from worker to GUI slots ---
            self.audio_thread.started.connect(self.audio_worker.run)
            self.audio_worker.finished.connect(self.audio_thread.quit)
            self.audio_worker.finished.connect(self.audio_worker.deleteLater)
            self.audio_thread.finished.connect(self.audio_thread.deleteLater)
            self.audio_worker.pitch_update.connect(self.pitch_widget.update_pitch)
            self.audio_worker.key_update.connect(self.update_key_display)
            self.audio_worker.status_update.connect(self.status_bar.showMessage)

            self.audio_thread.start()

            self.start_stop_button.setText("Stop Processing")
            self.start_stop_button.setStyleSheet("background-color: #c0392b;") # Red color
        else:
            self.audio_worker.stop()
            self.start_stop_button.setText("Start Processing")
            self.start_stop_button.setStyleSheet("background-color: #27ae60;") # Green color

    @pyqtSlot(str)
    def update_key_display(self, key):
        self.detected_key_label.setText(f"Detected Key: {key}")

    def closeEvent(self, event):
        """Ensure the audio thread is stopped when the window closes."""
        if self.audio_worker and self.audio_worker.running:
            self.audio_worker.stop()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    # We need to add librosa to the autotuner namespace for the pitch widget
    import librosa
    autotuner.librosa = librosa
    main()
