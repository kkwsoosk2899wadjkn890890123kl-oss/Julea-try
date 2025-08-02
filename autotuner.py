import pyaudio
import time
import argparse
import wave
import numpy as np
import aubio
# --- Audio Settings ---
CHUNK = 1024
FORMAT = pyaudio.paFloat32  # Use float32 for aubio
CHANNELS = 1
RATE = 44100
WIN_S = 4096  # FFT window size
HOP_S = CHUNK # Hop size

class KeyDetector:
    """Analyzes a stream of pitches to detect the musical key."""
    def __init__(self):
        self.pitch_buffer = []
        self.chroma = np.zeros(12)
        self.detected_key = "Unknown"
        self.key_profiles = self._generate_key_profiles()

    def _generate_key_profiles(self):
        """Generates correlation profiles for all major and minor keys."""
        profiles = {}
        # Krumhansl-Schmuckler key profiles (major and minor)
        major_profile = [6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88]
        minor_profile = [6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17]
        for i in range(12):
            root_note = NOTES[i]
            profiles[f"{root_note}-major"] = np.roll(major_profile, i)
            profiles[f"{root_note}-minor"] = np.roll(minor_profile, i)
        return profiles

    def add_pitch(self, pitch):
        """Adds a new pitch to the buffer and updates the chroma vector."""
        if pitch > 0:
            midi_note = int(round(pitch))
            self.pitch_buffer.append(midi_note)
            self.chroma[midi_note % 12] += 1

    def detect_key(self):
        """
        Detects the key by correlating the chroma vector with key profiles.
        Returns the name of the key (e.g., 'C-major').
        """
        if np.sum(self.chroma) == 0:
            return "Unknown"

        correlations = {}
        for key_name, profile in self.key_profiles.items():
            # Calculate Pearson correlation
            correlation = np.corrcoef(self.chroma, profile)[0, 1]
            correlations[key_name] = correlation

        # Find the key with the highest correlation
        best_key = max(correlations, key=correlations.get)
        self.detected_key = best_key
        return best_key

class AudioStream:
    """Handles live audio input and output with real-time pitch correction."""
    def __init__(self, scale='auto', strength=1.0):
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.scale = scale
        self.strength = strength
        self.allowed_notes = get_scale_notes(scale)
        self.key_detector = KeyDetector()
        self.pitches_for_key_detection = 200 # How many notes to collect before detecting key

        # --- Aubio setup for real-time processing ---
        self.pitch_o = aubio.pitch("default", WIN_S, HOP_S, RATE)
        self.pitch_o.set_unit("midi")
        self.pitch_o.set_tolerance(0.7)
        self.pvoc = aubio.pvoc(WIN_S, HOP_S)
        self.shift = aubio.shift(WIN_S, HOP_S, RATE)

    def callback(self, in_data, frame_count, time_info, status):
        """Processes audio data in real-time."""
        samples = np.frombuffer(in_data, dtype=np.float32)

        pitch = self.pitch_o(samples)[0]

        # --- Auto-Key Detection ---
        if self.scale == 'auto' and len(self.key_detector.pitch_buffer) < self.pitches_for_key_detection:
            self.key_detector.add_pitch(pitch)
            # Once we have enough pitches, detect the key and update the allowed notes
            if len(self.key_detector.pitch_buffer) == self.pitches_for_key_detection:
                detected_key = self.key_detector.detect_key()
                print(f"*** Detected Key: {detected_key} ***")
                self.allowed_notes = get_scale_notes(detected_key)

        # --- Pitch Correction Logic ---
        if pitch > 0 and self.allowed_notes:
            # Find the nearest note in the scale
            note_distances = [((pitch % 12) - scale_note + 6) % 12 - 6 for scale_note in self.allowed_notes]
            min_dist_idx = np.argmin(np.abs(note_distances))
            semitone_error = note_distances[min_dist_idx]

            # The desired pitch is the current pitch minus the error
            target_pitch = pitch - semitone_error

            # Apply correction strength
            pitch_to_set = (self.strength * target_pitch) + ((1 - self.strength) * pitch)
            self.shift.set_pitch(pitch_to_set)

        # --- Process and output ---
        fftgrain = self.pvoc(samples)
        shifted_fftgrain = self.shift(fftgrain)
        out_samples = self.pvoc.synth(shifted_fftgrain)

        out_data = out_samples.tobytes()
        return (out_data, pyaudio.paContinue)

    def start(self, input_device_index=None, output_device_index=None):
        """Opens and starts the audio stream."""
        # If scale is auto, start with chromatic until key is detected
        if self.scale == 'auto':
            self.allowed_notes = get_scale_notes('chromatic')

        self.stream = self.p.open(format=FORMAT,
                                  channels=CHANNELS,
                                  rate=RATE,
                                  input=True,
                                  output=True,
                                  input_device_index=input_device_index,
                                  output_device_index=output_device_index,
                                  frames_per_buffer=CHUNK,
                                  stream_callback=self.callback)
        self.stream.start_stream()
        print("Audio stream started.")

    def stop(self):
        """Closes the audio stream."""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.p.terminate()
        print("Audio stream stopped.")

# --- Scale Definitions ---
SCALES = {
    'chromatic': list(range(12)),
    'major': [0, 2, 4, 5, 7, 9, 11],
    'minor': [0, 2, 3, 5, 7, 8, 10],
}
NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def get_scale_notes(scale_name):
    """Parses a scale name (e.g., 'C-major') and returns its MIDI notes."""
    if scale_name == 'chromatic':
        return SCALES['chromatic']

    try:
        root_note_str, scale_type = scale_name.split('-')
        root_note = NOTES.index(root_note_str.upper())
        scale_pattern = SCALES[scale_type.lower()]
        # Create the full scale by adding the root note to the pattern
        return [(root_note + i) % 12 for i in scale_pattern]
    except (ValueError, KeyError):
        print(f"Warning: Invalid scale '{scale_name}'. Defaulting to chromatic.")
        return SCALES['chromatic']

def get_audio_devices():
    """Returns lists of available input and output audio devices."""
    p = pyaudio.PyAudio()
    input_devices = []
    output_devices = []
    for i in range(p.get_device_count()):
        info = p.get_device_info_by_index(i)
        if info.get('maxInputChannels') > 0:
            input_devices.append({'index': i, 'name': info.get('name')})
        if info.get('maxOutputChannels') > 0:
            output_devices.append({'index': i, 'name': info.get('name')})
    p.terminate()
    return input_devices, output_devices

def main():
    parser = argparse.ArgumentParser(description="A real-time autotuner.")
    parser.add_argument('--list-devices', action='store_true', help="List available audio devices and exit.")
    parser.add_argument('--input-device', type=int, help="Index of the input device to use.")
    parser.add_argument('--output-device', type=int, help="Index of the output device to use.")
    parser.add_argument('--scale', default='auto', help="Musical scale. Use 'auto' for automatic detection (e.g., 'C-major', 'auto').")
    parser.add_argument('--strength', type=float, default=1.0, help="Correction strength (0.0 to 1.0). 1.0 is full correction.")

    args = parser.parse_args()

    if args.list_devices:
        inputs, outputs = get_audio_devices()
        print("--- Input Devices ---")
        for device in inputs:
            print(f"  Index {device['index']}: {device['name']}")
        print("\n--- Output Devices ---")
        for device in outputs:
            print(f"  Index {device['index']}: {device['name']}")
        return

    print(f"Starting real-time autotuner with scale={args.scale} and strength={args.strength}")

    try:
        autotune_stream = AudioStream(scale=args.scale, strength=args.strength)
        autotune_stream.start(input_device_index=args.input_device, output_device_index=args.output_device)

        print("Autotuner is running. Press Ctrl+C to stop.")
        while autotune_stream.stream.is_active():
            time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nStopping autotuner...")
        if 'autotune_stream' in locals() and autotune_stream.stream:
            autotune_stream.stop()
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    # This will be removed, but we keep it for now for compatibility
    # with the old file-based processing.
    def process_file(input_filename, output_filename, scale_name, strength):
        print("File processing is disabled in real-time mode.")

    main()
